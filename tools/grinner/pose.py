"""Poses the grinner's rig from an animator's controls, and records clips of them.

A pose is a dict of named controls, zero at rest: angles in degrees, lengths in metres. The body is turned
bone by bone; each foot is put where it should stand and its leg solved to reach it, and so is a planted hand;
paired controls end in _l or _r and mean the same on both sides. `solve` turns controls into every bone's
rotation from rest, in the figure's axes (+X its left, -Y forward, +Z up).

  travel                          how far the root has walked
  hips_x/y/z, hips_pitch/roll/yaw the pelvis; pitch bows forward, roll leans left, yaw turns left
  spine_, chest_, neck_, head_    the same three turns, each on top of the bone below
  head_level                      0..1: how far the head ignores the body's lean
  foot_x/y/z, foot_yaw/pitch/roll the sole under the ankle; pitch lifts the heel off the ball (or, negative,
                                  the toes off the heel), yaw turns the toes out
  toe, knee                       toes bent up; knee swung outward round the hip-to-ankle line
  shoulder_up/fwd, arm_fwd/out/twist, arm_hang (0..1: hangs plumb however the chest leans)
  elbow, wrist_curl/side, hand_twist
  curl_<finger>, spread, thumb_curl, thumb_in
  give                            0..1: how far the ground pushes the fingers and thumb back where they leave the
                                  palm, which keeps their claws on it instead of under it
  planted                         0..1: how far the arm leaves the controls above to reach where its hand is put
  hand_x/y/z, hand_yaw/pitch/roll the palm of a planted hand, flat with its fingers forward, from the ground under
                                  the shoulder; pitch lifts its heel off the finger pads, yaw turns the fingers out
  elbow_out                       a planted arm's elbow swung outward round the shoulder-to-wrist line
  jaw                             the jaw dropped open, on a rig that has one
"""
import bpy
import numpy as np
from mathutils import Matrix
from sculpt import sdf as S
from sculpt.sdf import V
from sculpt.num import smoothstep
from . import body, rig
from .rig import HIP, KNEE, ANKLE, PELVIS, WAIST, CHEST, STERNUM, SHOULDER, ELBOW, WRIST, UPPER, FORE, FINGERWARD, HF

X, Y, Z, SAME = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1), np.eye(3)
FLIP = np.diag(rig.MIRROR)
SOLE, BALL, HEEL = (p * V(1, 1, 0) for p in (ANKLE, rig.BALL, body.from_foot((0, -0.045, 0))[0]))
OUTWARD, TOEWARD = (body.from_foot(d)[0] - body.from_foot((0, 0, 0))[0] for d in ((1, 0, 0), (0, 1, 0)))
ELBOW_HINGE = np.cross(FORE, body.FWD)
ACROSS_PALM, BACK_OF_HAND = HF.dir(V(0, 1, 0)), HF.dir(V(1, 0, 0))
FAN = dict(pinky=-1.0, ring=-0.4, middle=0.1, index=0.8)          # how far each finger spreads
CURL = (0.9, 1.0, 0.7)                                           # each knuckle's share of a finger's curl
_thumb = HF.dir(S.normalize(body.THUMB["chain"][1] - body.THUMB["chain"][0]))
THUMB_HINGE = np.cross(_thumb, -BACK_OF_HAND - ACROSS_PALM)       # closes the thumb across the palm
GIVES, SOFT = np.radians(np.arange(0.0, 101.0)), 0.012            # how far the ground can open a digit at its knuckle
PALM = SHOULDER * V(1, 1, 0)
LAID_FLAT = np.stack([Z, -X, -Y], axis=1) @ HF.R.T                # the rest hand to palm down, fingers forward, thumb inward
WRIST_UP, PADS = V(0, 0, 0.016), V(0, -0.088, 0)                  # from the heel of a flat hand: its wrist, its finger pads
ARM_HINGE = S.normalize(np.cross(UPPER, FORE))
ELBOW_BACK = V(0.3, 1.0, 0.0)
FOREARM_TWIST = 0.5                                              # the share of the hand's twist that the forearm takes up
MOVED = ("root", "hips")


def _touching(digit, at):
    """A digit's bones as the rig cuts them: each one's head, and where the ground can touch it and how thick it
    is there. Each carries the joints up to its end, and the last the point of the claw."""
    pts, (flesh, radii), (claw, sharp) = HF.w(np.array(digit["chain"])), digit["flesh"], digit["claw"]
    thick = dict(zip(map(tuple, flesh), radii))
    bones = [(pts[a], [(pts[i], thick[tuple(digit["chain"][i])]) for i in range(a + 1, b + 1)]) for a, b in zip(at, at[1:])]
    bones[-1][1].append((HF.w(np.array(claw[-1])), sharp[-1]))
    return bones


TOUCHING = {name: _touching(*digit) for name, digit in rig.DIGITS.items()}


def turn(axis, degrees):
    x, y, z = S.normalize(np.asarray(axis, dtype=np.float64))
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    a = np.radians(degrees)
    return SAME + np.sin(a) * k + (1.0 - np.cos(a)) * (k @ k)


def lean(pitch, roll, yaw):
    return turn(Z, yaw) @ turn(Y, roll) @ turn(X, pitch)


def part(r, share):
    """The rotation `r` carried only `share` of the way from rest."""
    angle = np.arccos(np.clip((np.trace(r) - 1.0) / 2.0, -1.0, 1.0))
    if angle < 1e-9:
        return SAME
    axis = V(r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1])
    return turn(axis, np.degrees(angle) * share)


def twist(r, axis):
    """Degrees of the turn about `axis` within the rotation `r`."""
    w = 0.5 * np.sqrt(max(1.0 + np.trace(r), 1e-12))
    return np.degrees(2.0 * np.arctan2(V(r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]) @ axis / (4.0 * w), w))


def _hinged(along_, hinge):
    return np.stack([hinge, np.cross(along_, hinge), along_], axis=1)


def _bent(top, end, a, b, pole):
    """A two-boned limb from `top` toward `end`, its joint on the side that `pole` (a function of the limb's
    direction) points to: the directions of its bones, of lengths a and b, its hinge, and how far short of
    `end` it falls."""
    reach = np.linalg.norm(end - top)
    d = np.clip(reach, abs(a - b) + 1e-4, a + b - 1e-4)
    u = (end - top) / reach
    pole = pole(u)
    v = S.normalize(pole - u * (pole @ u))
    bend = (a * a + d * d - b * b) / (2 * a * d)
    joint = top + a * (bend * u + np.sqrt(1.0 - bend * bend) * v)
    upper, lower = S.normalize(joint - top), S.normalize(top + d * u - joint)
    return upper, lower, S.normalize(np.cross(upper, lower)), reach - d


def _clearing(held, opens, curls, bones, knuckle):
    """The turn in degrees about `opens` at a digit's knuckle by which the ground opens it: the least of GIVES
    that lifts all of it clear, or the one that comes nearest to. A digit less than SOFT under the ground is
    opened only part of the way, so that it leaves the ground and meets it without a snap. The digit is held
    as `held` at the knuckle and curled by `curls` at joint after joint; `bones` is its entry in TOUCHING."""
    opens, up = S.normalize(opens), held[2]
    heights, bent, joint = [], SAME, np.zeros(3)
    for (head, points), curl, (beyond, _) in zip(bones, curls, bones[1:] + bones[-1:]):
        bent = bent @ turn(opens, -curl)
        for point, radius in points:
            w = joint + bent @ (point - head)
            along_ = opens * (opens @ w)
            heights.append((knuckle[2] + up @ along_ - radius, up @ (w - along_), up @ np.cross(opens, w)))
        joint = joint + bent @ (beyond - head)
    level, flat, tipped = np.array(heights).T[..., None]
    clear = (level + flat * np.cos(GIVES) + tipped * np.sin(GIVES)).min(0)
    first = int(np.argmax(clear >= 0.0))
    if clear[first] < 0.0:
        first, under = int(np.argmax(clear)), 0.0
    elif first:
        under = clear[first] / (clear[first] - clear[first - 1])
    else:
        return 0.0
    return float(np.degrees(GIVES[first] - under * (GIVES[first] - GIVES[first - 1])) * smoothstep(0.0, SOFT, -clear[0]))


def _leg(c, hips, pelvis):
    """The left leg's bones, reaching from the posed pelvis to where the foot is put, and how far short they fall."""
    flat = turn(Z, c("foot_yaw"))
    foot = flat @ turn(OUTWARD, c("foot_pitch")) @ turn(TOEWARD, c("foot_roll"))
    pivot = BALL if c("foot_pitch") > 0 else HEEL
    ankle = SOLE + V(c("foot_x"), c("foot_y"), c("foot_z")) + flat @ (pivot - SOLE) + foot @ (ANKLE - pivot)
    hip = pelvis + hips @ (HIP - PELVIS)
    behind = KNEE - HIP - S.normalize(ANKLE - HIP) * ((KNEE - HIP) @ S.normalize(ANKLE - HIP))
    thigh, shin, hinge, short = _bent(hip, ankle, np.linalg.norm(KNEE - HIP), np.linalg.norm(ANKLE - KNEE),
                                      lambda u: turn(u, c("knee")) @ (hips @ behind + flat @ behind))
    rest = S.normalize(np.cross(body.THIGH, body.SHIN))
    return {"thigh_l": _hinged(thigh, hinge) @ _hinged(body.THIGH, rest).T,
            "shin_l": _hinged(shin, hinge) @ _hinged(body.SHIN, rest).T,
            "foot_l": foot, "toe_l": foot @ turn(OUTWARD, -c("toe"))}, short


def _reach(c, chest, shoulder):
    """The left arm's bones below the shoulder, reaching to where the hand is put, and how far short they fall."""
    flat = turn(Z, c("hand_yaw"))
    hand = flat @ turn(X, c("hand_pitch")) @ turn(Y, c("hand_roll"))
    pivot = PADS if c("hand_pitch") > 0 else V(0, 0, 0)
    wrist = PALM + V(c("hand_x"), c("hand_y"), c("hand_z")) + flat @ pivot + hand @ (WRIST_UP - pivot)
    upper, fore, hinge, short = _bent(shoulder, wrist, np.linalg.norm(ELBOW - SHOULDER), np.linalg.norm(WRIST - ELBOW),
                                      lambda u: turn(u, c("elbow_out")) @ (chest @ ELBOW_BACK + Y))
    hand = hand @ LAID_FLAT
    fore = _hinged(fore, hinge) @ _hinged(FORE, ARM_HINGE).T
    fore = fore @ turn(FORE, FOREARM_TWIST * twist(fore.T @ hand, FORE))
    return (_hinged(upper, hinge) @ _hinged(UPPER, ARM_HINGE).T, fore, hand), short


def _arm(c, chest, sternum):
    """The left arm's bones, and how far short of a planted hand they fall."""
    clavicle = chest @ turn(Y, -c("shoulder_up")) @ turn(Z, -c("shoulder_fwd"))
    upper = part(clavicle, 1.0 - c("arm_hang")) @ turn(X, -c("arm_fwd")) @ turn(Y, -c("arm_out")) @ turn(UPPER, c("arm_twist"))
    fore = upper @ turn(ELBOW_HINGE, c("elbow"))
    hand = fore @ turn(FINGERWARD, c("hand_twist")) @ turn(ACROSS_PALM, -c("wrist_curl")) @ turn(BACK_OF_HAND, c("wrist_side"))
    shoulder, short = sternum + clavicle @ (SHOULDER - STERNUM), 0.0
    if c("planted") > 0.0:
        reached, short = _reach(c, chest, shoulder)
        upper, fore, hand = (free @ part(free.T @ put, c("planted")) for free, put in zip((upper, fore, hand), reached))
    out = {"clavicle_l": clavicle, "upperarm_l": upper, "forearm_l": fore, "hand_l": hand}
    wrist = shoulder + upper @ (ELBOW - SHOULDER) + fore @ (WRIST - ELBOW)

    def digit(name, held, opens, curls):
        bones = TOUCHING[name]
        at = held @ turn(opens, c("give") * _clearing(held, opens, curls, bones, wrist + hand @ (bones[0][0] - WRIST)))
        for k, curl in enumerate(curls, 1):
            at = out["%s_%d_l" % (name, k)] = at @ turn(opens, -curl)
    for name, fan in FAN.items():
        digit(name, hand @ turn(BACK_OF_HAND, fan * c("spread")), ACROSS_PALM, [share * c("curl_" + name) for share in CURL])
    digit("thumb", hand @ turn(BACK_OF_HAND, c("thumb_in")), -THUMB_HINGE, [0.5 * c("thumb_curl"), c("thumb_curl")])
    return out, short * c("planted")


def solve(controls):
    """Every bone's rotation from rest about its own head, as name -> 3x3; where root and hips have moved to;
    and how far the targets of the feet and planted hands lie beyond the limbs' reach."""
    def c(name):
        return controls.get(name, 0.0)

    def turns(bone):
        return lean(c(bone + "_pitch"), c(bone + "_roll"), c(bone + "_yaw"))
    hips = turns("hips")
    spine = hips @ turns("spine")
    chest = spine @ turns("chest")
    neck = part(chest, 1.0 - 0.5 * c("head_level")) @ turns("neck")
    head = part(chest, 1.0 - c("head_level")) @ turns("neck") @ turns("head")
    out = {"root": SAME, "hips": hips, "spine": spine, "chest": chest, "neck": neck, "head": head,
           "jaw": head @ turn(X, c("jaw"))}
    moves = {"root": V(0, -c("travel"), 0), "hips": V(c("hips_x"), c("hips_y"), c("hips_z"))}
    pelvis = PELVIS + moves["hips"]
    sternum = pelvis + hips @ (WAIST - PELVIS) + spine @ (CHEST - WAIST) + chest @ (STERNUM - CHEST)
    overreach = 0.0
    for side, m in (("_l", SAME), ("_r", FLIP)):
        def sided(name):
            return c(name + side)
        leg, short = _leg(sided, m @ hips @ m, pelvis * np.diag(m))
        arm, far = _arm(sided, m @ chest @ m, sternum * np.diag(m))
        overreach = max(overreach, short, far)
        out.update({name[:-2] + side: m @ r @ m for name, r in dict(arm, **leg).items()})
    return out, moves, overreach


def strike(ob, controls):
    """Put the rig in a pose. Returns how far the targets of its feet and planted hands lie beyond reach."""
    turned, moves, overreach = solve(controls)
    for pb in ob.pose.bones:
        rest = np.array(pb.bone.matrix_local)[:3, :3]
        above = turned[pb.parent.name] if pb.parent else SAME
        pb.rotation_quaternion = Matrix((rest.T @ above.T @ turned[pb.name] @ rest).tolist()).to_quaternion()
        if pb.name in MOVED:
            pb.location = rest.T @ above.T @ moves[pb.name]
    return overreach


def use(ob, action):
    ob.animation_data_create().action = action
    if action and action.slots:
        ob.animation_data.action_slot = action.slots[0]


def shelve(ob, actions):
    """Lay each clip on a track of its own, which is how the GLB exporter tells clips apart."""
    use(ob, None)
    for action in actions:
        track = ob.animation_data.nla_tracks.new()
        track.name = action.name
        track.strips.new(action.name, 0, action).action_slot = action.slots[0]


def record(ob, name, clip, frames):
    """Key a looping clip on every bone at every frame: clip(phase in 0..1) -> controls. The last frame
    repeats the first, a stride further on."""
    action = bpy.data.actions.new(name)
    use(ob, action)
    before, overreach = {}, 0.0
    for frame in range(frames + 1):
        overreach = max(overreach, strike(ob, clip(frame / frames)))
        for pb in ob.pose.bones:
            q = pb.rotation_quaternion.copy()
            if pb.name in before and before[pb.name].dot(q) < 0:
                q.negate()
            pb.rotation_quaternion = before[pb.name] = q
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            if pb.name in MOVED:
                pb.keyframe_insert("location", frame=frame)
    print("CLIP %-7s %d frames  %.2f s%s" % (name, frames, frames / bpy.context.scene.render.fps,
                                             "  LIMBS %.0f mm OUT OF REACH" % (overreach * 1e3) if overreach > 1e-4 else ""))
    return action

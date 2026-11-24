"""Poses the grinner's rig from an animator's controls, and records clips of them.

A pose is a dict of named controls, zero at rest: angles in degrees, lengths in metres. The body is turned
bone by bone; each foot is put where it should stand and its leg solved to reach it; paired controls end in
_l or _r and mean the same on both sides. `solve` turns controls into every bone's rotation from rest, in the
figure's axes (+X its left, -Y forward, +Z up).

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
"""
import bpy
import numpy as np
from mathutils import Matrix
from sculpt import sdf as S
from sculpt.sdf import V
from . import body, rig
from .rig import HIP, KNEE, ANKLE, PELVIS, UPPER, FORE, FINGERWARD, HF

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
MOVED = ("root", "hips")


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


def _hinged(along_, hinge):
    return np.stack([hinge, np.cross(along_, hinge), along_], axis=1)


def _leg(c, hips, pelvis):
    """The left leg's bones, reaching from the posed pelvis to where the foot is put, and how far short they fall."""
    flat = turn(Z, c("foot_yaw"))
    foot = flat @ turn(OUTWARD, c("foot_pitch")) @ turn(TOEWARD, c("foot_roll"))
    pivot = BALL if c("foot_pitch") > 0 else HEEL
    ankle = SOLE + V(c("foot_x"), c("foot_y"), c("foot_z")) + flat @ (pivot - SOLE) + foot @ (ANKLE - pivot)
    hip = pelvis + hips @ (HIP - PELVIS)
    a, b = np.linalg.norm(KNEE - HIP), np.linalg.norm(ANKLE - KNEE)
    reach = np.linalg.norm(ankle - hip)
    d = np.clip(reach, abs(a - b) + 1e-4, a + b - 1e-4)
    u = (ankle - hip) / reach
    behind = KNEE - HIP - S.normalize(ANKLE - HIP) * ((KNEE - HIP) @ S.normalize(ANKLE - HIP))
    pole = turn(u, c("knee")) @ (hips @ behind + flat @ behind)
    v = S.normalize(pole - u * (pole @ u))
    bend = (a * a + d * d - b * b) / (2 * a * d)
    knee = hip + a * (bend * u + np.sqrt(1.0 - bend * bend) * v)
    thigh, shin = S.normalize(knee - hip), S.normalize(hip + d * u - knee)
    rest = S.normalize(np.cross(body.THIGH, body.SHIN))
    hinge = S.normalize(np.cross(thigh, shin))
    return {"thigh_l": _hinged(thigh, hinge) @ _hinged(body.THIGH, rest).T,
            "shin_l": _hinged(shin, hinge) @ _hinged(body.SHIN, rest).T,
            "foot_l": foot, "toe_l": foot @ turn(OUTWARD, -c("toe"))}, reach - d


def _arm(c, chest):
    clavicle = chest @ turn(Y, -c("shoulder_up")) @ turn(Z, -c("shoulder_fwd"))
    upper = part(clavicle, 1.0 - c("arm_hang")) @ turn(X, -c("arm_fwd")) @ turn(Y, -c("arm_out")) @ turn(UPPER, c("arm_twist"))
    fore = upper @ turn(ELBOW_HINGE, c("elbow"))
    hand = fore @ turn(FINGERWARD, c("hand_twist")) @ turn(ACROSS_PALM, -c("wrist_curl")) @ turn(BACK_OF_HAND, c("wrist_side"))
    out = {"clavicle_l": clavicle, "upperarm_l": upper, "forearm_l": fore, "hand_l": hand}
    for name, fan in FAN.items():
        at = hand @ turn(BACK_OF_HAND, fan * c("spread"))
        for k, share in enumerate(CURL, 1):
            at = out["%s_%d_l" % (name, k)] = at @ turn(ACROSS_PALM, -share * c("curl_" + name))
    out["thumb_1_l"] = hand @ turn(BACK_OF_HAND, c("thumb_in")) @ turn(THUMB_HINGE, 0.5 * c("thumb_curl"))
    out["thumb_2_l"] = out["thumb_1_l"] @ turn(THUMB_HINGE, c("thumb_curl"))
    return out


def solve(controls):
    """Every bone's rotation from rest about its own head, as name -> 3x3; where root and hips have moved to;
    and how far the feet's targets lie beyond the legs' reach."""
    def c(name):
        return controls.get(name, 0.0)

    def turns(bone):
        return lean(c(bone + "_pitch"), c(bone + "_roll"), c(bone + "_yaw"))
    hips = turns("hips")
    spine = hips @ turns("spine")
    chest = spine @ turns("chest")
    neck = part(chest, 1.0 - 0.5 * c("head_level")) @ turns("neck")
    out = {"root": SAME, "hips": hips, "spine": spine, "chest": chest, "neck": neck,
           "head": part(chest, 1.0 - c("head_level")) @ turns("neck") @ turns("head")}
    moves = {"root": V(0, -c("travel"), 0), "hips": V(c("hips_x"), c("hips_y"), c("hips_z"))}
    overreach = 0.0
    for side, m in (("_l", SAME), ("_r", FLIP)):
        def sided(name):
            return c(name + side)
        leg, short = _leg(sided, m @ hips @ m, (PELVIS + moves["hips"]) * np.diag(m))
        overreach = max(overreach, short)
        out.update({name[:-2] + side: m @ r @ m for name, r in dict(_arm(sided, m @ chest @ m), **leg).items()})
    return out, moves, overreach


def strike(ob, controls):
    """Put the rig in a pose. Returns how far the feet's targets lie beyond the legs' reach."""
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
                                             "  FEET %.0f mm OUT OF REACH" % (overreach * 1e3) if overreach > 1e-4 else ""))
    return action

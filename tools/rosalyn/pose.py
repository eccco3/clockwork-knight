"""Poses Rosalyn's rig from an animator's controls, and records clips of them.

A pose is a dict of named controls, zero at rest: angles in degrees, lengths in metres. The body is turned
bone by bone; each foot and each hand is put where it should be and its limb solved to reach it; paired
controls end in _l or _r and mean the same on both sides. `solve` turns controls into every bone's rotation
from rest, in the figure's axes (+X her left, -Y forward, +Z up).

  hips_x/y/z, hips_pitch/roll/yaw the pelvis; pitch bows forward, roll leans left, yaw turns left
  spine_, chest_, neck_, head_    the same three turns, each on top of the bone below
  head_level                      0..1: how far the head ignores the body's lean
  eye_yaw, eye_up, blink          both eyes turned to her left and upward; 0..1: the lids shut
  foot_x/y/z, foot_yaw/pitch/roll the sole under the ankle; pitch lifts the heel off the ball (or, negative,
                                  the toes off the heel), yaw turns the toes out
  knee                            the knee swung outward round the hip-to-ankle line
  shoulder_up/fwd                 the collarbone
  hand_x/y/z                      the wrist, carried by the hips: outward, back and up from where it hangs
  hand_yaw/roll/pitch             the hand in the hips' axes, one after another: yaw turns the palm in to face
                                  the body, roll swings the fingers across her front, pitch tips them forward
  elbow                           the elbow swung outward round the shoulder-to-wrist line
  curl_<finger>, spread           each finger closed; the fingers fanned apart
  thumb_curl, thumb_in, thumb_lift the thumb closed, drawn in beside the forefinger, and raised off the palm
  skirt_hang                      0..1: the skirt hangs plumb however the hips lean
  skirt_x/y/twist, hem_x/y/twist  the skirt swung to her left, swung back and turned left; its lower half more
"""
import numpy as np
from sculpt import sdf as S, rig as R
from sculpt.sdf import V
from sculpt.turns import X, Y, Z, SAME, FLIP, MIRROR, turn, lean, part, between, twist, hinged, reach
from . import body, head, rig
from .rig import HIP, KNEE, ANKLE, PELVIS, WAIST, CHEST, STERNUM, SHOULDER, ELBOW, WRIST, UPPER, FORE, THIGH, SHIN, HF

SOLE, BALL, HEEL = (p * V(1, 1, 0) for p in (ANKLE, rig.BALL, rig.HEEL))
OUTWARD, TOEWARD = (body.from_foot(d)[0] - body.from_foot((0, 0, 0))[0] for d in ((1, 0, 0), (0, 1, 0)))
KNEE_HINGE, ELBOW_HINGE = S.normalize(np.cross(THIGH, SHIN)), S.normalize(np.cross(UPPER, FORE))
ACROSS_PALM, BACK_OF_HAND = HF.dir(V(0, 1, 0)), HF.dir(V(1, 0, 0))
FAN = dict(pinky=-1.0, ring=-0.4, middle=0.1, index=0.8)          # how far each finger spreads
CURL = (0.9, 1.0, 0.7)                                           # each knuckle's share of a finger's curl
THUMB_HINGE = np.cross(HF.dir(S.normalize(body.THUMB["joints"][2] - body.THUMB["joints"][1])), -BACK_OF_HAND - ACROSS_PALM)
MOVED = ("root", "hips")
COLUMNS = {name: (S.normalize((head_ - PELVIS) * V(1, 1, 0)), parent != "hips")
           for name, parent, head_, tail in rig.BONES if name.startswith("skirt")}     # each one's way out, and if it is a lower half


def _bent(root, target, upper, lower, hinge, pole, swing):
    """A limb's two bones from `root` to `target`, their rest directions and hinge given, the joint between
    them toward `pole` and swung `swing` degrees round the line it spans; and how far short it falls."""
    a, b = (np.linalg.norm(x) for x in (upper, lower))
    pole = turn(target - root, swing) @ pole
    first, second, bend, short = reach(root, target, a, b, pole)
    rest = lambda way: hinged(S.normalize(way), hinge).T
    return hinged(first, bend) @ rest(upper), hinged(second, bend) @ rest(lower), short


def _aside(joint, root, end):
    """Where a limb's middle joint stands off the line from its root to its end."""
    line = S.normalize(end - root)
    return joint - root - line * ((joint - root) @ line)


def _leg(c, hips, pelvis):
    flat = turn(Z, c("foot_yaw"))
    foot = flat @ turn(OUTWARD, c("foot_pitch")) @ turn(TOEWARD, c("foot_roll"))
    pivot = BALL if c("foot_pitch") > 0 else HEEL
    ankle = SOLE + V(c("foot_x"), c("foot_y"), c("foot_z")) + flat @ (pivot - SOLE) + foot @ (ANKLE - pivot)
    ahead = _aside(KNEE, HIP, ANKLE)
    thigh, shin, short = _bent(pelvis + hips @ (HIP - PELVIS), ankle, KNEE - HIP, ANKLE - KNEE, KNEE_HINGE,
                               hips @ ahead + flat @ ahead, -c("knee"))
    return {"thigh_l": thigh, "shin_l": shin, "foot_l": foot}, short


def _arm(c, hips, pelvis, chest, sternum):
    clavicle = chest @ turn(Y, -c("shoulder_up")) @ turn(Z, -c("shoulder_fwd"))
    hand = hips @ turn(X, -c("hand_pitch")) @ turn(Y, c("hand_roll")) @ turn(Z, -c("hand_yaw"))
    wrist = pelvis + hips @ (WRIST + V(c("hand_x"), c("hand_y"), c("hand_z")) - PELVIS)
    upper, fore, short = _bent(sternum + clavicle @ (SHOULDER - STERNUM), wrist, ELBOW - SHOULDER, WRIST - ELBOW, ELBOW_HINGE,
                               chest @ _aside(ELBOW, SHOULDER, WRIST), c("elbow"))
    out = {"clavicle_l": clavicle, "upperarm_l": upper, "forearm_l": fore, "hand_l": hand,
           "wrist_l": fore @ turn(FORE, twist(fore.T @ hand, FORE))}
    for name, fan in FAN.items():
        at = hand @ turn(BACK_OF_HAND, fan * c("spread"))
        for k, share in enumerate(CURL, 1):
            at = out["%s_%d_l" % (name, k)] = at @ turn(ACROSS_PALM, -share * c("curl_" + name))
    out["thumb_1_l"] = hand @ turn(rig.FINGERWARD, -c("thumb_lift")) @ turn(BACK_OF_HAND, c("thumb_in"))         @ turn(THUMB_HINGE, 0.3 * c("thumb_curl"))
    out["thumb_2_l"] = out["thumb_1_l"] @ turn(THUMB_HINGE, 0.7 * c("thumb_curl"))
    out["thumb_3_l"] = out["thumb_2_l"] @ turn(THUMB_HINGE, c("thumb_curl"))
    return out, short


def _skirt(c, hips):
    lean_ = between(Z, hips @ Z)
    plumb = part(lean_, 1.0 - c("skirt_hang")) @ lean_.T @ hips
    swung = plumb @ turn(X, c("skirt_y")) @ turn(Y, -c("skirt_x"))
    out = {}
    for name, (outward, lower) in COLUMNS.items():
        out[name] = swung @ turn(outward, c("skirt_twist"))
        if lower:
            out[name] = out[name] @ turn(X, c("hem_y")) @ turn(Y, -c("hem_x")) @ turn(outward, c("hem_twist"))
    return out


def solve(controls):
    """Every bone's rotation from rest about its own head, as name -> 3x3; where root and hips have moved to;
    and how far the feet's and hands' targets lie beyond their limbs' reach."""
    def c(name):
        return controls.get(name, 0.0)

    def turns(bone):
        return lean(c(bone + "_pitch"), c(bone + "_roll"), c(bone + "_yaw"))
    hips = turns("hips")
    spine = hips @ turns("spine")
    chest = spine @ turns("chest")
    head_ = part(chest, 1.0 - c("head_level")) @ turns("neck") @ turns("head")
    eye = head_ @ turn(Z, c("eye_yaw")) @ turn(X, -c("eye_up"))
    out = {"root": SAME, "hips": hips, "spine": spine, "chest": chest, "head": head_, "eye_l": eye, "eye_r": eye,
           "neck": part(chest, 1.0 - 0.5 * c("head_level")) @ turns("neck")}
    out.update(_skirt(c, hips))
    moves = {"root": V(0, 0, 0), "hips": V(c("hips_x"), c("hips_y"), c("hips_z"))}
    pelvis = PELVIS + moves["hips"]
    sternum = pelvis + hips @ (WAIST - PELVIS) + spine @ (CHEST - WAIST) + chest @ (STERNUM - CHEST)
    strain = 0.0
    for side, m in (("_l", SAME), ("_r", FLIP)):
        def sided(name):
            return c(name + side)
        mirrored = lambda r: m @ r @ m
        leg, far = _leg(sided, mirrored(hips), pelvis * np.diag(m))
        arm, short = _arm(sided, mirrored(hips), pelvis * np.diag(m), mirrored(chest), sternum * np.diag(m))
        strain = max(strain, far, short)
        lid = mirrored(head_) @ turn(rig.LID_HINGE, head.LID_SHUT * c("blink"))
        out.update({name[:-2] + side: mirrored(r) for name, r in dict(arm, **leg, lid_l=lid).items()})
    return out, moves, strain


def strike(ob, controls):
    """Put the rig in a pose. Returns how far the limbs' targets lie beyond their reach."""
    turned, moves, strain = solve(controls)
    R.strike(ob, turned, moves)
    return strain


def record(ob, name, clip, frames):
    """Key a clip on every bone at every frame: clip(phase in 0..1) -> controls."""
    return R.record(ob, name, frames, lambda phase: strike(ob, clip(phase)), MOVED)

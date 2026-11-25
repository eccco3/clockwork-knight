"""Rosalyn's skeleton and skin.

Seventy-two bones stand on the sculpt's landmarks: a root, five up the middle, an eye and its sleeping lid on
each side, an arm of five with fifteen in the hand, a leg of three, and sixteen in the skirt, which hangs in
eight columns of two. `wrist` carries the forearm's twist, so the hand turns over without wringing the arm.

Whatever is carved or cast in one piece rides one bone: her head from the choker up, her hair, eyes, lids and
brass. The rest is skinned by a field over the rest pose: `weights` gives any point its bones, so every mesh
binds by where its points lie, at each detail.
"""
import numpy as np
from sculpt import sdf as S, rig as R
from sculpt.sdf import V
from sculpt.gen import Frame
from sculpt.num import smoothstep, lerp, along
from sculpt.rig import beyond, near, chain, twin
from . import body, head, dress
from .body import HIP, KNEE, ANKLE, SHOULDER, ELBOW, WRIST, NECK_A, CHOKER, NECK_DIR, HF, UP, FWD, LEFT

PELVIS = V(0, HIP[1], HIP[2])
WAIST, CHEST = V(0, 0.008, 1.045), V(0, 0.006, 1.250)
CROWN = body.HEAD.w(V(0, 0, 0.090))
STERNUM = V(0.020, -0.030, 1.432)             # the collarbone's inner end
UPPER, FORE = S.normalize(ELBOW - SHOULDER), S.normalize(WRIST - ELBOW)
THIGH, SHIN = S.normalize(KNEE - HIP), S.normalize(ANKLE - KNEE)
TWIST = lerp(ELBOW, WRIST, 0.5)               # where the bone that twists the forearm begins
FINGERWARD = HF.dir(V(0, 0, 1))
KNUCKLES = HF.w(V(0, 0, 0.092))
HEEL, BALL = body.from_foot([(0, -0.045, 0.012), (0, 0.095, 0.012)])
DIGITS = dict(body.FINGERS, thumb=body.THUMB)
EYE = Frame(body.HEAD.w(head.EYE * R.MIRROR), FWD * np.cos(head.EYE_TURN) + LEFT * np.sin(head.EYE_TURN), LEFT)
LID_HINGE = body.HEAD.dir(head.LID_HINGE * R.MIRROR)          # the left lid shuts by turning head.LID_SHUT about this

HIPLINE, FLOUNCE = 0.930, 0.615               # heights at which the skirt's columns begin, and their lower halves
SKIRT = dict(front=0.0, fore=45.0, side=90.0, aft=135.0, back=180.0)        # columns, in degrees round from the front
SKIRT_MIDDLE = V(0, 0.012, 0)


def _digit_bones():
    for name, g in DIGITS.items():
        pts = HF.w(np.array(g["joints"]))
        for k in (1, 2, 3):
            yield "%s_%d_l" % (name, k), "%s_%d_l" % (name, k - 1) if k > 1 else "hand_l", pts[k - 1], pts[k]


def _column(name, half):
    return "skirt_%s_%d%s" % (name, half, "" if SKIRT[name] in (0.0, 180.0) else "_l")


def _skirt_bones():
    for name, degrees in SKIRT.items():
        out = V(np.sin(np.radians(degrees)), -np.cos(np.radians(degrees)), 0)
        top, mid, hem = (SKIRT_MIDDLE + UP * z + out * r for z, r in ((HIPLINE, 0.115), (FLOUNCE, 0.200), (dress.Z_HEM, 0.270)))
        yield _column(name, 1), "hips", top, mid
        yield _column(name, 2), _column(name, 1), mid, hem


BONES = list(R.both_sides([
    ("root", None, V(0, 0, 0), V(0, 0, 0.15)),
    ("hips", "root", PELVIS, WAIST), ("spine", "hips", WAIST, CHEST), ("chest", "spine", CHEST, NECK_A),
    ("neck", "chest", NECK_A, CHOKER), ("head", "neck", CHOKER, CROWN),
    ("eye_l", "head", EYE.o, EYE.w(V(0, 0, 0.030))), ("lid_l", "head", EYE.o, EYE.o + LID_HINGE * 0.030),
    ("clavicle_l", "chest", STERNUM, SHOULDER), ("upperarm_l", "clavicle_l", SHOULDER, ELBOW),
    ("forearm_l", "upperarm_l", ELBOW, TWIST), ("wrist_l", "forearm_l", TWIST, WRIST),
    ("hand_l", "wrist_l", WRIST, KNUCKLES), *_digit_bones(),
    ("thigh_l", "hips", HIP, KNEE), ("shin_l", "thigh_l", KNEE, ANKLE), ("foot_l", "shin_l", ANKLE, BALL),
    *_skirt_bones()]))
NAMES = [bone[0] for bone in BONES]


def armature(name):
    return R.armature(name, BONES)


def weigh(ob, bone=None, right=False):
    """Skin a mesh of the figure: to `bone` alone if it rides one (its twin, for the right side's of a pair
    described on the left), or else by where its points stand."""
    if bone is None:
        R.weigh(ob, NAMES, weights(R.points(ob)))
    else:
        side = bone + ("_r" if right else "_l")
        R.weigh(ob, [side if side in NAMES else bone], np.ones((len(ob.data.vertices), 1)))


# ---------------------------------------------------------------- the skin

def _leg(q):
    limb = np.maximum(near(q, [lerp(KNEE, HIP, 0.35), KNEE, ANKLE], [0.075, 0.070, 0.055], 0.012),
                      near(q, [HEEL, BALL + (BALL - HEEL) * 0.5], 0.060, 0.012))
    shin = limb * beyond(q, KNEE, THIGH + SHIN, 0.030, 0.030)
    foot = shin * beyond(q, ANKLE, SHIN, 0.025, 0.020)
    return chain(("thigh_l", limb), ("shin_l", shin), ("foot_l", foot))


def _digits(l):
    """Each digit bone's share of a point of the hand, in the hand's frame."""
    lines = {name: np.array(g["joints"]) for name, g in DIGITS.items()}
    off = {name: S.tube(l, line, 0.0) for name, line in lines.items()}
    out = {}
    for name, line in lines.items():
        rival = np.minimum.reduce([d for other, d in off.items() if other != name])
        hold = np.clip((rival - off[name]) / 0.006 + 0.5, 0.0, 1.0) * smoothstep(0.020, 0.010, off[name]) \
            * beyond(l, line[0], line[1] - line[0], 0.010, 0.006)
        holds = [hold]
        for j in (1, 2):
            holds.append(holds[-1] * beyond(l, line[j], S.normalize(line[j] - line[j - 1])
                                            + S.normalize(line[j + 1] - line[j]), 0.005, 0.005))
        out.update(chain(*(("%s_%d_l" % (name, k), h) for k, h in enumerate(holds, 1))))
    return out


def _arm(q):
    sleeve = near(q, [SHOULDER, ELBOW, WRIST, KNUCKLES, HF.w(V(0, 0, 0.20))], [0.080, 0.055, 0.045, 0.080, 0.090], 0.012)
    flesh = np.minimum(body.upper_arm(q), body.arm(q))
    sleeve = sleeve * smoothstep(-0.030, 0.030, body.trunk(q) - flesh)                        # the bodice keeps to the ribs
    upper = sleeve * beyond(q, SHOULDER, UPPER, 0.020, 0.070)
    girdle = np.maximum(smoothstep(0.110, 0.045, S.length(q - SHOULDER)), upper)
    fore = upper * beyond(q, ELBOW, UPPER + FORE, 0.030, 0.030)
    down, _ = along(q, ELBOW, WRIST)
    turned = fore * smoothstep(0.25, 0.92, down / np.linalg.norm(WRIST - ELBOW))
    hand = fore * beyond(q, WRIST, FORE + FINGERWARD, 0.016, 0.016)
    out = chain(("clavicle_l", girdle), ("upperarm_l", upper), ("forearm_l", fore), ("wrist_l", turned), ("hand_l", hand))
    for name, share in _digits(HF.l(q)).items():
        out[name] = hand * share
        out["hand_l"] = out["hand_l"] - out[name]
    return out


def _skirt(q):
    """The skirt's columns' shares of what the hips hold."""
    z = q[:, 2]
    hangs = smoothstep(1.000, 0.860, z)
    low = hangs * smoothstep(0.700, 0.530, z)
    round_ = np.degrees(np.arctan2(q[:, 0], -(q[:, 1] - SKIRT_MIDDLE[1])))
    out = {}
    for name, degrees in SKIRT.items():
        column = smoothstep(45.0, 0.0, np.abs(round_ - degrees))
        out[_column(name, 1)], out[_column(name, 2)] = column * (hangs - low), column * low
    return out


def _middle(p):
    up, out = along(p, NECK_A, CHOKER)
    wide = smoothstep(0.052, 0.078, out)
    spine = beyond(p, WAIST, UP, 0.040, 0.040)
    chest = spine * beyond(p, CHEST, UP, 0.045, 0.045)
    neck = chest * smoothstep(-0.006, 0.030, up) * (1.0 - wide * smoothstep(0.045, 0.025, up))      # not the shoulders
    top = np.linalg.norm(CHOKER - NECK_A)
    head_ = neck * smoothstep(top - 0.030, top - 0.005, up)
    return chain(("hips", np.ones(len(p))), ("spine", spine), ("chest", chest), ("neck", neck), ("head", head_))


def weights(p):
    """An (N, bones) array: each rest-pose point's share in every bone of NAMES, rows summing to one."""
    q = S.mirror_x(p)
    limbs = dict(_arm(q), **_leg(q))
    held = np.minimum(sum(limbs.values()), 1.0)
    middle = {name: share * (1.0 - held) for name, share in _middle(p).items()}
    paired = dict(limbs)
    for name, share in _skirt(q).items():
        paired[name] = middle["hips"] * share
    middle["hips"] = middle["hips"] - sum(paired[name] for name in paired if name not in limbs)
    w = np.zeros((len(p), len(NAMES)))
    for name, share in middle.items():
        w[:, NAMES.index(name)] = share
    left = p[:, 0] >= 0
    for name, share in paired.items():
        w[left, NAMES.index(name)] += share[left]
        w[~left, NAMES.index(twin(name))] += share[~left]
    return w / w.sum(1, keepdims=True)

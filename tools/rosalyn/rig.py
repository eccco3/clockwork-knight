"""Rosalyn's skeleton and skin.

Eighty bones stand on the sculpt's landmarks: a root, five up the middle, an eye and its sleeping lid on
each side, an arm of nine with fifteen in the hand, a leg of three, and sixteen in the skirt, which hangs in
eight columns of two. The upper arm and the forearm are each LENGTHS bones end to end, which share out the
limb's twist: the shoulder keeps its roundness, and the hand turns over without wringing the arm.

Whatever is carved or cast in one piece rides one bone: her head from the choker up, her hair, eyes, lids and
brass. The rest is skinned by a field over the rest pose: `weights` gives any point its bones, so every mesh
binds by where its points lie, at each detail.
"""
import numpy as np
from sculpt import sdf as S, rig as R
from sculpt.sdf import V
from sculpt.gen import Frame
from sculpt.num import smoothstep, lerp, along
from sculpt.rig import beyond, chain, twisted, twin
from . import body, head, dress
from .body import HIP, KNEE, ANKLE, SHOULDER, ELBOW, WRIST, NECK_A, CHOKER, NECK_DIR, HF, UP, FWD, LEFT

PELVIS = V(0, HIP[1], HIP[2])
WAIST, CHEST = V(0, 0.008, 1.045), V(0, 0.006, 1.250)
CROWN = body.HEAD.w(V(0, 0, 0.090))
STERNUM = V(0.020, -0.030, 1.432)             # the collarbone's inner end
GIRDLE, UPPER, FORE = (S.normalize(b - a) for a, b in ((STERNUM, SHOULDER), (SHOULDER, ELBOW), (ELBOW, WRIST)))
CAP = S.normalize(GIRDLE + UPPER)             # out over the shoulder, between the collarbone's way and the arm's
INWARD = S.normalize(np.cross(np.cross(UPPER, -LEFT), UPPER))  # square off the upper arm, toward her ribs
THIGH, SHIN = S.normalize(KNEE - HIP), S.normalize(ANKLE - KNEE)
LENGTHS = 3                                   # bones that share the twist of the upper arm, and of the forearm
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


def lengths(limb):
    """The names of the bones that share out a limb's twist, from its root."""
    return ["%s_%d_l" % (limb, k) for k in range(1, LENGTHS + 1)]


def _twisting(limb, parent, head, tail):
    for k, name in enumerate(lengths(limb)):
        yield name, parent, lerp(head, tail, k / LENGTHS), lerp(head, tail, (k + 1) / LENGTHS)
        parent = name


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
    ("clavicle_l", "chest", STERNUM, SHOULDER), ("deltoid_l", "clavicle_l", SHOULDER, SHOULDER + CAP * 0.05),
    *_twisting("upperarm", "clavicle_l", SHOULDER, ELBOW),
    *_twisting("forearm", lengths("upperarm")[-1], ELBOW, WRIST), ("hand_l", lengths("forearm")[-1], WRIST, KNUCKLES),
    *_digit_bones(),
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
    limb = smoothstep(0.020, 0.008, np.minimum(body.leg(q), body.shoe(q)))        # not the skirt that hangs about it
    shin = limb * beyond(q, KNEE, THIGH + SHIN, 0.030, 0.030)
    foot = shin * beyond(q, ANKLE, SHIN, 0.025, 0.020)
    return chain(("thigh_l", limb), ("shin_l", shin), ("foot_l", foot))


def _digits(l):
    """Each digit bone's share of a point of the hand, in the hand's frame. A digit holds what lies within three
    of its root's radii, and its joints ease over three quarters of their own."""
    lines = {name: np.array(g["joints"]) for name, g in DIGITS.items()}
    thick = {name: g["flesh"][1][::2] for name, g in DIGITS.items()}
    off = {name: S.tube(l, line, 0.0) for name, line in lines.items()}
    out = {}
    for name, line in lines.items():
        rival = np.minimum.reduce([d for other, d in off.items() if other != name])
        ease = [0.75 * r for r in thick[name]]
        hold = np.clip((rival - off[name]) / 0.006 + 0.5, 0.0, 1.0) * smoothstep(3.0 * thick[name][0], 1.5 * thick[name][0], off[name]) \
            * beyond(l, line[0], line[1] - line[0], 2.0 * ease[0], ease[0])
        holds = [hold]
        for j in (1, 2):
            holds.append(holds[-1] * beyond(l, line[j], S.normalize(line[j] - line[j - 1])
                                            + S.normalize(line[j + 1] - line[j]), ease[j], ease[j]))
        out.update(chain(*(("%s_%d_l" % (name, k), h) for k, h in enumerate(holds, 1))))
    return out


def _down(q, joint, end, clear=0.12):
    """How far a point lies down the part of a limb that twists, 0..1: its ends, `clear` of its length each, do not."""
    return (along(q, joint, end)[0] / np.linalg.norm(end - joint) - clear) / (1.0 - 2.0 * clear)


def _arm(q):
    """The shoulder passes from the collarbone to the deltoid over its top, and from the deltoid to the arm down
    its side: the deltoid turns half as far as the arm, so neither blend spans the whole of the arm's swing.
    The sleeve goes whole with the arm, out to the fold of the armpit; below the fold the deltoid carries the
    bodice's side, less and less down the ribs, so a raised arm draws the cloth up rather than tearing it."""
    s, r = along(q, SHOULDER, ELBOW)
    flesh = np.minimum(body.upper_arm(q), body.arm(q))
    by_ribs = smoothstep(0.32, 0.26, s)
    sleeve = smoothstep(0.045, 0.030, flesh) * np.maximum(smoothstep(0.066, 0.057, r), 1.0 - by_ribs)
    toward = ((q - SHOULDER - np.outer(s, UPPER)) @ INWARD) / np.maximum(r, 1e-9)
    side = 0.6 * smoothstep(0.110, 0.062, r) * smoothstep(0.02, 0.07, s) * by_ribs * smoothstep(0.6, 0.9, toward)
    out_over = (q - SHOULDER) @ CAP
    cap = np.maximum(sleeve * smoothstep(-0.030, 0.010, out_over), side)
    upper = sleeve * smoothstep(0.020, 0.070, out_over)
    girdle = np.maximum(smoothstep(0.110, 0.045, S.length(q - SHOULDER)), cap)
    fore = upper * beyond(q, ELBOW, UPPER + FORE, 0.030, 0.030)
    hand = fore * beyond(q, WRIST, FORE + FINGERWARD, 0.016, 0.016)
    out = chain(("clavicle_l", girdle), ("deltoid_l", cap),
                *zip(lengths("upperarm"), twisted(upper, _down(q, SHOULDER, ELBOW), LENGTHS)),
                *zip(lengths("forearm"), twisted(fore, _down(q, ELBOW, WRIST), LENGTHS)), ("hand_l", hand))
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

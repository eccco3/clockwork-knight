"""The grinner's skeleton and skin.

Fifty bones stand on the sculpt's landmarks: a root, five up the middle, and on each side an arm of four,
fourteen in the hand and a leg of four. Paired bones are described on the left and end in _l; their twins
end in _r. A kind of grinner that bites has one more, the jaw. The skin is a field over the rest pose:
`weights` gives any point its bones, so every mesh of the figure binds by where its points lie, at each
detail level and after the head is resculpted.
"""
import bpy
import numpy as np
from sculpt import sdf as S
from sculpt.sdf import V
from sculpt.num import smoothstep, along
from . import body, head as skull
from .body import HIP, KNEE, ANKLE, SHOULDER, ELBOW, WRIST, NECK_A, NECK_B, NECK_R, HF, THIGH, SHIN, FORE

MIRROR = V(-1, 1, 1)
PELVIS = V(0, HIP[1], HIP[2])
WAIST, CHEST = V(0, 0.015, 0.734), V(0, 0.015, 0.860)
CROWN = NECK_B + V(0, -0.020, 0.130)
STERNUM = V(0.026, -0.009, 0.989)             # the collarbone's inner end
UPPER = S.normalize(ELBOW - SHOULDER)
FINGERWARD = HF.dir(V(0, 0, 1))
KNUCKLES = HF.w(V(0, 0, 0.086))
BALL, TOE_TIP = body.from_foot([(0, 0.095, 0.012), (0, 0.142, 0.010)])
TOE_LINE = (0.097, -0.18)                      # where the toes hinge: foot-frame y at x = 0, and its slope across the foot
DIGITS = dict({name: (g, (0, 1, 2, 3)) for name, g in body.FINGERS.items()}, thumb=(body.THUMB, (0, 2, 3)))


def _digit_bones():
    for name, (g, at) in DIGITS.items():
        pts = HF.w(np.array(g["chain"]))
        for k, (a, b) in enumerate(zip(at, at[1:]), 1):
            yield "%s_%d_l" % (name, k), "%s_%d_l" % (name, k - 1) if k > 1 else "hand_l", pts[a], pts[b]


def _twin(name):
    return name[:-1] + "r" if name and name.endswith("_l") else name


def _both_sides(bones):
    for name, parent, head, tail in bones:
        yield name, parent, head, tail
        if name.endswith("_l"):
            yield _twin(name), _twin(parent), head * MIRROR, tail * MIRROR


BONES = list(_both_sides([
    ("root", None, V(0, 0, 0), V(0, 0, 0.15)),
    ("hips", "root", PELVIS, WAIST), ("spine", "hips", WAIST, CHEST), ("chest", "spine", CHEST, NECK_A),
    ("neck", "chest", NECK_A, NECK_B), ("head", "neck", NECK_B, CROWN),
    ("clavicle_l", "chest", STERNUM, SHOULDER), ("upperarm_l", "clavicle_l", SHOULDER, ELBOW),
    ("forearm_l", "upperarm_l", ELBOW, WRIST), ("hand_l", "forearm_l", WRIST, KNUCKLES), *_digit_bones(),
    ("thigh_l", "hips", HIP, KNEE), ("shin_l", "thigh_l", KNEE, ANKLE), ("foot_l", "shin_l", ANKLE, BALL),
    ("toe_l", "foot_l", BALL, TOE_TIP)]))
NAMES = [bone[0] for bone in BONES]
JAW = ("jaw", "head", skull.from_head(skull.JAW_HINGE), skull.from_head(skull.CHIN))
MOST = 4                                       # bones that may hold one vertex


def armature(name, jaw=False):
    ob = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for bone, parent, head, tail in BONES + [JAW] * jaw:
        b = ob.data.edit_bones.new(bone)
        b.head, b.tail = head, tail
        if parent:
            b.parent = ob.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


def bind(ob, rig):
    """Skin a mesh of the figure to the rig by where its points stand."""
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    jaw = JAW[0] in rig.data.bones
    w = weights(co.reshape(-1, 3), jaw)
    w[w < np.sort(w, axis=1)[:, -MOST, None]] = 0.0
    w /= w.sum(1, keepdims=True)
    for k, name in enumerate(NAMES + [JAW[0]] * jaw):
        group = ob.vertex_groups.new(name=name)
        for i in np.nonzero(w[:, k])[0]:
            group.add([int(i)], float(w[i, k]), "REPLACE")
    ob.parent = rig
    ob.modifiers.new("rig", "ARMATURE").object = rig


# ---------------------------------------------------------------- the skin

def _beyond(p, joint, way, before, after):
    """0 short of a joint and 1 past it along `way`, easing from `before` metres short to `after` past."""
    return smoothstep(-before, after, (p - joint) @ S.normalize(way))


def _near(p, pts, radii, soft):
    """1 within the round polyline, easing to 0 over `soft` metres either side of its surface."""
    return smoothstep(soft, -soft, S.tube(p, pts, radii))


def _chain(*holds):
    """Weights down a chain of bones from (name, hold) pairs, where a hold is the share of each point carried
    by that bone and all below it."""
    names, held = zip(*holds)
    return {name: h - below for name, h, below in zip(names, held, held[1:] + (0.0,))}


def _leg(q):
    down = (q - HIP) @ THIGH
    apart = np.maximum(smoothstep(0.0, 0.03, q[:, 0]), smoothstep(0.06, 0.12, down))    # the gusset stays with the hips
    thigh = smoothstep(-0.02, 0.09, down) * apart * smoothstep(0.26, 0.20, q[:, 0])
    shin = thigh * _beyond(q, KNEE, THIGH + SHIN, 0.030, 0.030)
    foot = shin * _beyond(q, ANKLE, SHIN, 0.025, 0.020)
    l = body.to_foot(q)
    toe = foot * smoothstep(-0.012, 0.010, l[:, 1] - TOE_LINE[0] - TOE_LINE[1] * l[:, 0])
    return _chain(("thigh_l", thigh), ("shin_l", shin), ("foot_l", foot), ("toe_l", toe))


def _digits(l):
    """Each digit bone's share of a point of the hand, in the hand's frame."""
    lines = {name: np.array(g["chain"] + [g["claw"][0][-1]]) for name, (g, at) in DIGITS.items()}
    off = {name: S.tube(l, line, 0.0) for name, line in lines.items()}
    out = {}
    for name, (g, at) in DIGITS.items():
        line = lines[name]
        rival = np.minimum.reduce([d for other, d in off.items() if other != name])
        hold = np.clip((rival - off[name]) / 0.006 + 0.5, 0.0, 1.0) * smoothstep(0.022, 0.010, off[name]) \
            * _beyond(l, line[at[0]], line[at[0] + 1] - line[at[0]], 0.010, 0.006)
        holds = [hold]
        for j in at[1:-1]:
            holds.append(holds[-1] * _beyond(l, line[j], S.normalize(line[j] - line[j - 1])
                                             + S.normalize(line[j + 1] - line[j]), 0.005, 0.005))
        out.update(_chain(*(("%s_%d_l" % (name, k), h) for k, h in enumerate(holds, 1))))
    return out


def _arm(q):
    sleeve = _near(q, [SHOULDER, ELBOW, WRIST, KNUCKLES, HF.w(V(0, 0, 0.20))], [0.052, 0.052, 0.070, 0.140, 0.160], 0.012)
    upper = sleeve * _beyond(q, SHOULDER, UPPER, 0.015, 0.045)
    girdle = np.maximum(smoothstep(0.115, 0.045, S.length(q - SHOULDER)), upper)
    fore = upper * _beyond(q, ELBOW, UPPER + FORE, 0.030, 0.030)
    hand = fore * _beyond(q, WRIST, FORE + FINGERWARD, 0.018, 0.018)
    out = _chain(("clavicle_l", girdle), ("upperarm_l", upper), ("forearm_l", fore), ("hand_l", hand))
    for name, share in _digits(HF.l(q)).items():
        out[name] = hand * share
        out["hand_l"] = out["hand_l"] - out[name]
    return out


def _middle(p, jaw):
    up, out = along(p, NECK_A, NECK_B)
    wide = smoothstep(NECK_R + 0.006, NECK_R + 0.030, out)
    spine = _beyond(p, WAIST, CHEST - WAIST, 0.040, 0.040)
    chest = spine * _beyond(p, CHEST, NECK_A - CHEST, 0.040, 0.040)
    neck = chest * smoothstep(0.0, 0.050, up) * (1.0 - wide * smoothstep(0.070, 0.040, up))      # not the shoulders
    top = np.linalg.norm(NECK_B - NECK_A)
    head = neck * (1.0 - smoothstep(top + 0.010, top - 0.030, up) * (1.0 - wide))                  # the jaw overhangs
    holds = [("hips", np.ones(len(p))), ("spine", spine), ("chest", chest), ("neck", neck), ("head", head)]
    return _chain(*holds, *[(JAW[0], head * skull.jaw(skull.to_head(p)))] * jaw)


def weights(p, jaw=False):
    """An (N, bones) array: each rest-pose point's share in every bone of NAMES, and in the jaw after them if
    the rig has one, rows summing to one."""
    names = NAMES + [JAW[0]] * jaw
    q = S.mirror_x(p)
    limbs = dict(_arm(q), **_leg(q))
    held = np.minimum(sum(limbs.values()), 1.0)
    w = np.zeros((len(p), len(names)))
    for name, share in _middle(p, jaw).items():
        w[:, names.index(name)] = share * (1.0 - held)
    left = p[:, 0] >= 0
    for name, share in limbs.items():
        w[left, names.index(name)] = share[left]
        w[~left, names.index(_twin(name))] = share[~left]
    return w / w.sum(1, keepdims=True)

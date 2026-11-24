"""Her body below the head: the landmarks every part is measured from, and the carved torso, arms and legs.

World frame as the knight's: +X the figure's left, -Y forward, +Z up, metres, feet on z = 0. She stands at
rest with her arms a little away from her sides. Paired parts are sculpted on the left; callers mirror
points with sdf.mirror_x. Each part offers the field its mesh is fitted to and the polycube that meshes it,
with edge loops ringing the neck, shoulders, arms and every finger. `cells` scales every lattice with the
build's one detail setting.
"""
import numpy as np
from sculpt import sdf as S, mesher
from sculpt.sdf import V
from sculpt.gen import Frame
from sculpt.lattice import Box
from sculpt.num import smoothstep, lerp, along

UP, FWD, BACK, LEFT = V(0, 0, 1), V(0, -1, 0), V(0, 1, 0), V(1, 0, 0)

# ---------------------------------------------------------------- landmarks (left side)

HEAD = Frame(V(0, -0.022, 1.630), UP, -LEFT)   # between the eyes at the centre of the skull; y out of the face
NECK_A, NECK_B = V(0, 0.018, 1.440), V(0, -0.004, 1.580)
NECK_DIR = S.normalize(NECK_B - NECK_A)
CHOKER = lerp(NECK_A, NECK_B, 0.47)           # where the head's wood meets the body's, under a brass band
SHOULDER = V(0.150, 0.012, 1.405)
ELBOW = SHOULDER + S.normalize(V(0.407, 0.050, -0.914)) * 0.285
WRIST = ELBOW + S.normalize(V(0.300, -0.300, -0.905)) * 0.245
UPPER = S.normalize(ELBOW - SHOULDER)
HF = Frame(WRIST, V(0.240, -0.260, -0.935), V(1.0, -0.30, 0.10))   # hand: x back of hand, y thumb side, z fingers
HIP = V(0.082, 0.014, 0.905)
KNEE = V(0.078, 0.000, 0.500)
ANKLE = V(0.072, 0.022, 0.082)
TOE_OUT = np.radians(9.0)
ARM_FROM, STUB_TO = 0.105, 0.135              # along the upper arm: the arm piece starts, the torso's stub ends
CHEST_CUT = 1.235                              # the torso piece ends here, well under the bodice


def cells(n, detail, least=1):
    return max(least, int(round(n * detail)))


# ---------------------------------------------------------------- neck and torso

def neck(p):
    q = S.mirror_x(p)
    d = S.cone(p, NECK_A - NECK_DIR * 0.030, NECK_B, 0.0495, 0.0450)
    cord = S.tube(q, [V(0.050, 0.004, 1.585), V(0.034, -0.016, 1.520), V(0.013, -0.036, 1.446)], [0.0085, 0.0080, 0.0070])
    return S.smin(d, cord, 0.016)


def upper_arm(q):
    return S.tube(q, [SHOULDER, lerp(SHOULDER, ELBOW, 0.40), lerp(SHOULDER, ELBOW, 0.80), ELBOW],
                  [0.0400, 0.0365, 0.0318, 0.0290])


def trunk(p):
    """The torso without neck or arms: ribs, waist, hips, shoulder blades and a modest bust."""
    q = S.mirror_x(p)
    d = S.smin(S.ellipsoid(p, V(0, 0.004, 1.285), V(0.128, 0.090, 0.165)),
               S.ellipsoid(p, V(0, 0.006, 1.090), V(0.104, 0.076, 0.130)), 0.05)
    d = S.smin(d, S.ellipsoid(p, V(0, 0.016, 0.925), V(0.162, 0.104, 0.125)), 0.06)
    d = S.smin(d, S.ellipsoid(q, V(0.060, -0.060, 1.258), V(0.046, 0.037, 0.046)), 0.040)
    d = S.smin(d, S.ellipsoid(q, V(0.078, 0.064, 1.345), V(0.050, 0.018, 0.066), S.euler(z=14)), 0.045)
    return S.ssub(d, S.tube(p, [V(0, 0.100, 1.40), V(0, 0.100, 1.30), V(0, 0.092, 1.16)], 0.0040), 0.022)


def _girdle(p):
    """Trunk, sloping shoulders, the roots of the arms and the neck."""
    q = S.mirror_x(p)
    d = trunk(p)
    d = S.smin(d, S.cone(q, V(0.032, 0.022, 1.476), SHOULDER + V(-0.016, 0.0, 0.020), 0.026, 0.028), 0.045)
    d = S.smin(d, S.sphere(q, SHOULDER + V(-0.002, 0, 0), 0.0405), 0.028)
    d = S.smin(d, upper_arm(q), 0.020)
    return S.smin(d, neck(p), 0.030)


COLLARBONE = [(0.016, 1.431), (0.050, 1.437), (0.085, 1.441), (0.118, 1.439)]      # across and up, breastbone to shoulder
COLLARBONE_R, COLLARBONE_PROUD = 0.0060, 0.0022
_collarbone = None


def collarbone():
    """The collarbone's line, laid just under the surface of the upper chest (found once by casting forward)."""
    global _collarbone
    if _collarbone is None:
        sink = BACK * (COLLARBONE_R - COLLARBONE_PROUD)
        _collarbone = [S.hug(_girdle, V(x, 0.030, z), FWD, UP, 1, 0.0, 0.0, off=0.0)[0] + sink for x, z in COLLARBONE]
    return _collarbone


def torso(p):
    """The whole torso as one form, with collarbones and the pit of the throat."""
    d = S.smin(_girdle(p), S.tube(S.mirror_x(p), collarbone(), COLLARBONE_R), 0.012)
    return S.ssub(d, S.sphere(p, V(0, -0.064, 1.446), 0.0080), 0.020)


def chest(p):
    """The torso piece: bare shoulders, collarbones and back, ending inside the choker, the sleeves and the bodice."""
    q = S.mirror_x(p)
    d = S.smax(torso(p), (p - CHOKER - NECK_DIR * 0.0012) @ NECK_DIR, 0.001)
    d = S.smax(d, (q - SHOULDER) @ UPPER - STUB_TO, 0.003)
    return S.smax(d, CHEST_CUT - p[:, 2], 0.004)


def chest_grid(detail):
    c = lambda n, least=2: cells(n, detail, least)
    return dict(i=c(24), j=c(15), k=c(42), arm=c(7), stub=c(18), neck=c(6), up=c(10))


def chest_boxes(detail=1.0):
    """A trunk with an arm stub from each flank and the neck from its top. Lattice: i to her left, j backward, k up."""
    g = chest_grid(detail)
    boxes = [Box((-g["i"], -g["j"], 0), (g["i"], g["j"], g["k"]), 2,
                 [V(0, 0.004, CHEST_CUT), V(0, 0.006, 1.330), V(0, 0.010, 1.410), V(0, 0.014, 1.470)],
                 [0.100, 0.112, 0.112, 0.062], [0.066, 0.072, 0.064, 0.038], LEFT, BACK, cap=(0.0, 0.3))]
    path = [SHOULDER + V(-0.030, 0, 0.004), SHOULDER + UPPER * 0.050, SHOULDER + UPPER * (STUB_TO + 0.002)]
    for side in (1, -1):
        lo = (g["i"] if side > 0 else -g["i"] - g["stub"], -g["arm"], g["k"] - 2 * g["arm"])
        hi = (lo[0] + g["stub"], g["arm"], g["k"])
        boxes.append(Box(lo, hi, 0, [x * V(side, 1, 1) for x in path][::side], 0.024, 0.024, BACK, UP,
                         cap=(0.0, 0.2) if side > 0 else (0.2, 0.0)))
    boxes.append(Box((-g["neck"], -g["neck"], g["k"]), (g["neck"], g["neck"], g["k"] + g["up"]), 2,
                     [NECK_A + NECK_DIR * 0.046, CHOKER + NECK_DIR * 0.004], 0.030, 0.030, LEFT, BACK, cap=(0.0, 0.2)))
    return boxes


# ---------------------------------------------------------------- arm and hand

def _digit(base, spread, lengths, curls, radii):
    """A finger from its knuckle: joint points in the hand frame, curling toward the palm."""
    pts, curl = [V(*base)], 0.0
    for length, c in zip(lengths, curls):
        curl += c
        a, b = np.radians(spread), np.radians(curl)
        pts.append(pts[-1] + V(-np.sin(b), np.sin(a) * np.cos(b), np.cos(a) * np.cos(b)) * length)
    return _joints(pts, radii)


def _joints(pts, r, root=None):
    """A digit's flesh through its four joint points, and the line its lattice follows, which leaves the
    palm at `root` (by default just behind the first joint)."""
    mcp, pip, dip, tip = pts
    flesh = ([mcp, lerp(mcp, pip, 0.5), pip, lerp(pip, dip, 0.5), dip, lerp(dip, tip, 0.6), tip],
             [r[0], 0.46 * (r[0] + r[1]), 1.04 * r[1], 0.46 * (r[1] + r[2]), 1.03 * r[2], 0.98 * r[3], 0.80 * r[3]])
    end = tip + S.normalize(tip - dip) * 0.5 * r[3]
    if root is None:
        return dict(flesh=flesh, spine=[mcp - S.normalize(pip - mcp) * 0.008, pip, dip, end],
                    spine_r=[0.7 * r[0], 0.7 * r[1], 0.7 * r[2], 0.5 * r[3]])
    return dict(flesh=flesh, spine=[root, pip, dip, end], spine_r=[0.7 * r[1], 0.7 * r[1], 0.7 * r[2], 0.5 * r[3]])


FINGERS = {
    "pinky": _digit((-0.001, -0.0250, 0.086), -9.0, (0.032, 0.020, 0.019), (16, 24, 14), (0.0066, 0.0058, 0.0052, 0.0044)),
    "ring": _digit((0.001, -0.0085, 0.094), -3.0, (0.041, 0.026, 0.022), (15, 23, 13), (0.0074, 0.0064, 0.0057, 0.0048)),
    "middle": _digit((0.002, 0.0085, 0.097), 1.5, (0.045, 0.028, 0.023), (13, 21, 12), (0.0078, 0.0067, 0.0059, 0.0050)),
    "index": _digit((0.001, 0.0255, 0.093), 6.0, (0.040, 0.025, 0.022), (10, 18, 11), (0.0076, 0.0066, 0.0058, 0.0049)),
}
THUMB = _joints([V(-0.0060, 0.0200, 0.0120), V(-0.0135, 0.0390, 0.0450), V(-0.0190, 0.0530, 0.0720),
                 V(-0.0225, 0.0625, 0.0950)], (0.0115, 0.0092, 0.0078, 0.0062), root=V(-0.0110, 0.0240, 0.0400))
DIGITS = list(FINGERS.values()) + [THUMB]


def arm(p):
    """The arm from inside the sleeve to the fingertips."""
    l = HF.l(p)
    d = S.smin(upper_arm(p), S.sphere(p, ELBOW + V(0, 0.004, 0), 0.0292), 0.014)
    fore = S.tube(p, [ELBOW, lerp(ELBOW, WRIST, 0.24), lerp(ELBOW, WRIST, 0.64), WRIST], [0.0285, 0.0300, 0.0238, 0.0180])
    d = S.smin(d, fore, 0.014)
    d = S.smin(d, S.ellipsoid(l, V(0, 0, 0.002), V(0.0135, 0.0220, 0.026)), 0.012)
    d = S.smin(d, S.sphere(l, V(0.0085, -0.0185, -0.004), 0.0072), 0.006)          # head of the ulna
    palm = S.smin(S.ellipsoid(l, V(0, 0, 0.032), V(0.0122, 0.0285, 0.034)),
                  S.box(l, V(-0.001, 0.0005, 0.068), V(0.0092, 0.0330, 0.027), 0.0090), 0.018)
    palm = S.smin(palm, S.ellipsoid(l, V(-0.0085, 0.0235, 0.036), V(0.0105, 0.0150, 0.030)), 0.012)
    palm = S.smin(palm, S.ellipsoid(l, V(-0.0060, -0.0225, 0.042), V(0.0085, 0.0105, 0.032)), 0.012)
    palm = S.ssub(palm, S.ellipsoid(l, V(-0.0195, -0.002, 0.055), V(0.010, 0.017, 0.026)), 0.010)
    flesh = None
    for g in DIGITS:
        f = S.tube(l, *g["flesh"])
        flesh = f if flesh is None else np.minimum(flesh, f)
    for g in FINGERS.values():
        mcp = g["flesh"][0][0]
        palm = S.smin(palm, S.sphere(l, mcp + V(0.0030, 0, -0.002), 0.0078), 0.006)
    d = S.smin(d, S.smin(palm, flesh, 0.0065), 0.012)
    return S.smax(d, ARM_FROM - (p - SHOULDER) @ UPPER, 0.004)


def arm_grid(detail):
    c = lambda n, least=1: cells(n, detail, least)
    f, web, pad = c(4, 2), c(2), c(2)
    return dict(f=f, web=web, pad=pad, wide=4 * f + 3 * web, thick=f + 2 * pad, k=c(128), finger=c(34), thumb=c(30),
                at=c(115))


def arm_boxes(detail=1.0):
    """Arm and palm as one flat trunk; the fingers leave its end with webs between them, the thumb its side.
    Lattice: i across the palm (little finger -> index), j palm -> back, k toward the tips."""
    g = arm_grid(detail)
    wide, back, tip = HF.dir(V(0, 1, 0)), HF.dir(V(1, 0, 0)), HF.dir(V(0, 0, 1))
    start = SHOULDER + UPPER * (ARM_FROM + 0.004)
    boxes = [Box((0, 0, 0), (g["wide"], g["thick"], g["k"]), 2,
                 [start, lerp(start, ELBOW, 0.5), ELBOW, lerp(ELBOW, WRIST, 0.5), WRIST, HF.w((0, 0, 0.046)), HF.w((0, 0, 0.088))],
                 [0.022, 0.021, 0.019, 0.017, 0.015, 0.023, 0.027], [0.022, 0.021, 0.019, 0.016, 0.0090, 0.0068, 0.0058],
                 wide, back, cap=(0.5, 0.0))]
    for n, f in enumerate(FINGERS.values()):
        lo = (n * (g["f"] + g["web"]), g["pad"], g["k"])
        boxes.append(Box(lo, (lo[0] + g["f"], lo[1] + g["f"], lo[2] + g["finger"]), 2,
                         [HF.w(x) for x in f["spine"]], f["spine_r"], f["spine_r"], wide, back, cap=(0.0, 0.5)))
    lo = (g["wide"], g["pad"], g["at"])
    boxes.append(Box(lo, (lo[0] + g["thumb"], lo[1] + g["f"], lo[2] + g["f"]), 0,
                     [HF.w(x) for x in THUMB["spine"]], THUMB["spine_r"], THUMB["spine_r"], back, tip, cap=(0.0, 0.5)))
    return boxes


# ---------------------------------------------------------------- leg, and the foot inside its shoe

def to_foot(p):
    """Foot frame: x outward, y toward the toes, z up from the ground under the ankle."""
    c, s = np.cos(TOE_OUT), np.sin(TOE_OUT)
    dx, dy = p[:, 0] - ANKLE[0], p[:, 1] - ANKLE[1]
    return np.stack([dx * c + dy * s, dx * s - dy * c, p[:, 2]], axis=1)


def from_foot(l):
    c, s = np.cos(TOE_OUT), np.sin(TOE_OUT)
    l = np.atleast_2d(np.asarray(l, dtype=np.float64))
    return np.stack([ANKLE[0] + l[:, 0] * c + l[:, 1] * s, ANKLE[1] + l[:, 0] * s - l[:, 1] * c, l[:, 2]], axis=1)


def foot(l):
    """The foot in its own frame, standing on a low heel."""
    d = S.ellipsoid(l, V(0, -0.030, 0.034), V(0.0235, 0.027, 0.030))
    d = S.smin(d, S.ellipsoid(l, V(0, 0.040, 0.036), V(0.029, 0.070, 0.0235), S.rot_x(np.radians(-14.0))), 0.026)
    d = S.smin(d, S.ellipsoid(l, V(-0.003, 0.104, 0.0165), V(0.0375, 0.046, 0.0150)), 0.018)
    return S.smax(d, 0.004 - l[:, 2], 0.004)


def leg(p):
    """Shin, ankle and foot; the thigh is left to the skirt."""
    d = S.tube(p, [lerp(KNEE, HIP, 0.25), KNEE, lerp(KNEE, ANKLE, 0.28) + V(0.004, 0.012, 0), lerp(KNEE, ANKLE, 0.70), ANKLE],
               [0.050, 0.0445, 0.0475, 0.0300, 0.0245])
    l = to_foot(p)
    d = S.smin(d, S.sphere(l, V(0.0215, -0.006, 0.076), 0.0115), 0.010)
    d = S.smin(d, S.sphere(l, V(-0.0205, 0.002, 0.084), 0.0115), 0.010)
    d = S.smin(d, foot(l), 0.020)
    return S.smax(d, (p - lerp(KNEE, HIP, 0.12)) @ UP, 0.004)


def leg_grid(detail):
    c = lambda n, least=2: cells(n, detail, least)
    return dict(i=c(8), j=c(26), k=c(4), shin=c(8), at=c(3), up=c(70))


def leg_boxes(detail=1.0):
    """The foot lies along j (heel -> toes); the shin stands on its instep and runs up k to the knee."""
    g = leg_grid(detail)
    out = from_foot((1, 0, 0))[0] - from_foot((0, 0, 0))[0]
    toe = from_foot((0, 1, 0))[0] - from_foot((0, 0, 0))[0]
    return [Box((0, 0, 0), (g["i"], g["j"], g["k"]), 1,
                from_foot([(0, -0.046, 0.030), (0, 0.020, 0.034), (-0.002, 0.090, 0.020), (-0.002, 0.140, 0.014)]),
                [0.018, 0.023, 0.029, 0.024], [0.020, 0.020, 0.011, 0.007], out, UP, cap=(0.5, 0.4)),
            Box((0, g["at"], g["k"]), (g["i"], g["at"] + g["shin"], g["k"] + g["up"]), 2,
                [ANKLE + V(0, 0, -0.024), lerp(KNEE, ANKLE, 0.5), KNEE, lerp(KNEE, HIP, 0.10)],
                [0.016, 0.024, 0.030, 0.032], [0.016, 0.024, 0.030, 0.032], out, toe, cap=(0.0, 0.5))]


# ---------------------------------------------------------------- slipper

def shoe(p):
    """A lacquered slipper: the foot's own shape a little larger, open over the instep."""
    l = to_foot(p)
    top = 0.036 + 0.016 * smoothstep(0.0, -0.045, l[:, 1]) + 0.050 * smoothstep(0.055, 0.075, l[:, 1])
    d = S.smax(foot(l) - 0.0026, l[:, 2] - top, 0.0022)
    return S.smax(d, -l[:, 2], 0.002)


def shoe_wrap(detail=1.0):
    n = (cells(16, detail, 4), cells(36, detail, 4), cells(12, detail, 4))
    v, q, nrm = mesher.wrap(shoe, from_foot((0, -0.034, 0.020))[0], from_foot((0, 0.105, 0.013))[0], (0.05, 0.11, 0.04),
                            n, relax=8)
    unit = mesher.cube_lattice(*n)[0]
    return v, q, nrm, np.rint((unit + 1.0) / 2.0 * np.array(n)).astype(np.int64)

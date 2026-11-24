"""The grinner below the neck: skin (forearms, clawed hands, backward legs, feet) and clothes.

World frame as the knight's: +X the figure's left, -Y forward, +Z up, metres, feet on z = 0.
Paired parts are sculpted on the left; callers mirror points with sdf.mirror_x.
Each part offers a field (the game mesh is fitted to it), a detail field (baked to the normal map),
a paint (albedo, roughness, metallic at surface points) and the polycube that meshes it.
"""
import numpy as np
from knight import sdf as S
from knight.sdf import V
from knight.gen import Frame
from .lattice import Box
from .sculpt import smoothstep, bump, lerp, noise3, fbm, along, mix

UP, DOWN, FWD, BACK, LEFT = V(0, 0, 1), V(0, 0, -1), V(0, -1, 0), V(0, 1, 0), V(1, 0, 0)

# ---------------------------------------------------------------- landmarks (left side)

HIP = V(0.068, 0.020, 0.600)
KNEE = V(0.084, 0.185, 0.332)                  # behind the hip: the leg folds the wrong way
ANKLE = V(0.088, 0.030, 0.062)
TOE_OUT = np.radians(11.0)
SHOULDER = V(0.128, -0.040, 0.975)
ELBOW = V(0.277, -0.070, 0.719)
WRIST = V(0.395, -0.153, 0.461)                # the fingertips hang below the knee
NECK_A, NECK_B, NECK_R = V(0, -0.050, 0.975), V(0, -0.084, 1.082), 0.038
THIGH = S.normalize(KNEE - HIP)
SHIN = S.normalize(ANKLE - KNEE)
FORE = S.normalize(WRIST - ELBOW)
CUFF = lerp(ELBOW, WRIST, 0.42)                # the sleeves were cut for a shorter arm
HEM = lerp(HIP, KNEE, 0.76)
HF = Frame(WRIST, V(0.30, -0.26, -0.918), V(1.0, -0.35, 0.10))   # hand: x back of hand, y thumb side, z fingers

SKIN = V(0.72, 0.625, 0.585)
SKIN_COLD = V(0.60, 0.585, 0.63)
BRUISE = V(0.40, 0.31, 0.39)
DEAD = V(0.20, 0.175, 0.20)
HORN = V(0.050, 0.042, 0.038)
DIRT = V(0.27, 0.225, 0.18)
SCAB = V(0.36, 0.17, 0.14)


def curve(pts, radii, n=4):
    """Catmull-Rom resampling of a polyline and its radii."""
    P = np.array(pts, dtype=np.float64)
    R = np.array(radii, dtype=np.float64)
    out, rad = [], []
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        for k in range(n):
            t = k / n
            out.append(0.5 * (2 * p1 + (p2 - p0) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
            rad.append(R[i] + (R[i + 1] - R[i]) * t)
    return out + [P[-1]], rad + [R[-1]]


def skin_tone(p, cold):
    """Pale, mottled child's skin; `cold` in 0..1 drains it toward grey-violet."""
    col = np.tile(SKIN, (len(p), 1)) * (0.90 + 0.16 * fbm(p * 38.0))[:, None]
    blotch = smoothstep(0.38, 0.72, fbm(p * 13.0 + 3.1))
    col = mix(col, SKIN_COLD, np.clip(0.20 + 0.45 * blotch + cold, 0, 1) * 0.9)
    return mix(col, BRUISE, 0.45 * smoothstep(0.52, 0.80, fbm(p * 21.0 + 9.7)) * (0.35 + cold))


# ---------------------------------------------------------------- forearm and hand

def _digit(base, spread, lengths, curls, radii):
    pts, curl = [V(*base)], 0.0
    for length, c in zip(lengths, curls):
        curl += c
        a, b = np.radians(spread), np.radians(curl)
        d = V(-np.sin(b), np.sin(a) * np.cos(b), np.cos(a) * np.cos(b))
        pts.append(pts[-1] + d * length)
    return _with_claw(pts, d, radii)


def _with_claw(pts, d, r):
    mcp, pip, dip, tip = pts
    e = S.normalize(V(1, 0, 0) - d * d[0])                      # toward the back of the hand
    flesh = ([mcp, lerp(mcp, pip, 0.5), pip, lerp(pip, dip, 0.5), dip, tip],
             [r[0], 0.44 * (r[0] + r[1]), 1.05 * r[1], 0.45 * (r[1] + r[2]), 1.04 * r[2], r[3]])
    claw = curve([lerp(dip, tip, 0.45) + e * 0.0022, tip + d * 0.006 + e * 0.0022,
                  tip + d * 0.019 - e * 0.0025, tip + d * 0.028 - e * 0.0125],
                 [0.90 * r[3], 0.92 * r[3], 0.66 * r[3], 0.0009], 3)
    c, cr = claw                                                # the lattice follows the claw's own centre line
    spine = [mcp - S.normalize(pip - mcp) * 0.008, pip, dip, c[2], c[5], c[7], c[9]]
    return dict(flesh=flesh, claw=claw, joints=[pip, dip], dir=d, back=e, spine=spine,
                spine_r=[0.7 * r[0], 0.7 * r[1], 0.7 * r[2], 0.55 * r[3], 0.5 * cr[5], 0.5 * cr[7], 0.0005])


FINGERS = {
    "pinky": _digit((-0.001, -0.0225, 0.079), -11.0, (0.034, 0.022, 0.019), (9, 15, 11), (0.0070, 0.0060, 0.0053, 0.0045)),
    "ring": _digit((0.001, -0.0075, 0.087), -4.0, (0.043, 0.029, 0.022), (10, 16, 12), (0.0078, 0.0066, 0.0058, 0.0049)),
    "middle": _digit((0.002, 0.0080, 0.090), 1.5, (0.047, 0.031, 0.023), (10, 16, 12), (0.0082, 0.0070, 0.0061, 0.0051)),
    "index": _digit((0.001, 0.0235, 0.086), 7.0, (0.043, 0.027, 0.021), (9, 15, 11), (0.0080, 0.0068, 0.0060, 0.0050)),
}
_t0 = V(-0.004, 0.022, 0.018)
_t1 = _t0 + S.normalize(V(-0.28, 0.62, 0.73)) * 0.040
_t2 = _t1 + S.normalize(V(-0.34, 0.50, 0.80)) * 0.031
_t3 = _t2 + S.normalize(V(-0.42, 0.40, 0.82)) * 0.026
THUMB = _with_claw([_t0, _t1, _t2, _t3], S.normalize(_t3 - _t2), (0.0115, 0.0088, 0.0078, 0.0058))
DIGITS = list(FINGERS.values()) + [THUMB]


def arm_parts(p):
    l = HF.l(p)
    fore = S.tube(p, [ELBOW, lerp(ELBOW, WRIST, 0.22), lerp(ELBOW, WRIST, 0.62), WRIST], [0.0235, 0.0262, 0.0200, 0.0165])
    d = S.smin(fore, S.sphere(p, ELBOW, 0.0245), 0.012)
    d = S.smin(d, S.ellipsoid(l, V(0, 0, 0.002), V(0.0135, 0.0205, 0.024)), 0.012)
    d = S.smin(d, S.sphere(l, V(0.0085, -0.0165, -0.004), 0.0075), 0.006)          # head of the ulna
    palm = S.smin(S.ellipsoid(l, V(0, 0, 0.022), V(0.0125, 0.0240, 0.026)),
                  S.box(l, V(-0.001, 0.0005, 0.056), V(0.0098, 0.0305, 0.031), 0.0095), 0.014)
    palm = S.smin(palm, S.ellipsoid(l, V(-0.0075, 0.0205, 0.034), V(0.0105, 0.0135, 0.026)), 0.010)
    palm = S.smin(palm, S.ellipsoid(l, V(-0.0060, -0.0220, 0.036), V(0.0090, 0.0105, 0.028)), 0.010)
    palm = S.ssub(palm, S.ellipsoid(l, V(-0.0195, -0.002, 0.050), V(0.010, 0.016, 0.024)), 0.010)
    flesh, claw = None, None
    for g in DIGITS:
        f = S.tube(l, *g["flesh"])
        c = S.tube(l, *g["claw"])
        flesh = f if flesh is None else np.minimum(flesh, f)
        claw = c if claw is None else np.minimum(claw, c)
    for g in FINGERS.values():
        mcp = g["flesh"][0][0]
        palm = S.smin(palm, S.sphere(l, mcp + V(0.0035, 0, -0.002), 0.0080), 0.006)
        palm = S.smin(palm, S.cone(l, V(0.0105, 0.3 * mcp[1], 0.010), mcp + V(0.0060, 0, -0.006), 0.0030, 0.0022), 0.005)
    hand = S.smin(S.smin(palm, flesh, 0.007), claw, 0.0012)
    d = S.smax(S.smin(d, hand, 0.012), (lerp(ELBOW, WRIST, 0.27) - p) @ FORE, 0.004)       # ends inside the sleeve
    return dict(d=d, claw=claw, flesh=flesh, l=l)


def arm(p):
    return arm_parts(p)["d"]


def arm_detail(p):
    P = arm_parts(p)
    l = P["l"]
    h = 0.00035 * (fbm(p * 260.0, 2) - 0.5)
    for g in DIGITS:
        for j in g["joints"]:
            v = l - j
            s = v @ g["dir"]
            h = h - 0.00030 * np.exp(-((v * v).sum(-1)) / 0.0075 ** 2) * np.cos(2 * np.pi * s / 0.0019) \
                * smoothstep(-0.001, 0.003, v @ g["back"])
    ridges = noise3(l * V(1100.0, 1100.0, 55.0)) - 0.5
    h = h + 0.00022 * ridges * smoothstep(0.0008, 0.0, P["claw"])
    return P["d"] - h


def arm_paint(p):
    P = arm_parts(p)
    l = P["l"]
    reach = smoothstep(-0.10, 0.20, l[:, 2])                                        # 0 mid-forearm .. 1 fingertips
    col = skin_tone(p, 0.25 + 0.55 * reach)
    col = mix(col, DEAD, 0.75 * smoothstep(0.085, 0.20, l[:, 2]) * (0.6 + 0.4 * fbm(p * 60.0)))
    col = mix(col, BRUISE, 0.35 * smoothstep(0.004, 0.0, np.abs(l[:, 0]) - 0.004) * bump(l[:, 2], 0.088, 0.012))
    col = mix(col, DIRT, 0.5 * smoothstep(0.45, 0.8, fbm(p * 45.0 + 2.0)) * reach)
    nail = smoothstep(0.0009, 0.0002, P["claw"])
    col = mix(col, DEAD * 0.7, smoothstep(0.0045, 0.0010, P["claw"]))               # the quick, bruised round each claw
    streak = 0.75 + 0.5 * noise3(l * V(900.0, 900.0, 40.0))
    col = mix(col, HORN * streak[:, None], nail)
    rough = 0.58 - 0.10 * reach
    rough = rough * (1 - nail) + 0.24 * nail
    return col, rough, np.zeros(len(p)), 1.0 - nail


PALM_K, THUMB_K, FINGER_N, THUMB_N = 25, 19, 17, 13


def arm_boxes(n=1):
    """Forearm and palm as one flat trunk, four cells thick; the fingers leave the middle of its end two cells
    wide with one-cell webs, the thumb leaves its side. Lattice: i across the palm (little finger -> index),
    j palm -> back, k toward the tips."""
    wide, back, tip = HF.dir(V(0, 1, 0)), HF.dir(V(1, 0, 0)), HF.dir(V(0, 0, 1))
    k_palm, k_thumb = PALM_K, THUMB_K
    trunk = Box(np.array((0, 0, 0)) * n, np.array((11, 4, k_palm)) * n, 2,
                [lerp(ELBOW, WRIST, 0.30), lerp(ELBOW, WRIST, 0.70), WRIST, HF.w((0, 0, 0.045)), HF.w((0, 0, 0.083))],
                [0.016, 0.014, 0.014, 0.022, 0.026], [0.015, 0.013, 0.0085, 0.0070, 0.0062], wide, back, cap=(0.5, 0.0))
    boxes = [trunk]
    for k, g in enumerate(FINGERS.values()):
        boxes.append(Box(np.array((3 * k, 1, k_palm)) * n, np.array((3 * k + 2, 3, k_palm + FINGER_N)) * n, 2,
                         [HF.w(q) for q in g["spine"]], g["spine_r"], g["spine_r"], wide, back, cap=(0.0, 0.3)))
    boxes.append(Box(np.array((11, 1, k_thumb)) * n, np.array((11 + THUMB_N, 3, k_thumb + 2)) * n, 0,
                     [HF.w(q) for q in THUMB["spine"]], THUMB["spine_r"], THUMB["spine_r"], back, tip, cap=(0.0, 0.3)))
    return boxes


def arm_pin(c, n=1):
    """Hold the point of every claw."""
    i, j, k = c[:, 0], c[:, 1], c[:, 2]
    finger = (i % (3 * n) == n) & (i < 11 * n) & (k == (PALM_K + FINGER_N) * n)
    thumb = (i == (11 + THUMB_N) * n) & (k == (THUMB_K + 1) * n)
    return (j == 2 * n) & (finger | thumb)


def arm_seam(a, b, n=1):
    """Glove cut: the back of the hand and the palm are two islands."""
    return (a[:, 1] == 2 * n) & (b[:, 1] == 2 * n)


# ---------------------------------------------------------------- leg and foot

def to_foot(p):
    """Foot frame: x outward, y toward the toes, z up from the ground under the ankle."""
    c, s = np.cos(TOE_OUT), np.sin(TOE_OUT)
    dx, dy = p[:, 0] - ANKLE[0], p[:, 1] - ANKLE[1]
    return np.stack([dx * c + dy * s, dx * s - dy * c, p[:, 2]], axis=1)


def from_foot(l):
    c, s = np.cos(TOE_OUT), np.sin(TOE_OUT)
    l = np.atleast_2d(np.asarray(l, dtype=np.float64))
    return np.stack([ANKLE[0] + l[:, 0] * c + l[:, 1] * s, ANKLE[1] + l[:, 0] * s - l[:, 1] * c, l[:, 2]], axis=1)


TOES = [(V(-0.0270, 0.100, 0.0150), V(-0.0300, 0.136, 0.0135), 0.0118),
        (V(-0.0095, 0.106, 0.0125), V(-0.0110, 0.139, 0.0110), 0.0088),
        (V(0.0055, 0.104, 0.0120), V(0.0060, 0.133, 0.0105), 0.0082),
        (V(0.0190, 0.098, 0.0115), V(0.0210, 0.124, 0.0100), 0.0077),
        (V(0.0310, 0.089, 0.0110), V(0.0340, 0.111, 0.0100), 0.0072)]
CALF = lerp(KNEE, ANKLE, 0.30) + V(0, 0.866, -0.5) * 0.011


def leg_parts(p):
    d = S.smax(S.cone(p, HIP, KNEE, 0.054, 0.037), (lerp(KNEE, HIP, 0.47) - p) @ THIGH, 0.004)  # ends inside the shorts
    d = S.smin(d, S.sphere(p, KNEE + V(0, 0.004, 0), 0.0355), 0.020)
    for sx in (1, -1):                                                              # the joint's knuckles, now at the back
        d = S.smin(d, S.sphere(p, KNEE + V(sx * 0.017, 0.013, -0.002), 0.0185), 0.012)
    cap = S.ellipsoid(p, KNEE + V(0, -0.031, -0.008), V(0.0155, 0.0095, 0.0185))    # the kneecap, left in the fold
    d = S.smin(d, cap, 0.010)
    shin = S.tube(p, [KNEE, CALF, lerp(KNEE, ANKLE, 0.68), ANKLE], [0.0330, 0.0355, 0.0255, 0.0215])
    d = S.smin(d, shin, 0.018)
    l = to_foot(p)
    d = S.smin(d, S.ellipsoid(l, V(0, -0.020, 0.062), V(0.0125, 0.0150, 0.0320)), 0.022)       # heel cord
    foot = S.ellipsoid(l, V(0, -0.028, 0.026), V(0.0245, 0.027, 0.026))
    foot = S.smin(foot, S.ellipsoid(l, V(0, 0.038, 0.034), V(0.031, 0.066, 0.0245), S.rot_x(np.radians(-12.0))), 0.026)
    foot = S.smin(foot, S.ellipsoid(l, V(-0.003, 0.088, 0.0185), V(0.041, 0.030, 0.0185)), 0.016)
    foot = S.smin(foot, S.sphere(l, V(0.0215, -0.008, 0.058), 0.0115), 0.010)
    foot = S.smin(foot, S.sphere(l, V(-0.0205, 0.000, 0.066), 0.0115), 0.010)
    toes, claw = None, None
    for a, b, r in TOES:
        t = S.capsule(l, a, b, r)
        c = S.cone(l, b + V(0, 0.004, 0.0035), b + V(0, r + 0.013, -0.0035), 0.50 * r, 0.0007)
        toes = t if toes is None else S.smin(toes, t, 0.003)
        claw = c if claw is None else np.minimum(claw, c)
    foot = S.smin(S.smin(foot, toes, 0.010), claw, 0.0012)
    foot = S.smax(foot, -l[:, 2], 0.005)
    return dict(d=S.smin(d, foot, 0.016), claw=claw, cap=cap, l=l)


def leg(p):
    return leg_parts(p)["d"]


def leg_detail(p):
    P = leg_parts(p)
    h = 0.00040 * (fbm(p * 240.0, 2) - 0.5)
    s, _ = along(p, KNEE, ANKLE)
    crease = np.exp(-(S.length(p - (KNEE + V(0, -0.034, 0.0))) / 0.018) ** 2)       # skin bunched in the wrong-way fold
    h = h - 0.0006 * crease * np.cos(2 * np.pi * (p[:, 2] - KNEE[2]) / 0.0065 + 3.0 * noise3(p * 60.0))
    h = h + 0.00020 * (noise3(P["l"] * V(1000.0, 60.0, 1000.0)) - 0.5) * smoothstep(0.0008, 0.0, P["claw"])
    return P["d"] - h


def leg_paint(p):
    P = leg_parts(p)
    l = P["l"]
    low = smoothstep(0.34, 0.02, p[:, 2])
    col = skin_tone(p, 0.20 + 0.45 * low)
    col = mix(col, DEAD, 0.55 * smoothstep(0.075, 0.135, l[:, 1]) * smoothstep(0.06, 0.03, p[:, 2]))
    knee = np.exp(-(S.length(p - (KNEE + V(0, -0.032, -0.008))) / 0.024) ** 2)
    col = mix(col, SCAB, 0.65 * knee * smoothstep(0.45, 0.70, fbm(p * 42.0 + 1.7)))
    col = mix(col, BRUISE, 0.5 * knee + 0.45 * smoothstep(0.60, 0.80, fbm(p * 17.0 + 4.0)) * low)
    grime = smoothstep(0.13, 0.0, p[:, 2]) * (0.45 + 0.55 * fbm(p * 26.0)) + 0.8 * smoothstep(0.012, 0.002, p[:, 2])
    col = mix(col, DIRT, 0.85 * grime)
    nail = smoothstep(0.0009, 0.0002, P["claw"])
    col = mix(col, DEAD * 0.7, smoothstep(0.0040, 0.0010, P["claw"]))
    col = mix(col, HORN, nail)
    rough = 0.60 + 0.15 * np.clip(grime, 0, 1)
    rough = rough * (1 - nail) + 0.26 * nail
    return col, rough, np.zeros(len(p)), 1.0 - nail


FOOT_J, SHIN_J, SHIN_K = 18, (2, 7), 38


def leg_boxes(n=1):
    """The foot lies along j (heel -> toes), three cells high; the shin stands on its instep and runs up k past
    the knee. Lattice i is outward."""
    out = from_foot((1, 0, 0))[0] - from_foot((0, 0, 0))[0]
    toe = from_foot((0, 1, 0))[0] - from_foot((0, 0, 0))[0]
    foot = Box(np.array((0, 0, 0)) * n, np.array((6, FOOT_J, 3)) * n, 1,
               from_foot([(0, -0.042, 0.026), (0, 0.020, 0.030), (-0.002, 0.090, 0.017), (-0.002, 0.134, 0.012)]),
               [0.019, 0.024, 0.031, 0.027], [0.019, 0.021, 0.012, 0.0075], out, UP, cap=(0.5, 0.4))
    shin = Box(np.array((0, SHIN_J[0], 3)) * n, np.array((6, SHIN_J[1], 3 + SHIN_K)) * n, 2,
               [ANKLE + V(0, 0, -0.022), lerp(KNEE, ANKLE, 0.5), KNEE, lerp(KNEE, HIP, 0.44)],
               [0.016, 0.022, 0.026, 0.030], [0.016, 0.022, 0.026, 0.030], out, toe, cap=(0.0, 0.5))
    return [foot, shin]


def leg_seam(a, b, n=1):
    """Three islands: the sole, the top of the foot opened down the heel, and the shin opened up its back."""
    def on(c):
        i, j, k = c[:, 0], c[:, 1], c[:, 2]
        rim = (k == 0) & ((i == 0) | (i == 6 * n) | (j == 0) | (j == FOOT_J * n))
        back = (i == 3 * n) & (((j == SHIN_J[0] * n) & (k >= 3 * n)) | ((k == 3 * n) & (j <= SHIN_J[0] * n)) | (j == 0))
        return rim, back, k == 6 * n
    ra, ba, aa = on(a)
    rb, bb, ab = on(b)
    return (ra & rb) | (ba & bb) | (aa & ab)


# ---------------------------------------------------------------- shirt and braces

def torso_body(p):
    q = S.mirror_x(p)
    d = S.smin(S.ellipsoid(p, V(0, -0.030, 0.885), V(0.106, 0.078, 0.118)),
               S.ellipsoid(p, V(0, -0.008, 0.745), V(0.088, 0.066, 0.100)), 0.05)
    d = S.smin(d, S.ellipsoid(q, SHOULDER + V(-0.012, 0.002, -0.004), V(0.040, 0.040, 0.042)), 0.035)
    d = S.smin(d, S.cone(q, V(0.025, -0.052, 1.010), SHOULDER + V(-0.012, 0, 0.014), 0.030, 0.026), 0.030)
    d = S.smin(d, S.ellipsoid(p, V(0, -0.046, 0.972), V(0.088, 0.060, 0.046)), 0.030)       # collarbones round the neck
    return S.smin(d, S.ellipsoid(p, V(0, 0.022, 0.930), V(0.085, 0.050, 0.075)), 0.040)     # a rounded, hunched back


def spine_y(z):
    return -0.132 * (z - 0.66)


NECK_DIR = S.normalize(NECK_B - NECK_A)
COLLAR = V(0, -0.0690, 1.036)
BUTTON_Z = 0.728 + 0.060 * np.arange(5)
_buttons = None


def _shirt_cloth(p, fine=True):
    """The shirt before its openings, trim and braces. Returns distance and distance along the forearm.
    fine adds the folds too small for the game mesh, which reach it through the normal map."""
    q = S.mirror_x(p)
    z = p[:, 2]
    wob = noise3(p * 16.0)
    th = np.arctan2(p[:, 0], p[:, 1] - spine_y(z))
    body = torso_body(p) - 0.007 - 0.009 * bump(z, 0.742, 0.035) - 0.004 * (fbm(p * V(11.0, 11.0, 5.0)) - 0.5)
    if fine:
        body = body - 0.0030 * smoothstep(0.88, 0.76, z) * np.sin(17.0 * th + 6.0 * wob)       # gathers above the waistband
    body = S.smax(body, 0.672 - z, 0.003)
    hs, _ = along(q, ELBOW, WRIST)
    us, _ = along(q, SHOULDER, ELBOW)
    s = np.where(hs > 0, hs, us - np.linalg.norm(ELBOW - SHOULDER))
    arm_ = S.tube(q, [SHOULDER, ELBOW, lerp(ELBOW, WRIST, 0.55)], [0.031, 0.0245, 0.0235])
    arm_ = arm_ - 0.008 - 0.004 * smoothstep(0.0, 0.12, hs) \
        - 0.0026 * np.exp(-(s / 0.07) ** 2) * np.sin(2 * np.pi * s / 0.046 + 4.0 * wob + 1.3 * np.sin(55.0 * (q @ BACK)))
    cuff = (CUFF - ELBOW) @ FORE
    if fine:
        arm_ = arm_ - 0.0022 * np.exp(-(s / 0.055) ** 2) * np.sin(2 * np.pi * s / 0.017 + 9.0 * wob + 2.0 * np.sin(70.0 * (q @ LEFT))) \
            - 0.003 * (fbm(q * 30.0) - 0.5) - 0.0015 * smoothstep(cuff - 0.015, cuff - 0.012, hs)
    arm_ = S.smax(arm_, (q - CUFF) @ FORE, 0.0015)
    return S.smin(body, arm_, 0.022), hs


def _button_points():
    global _buttons
    if _buttons is None:
        lo, hi = np.full(5, -0.30), np.full(5, spine_y(BUTTON_Z))
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            inside = _shirt_cloth(np.stack([np.zeros(5), mid, BUTTON_Z], axis=1))[0] < 0
            lo, hi = np.where(inside, lo, mid), np.where(inside, mid, hi)
        _buttons = np.stack([np.zeros(5), 0.5 * (lo + hi) - 0.0022, BUTTON_Z], axis=1)
    return _buttons


def shirt(p):
    """The shirt the game mesh is fitted to: broad forms only."""
    return _shirt_cloth(p, False)[0]


def shirt_parts(p):
    q = S.mirror_x(p)
    z = p[:, 2]
    cloth, hs = _shirt_cloth(p)
    front = p[:, 1] < spine_y(z)
    placket = np.where(front, np.abs(p[:, 0]) - 0.0115, 1.0)
    d = np.minimum(cloth, S.smax(cloth - 0.0011, placket, 0.0006))
    collar = S.torus(p, COLLAR, NECK_DIR, NECK_R + 0.0075, 0.0058)
    button = None
    for c in _button_points():
        b = S.ellipsoid(p, c, V(0.0058, 0.0024, 0.0058))
        button = b if button is None else np.minimum(button, b)
    d = np.minimum(d, button)
    # braces: straight up the front, over the shoulders, meeting in a Y between the shoulder blades
    xc = np.where(front, 0.050 + 0.026 * np.clip((z - 0.70) / 0.32, 0, 1), 0.076 * np.clip((z - 0.80) / 0.22, 0, 1))
    slab = np.maximum(np.abs(q[:, 0] - xc) - 0.0125, 0.700 - z)
    brace = S.smax(d - 0.0030, slab, 0.0008)
    return dict(d=np.minimum(d, brace), brace=slab, button=button, collar=collar, placket=placket, hs=hs, cloth=cloth)


def shirt_detail(p):
    P = shirt_parts(p)
    crumple = 0.0011 * (fbm(p * 75.0, 2) - 0.5) * (P["brace"] > 0)
    edge = 0.0004 * smoothstep(0.0012, 0.0, np.abs(P["brace"] + 0.0022))            # a stitched line inside each strap edge
    return P["d"] - crumple + edge


LINEN = V(0.60, 0.565, 0.485)
GRIME = V(0.33, 0.29, 0.23)
LEATHER = V(0.135, 0.085, 0.060)
BONE = V(0.74, 0.70, 0.60)


def shirt_paint(p):
    P = shirt_parts(p)
    z = p[:, 2]
    col = np.tile(LINEN, (len(p), 1)) * (0.93 + 0.14 * fbm(p * 28.0))[:, None]
    cuff = (CUFF - ELBOW) @ FORE
    dirty = smoothstep(cuff - 0.07, cuff, P["hs"]) + smoothstep(0.03, 0.0, P["collar"]) * 0.7 \
        + smoothstep(0.80, 0.70, z) * 0.35 + smoothstep(0.55, 0.80, fbm(p * 9.0 + 5.0)) * 0.55
    col = mix(col, GRIME, 0.75 * dirty)
    col = mix(col, V(0.33, 0.20, 0.16), 0.5 * smoothstep(0.62, 0.78, fbm(p * 6.0 + 21.0)) * smoothstep(0.86, 0.98, z))
    strap = (P["brace"] < 0) & (P["button"] > 0.0005)
    col = np.where(strap[:, None], LEATHER * (0.8 + 0.5 * fbm(p * 120.0))[:, None], col)
    button = P["button"] < 0.0006
    col = np.where(button[:, None], BONE, col)
    rough = np.where(strap, 0.52, 0.92)
    rough = np.where(button, 0.38, rough)
    return col, rough, np.zeros(len(p)), 1.0 - (strap | button)


def collar(segs=28):
    """A band collar standing round the neck, notched where it buttons. Returns verts, quads, normals and
    chart coordinates (u round the neck, v across the band)."""
    frame = Frame(COLLAR, NECK_DIR, LEFT)
    profile = np.array([(0.0125, -0.0160), (0.0120, -0.0040), (0.0105, 0.0060), (0.0080, 0.0095), (0.0050, 0.0090),
                        (0.0030, 0.0040), (0.0025, -0.0080)])
    ang = 2 * np.pi * np.arange(segs + 1) / segs
    notch = 1.0 - 0.55 * np.exp(-((np.abs(ang - 1.5 * np.pi)) / 0.14) ** 2)         # local -y is the figure's front
    r = NECK_R + profile[None, :, 0] + 0.0 * ang[:, None]
    h = np.where(profile[None, :, 1] > 0, profile[None, :, 1] * notch[:, None], profile[None, :, 1])
    P = frame.w(np.stack([r * np.cos(ang)[:, None], r * np.sin(ang)[:, None], h], axis=-1).reshape(-1, 3)).reshape(segs + 1, -1, 3)
    n = S.normalize(np.cross(np.gradient(P, axis=1), np.gradient(P, axis=0)))
    m = P.shape[1]
    quads = [(i * m + j, (i + 1) * m + j, (i + 1) * m + j + 1, i * m + j + 1) for i in range(segs) for j in range(m - 1)]
    chart = np.stack(np.meshgrid(np.linspace(0, 1, segs + 1), np.linspace(0, 1, m), indexing="ij"), axis=-1)
    return P.reshape(-1, 3), quads, n.reshape(-1, 3), chart.reshape(-1, 2)


def collar_paint(c):
    p = np.stack([c[:, 0] * 9.0, c[:, 1] * 2.0, np.zeros(len(c))], axis=1)
    col = np.tile(LINEN, (len(c), 1)) * (0.90 + 0.14 * fbm(p * 3.0))[:, None]
    col = mix(col, GRIME, 0.35 + 0.45 * smoothstep(0.35, 0.75, c[:, 1]) + 0.3 * fbm(p + 4.0))
    return col, np.full(len(c), 0.92), np.zeros(len(c)), np.ones(len(c))


SHIRT_I, SHIRT_J, SHIRT_K, SLEEVE, SLEEVE_N, SLEEVE_J = 8, 6, 34, 7, 24, -4


def shirt_boxes(n=1):
    """A torso with a sleeve from each flank. Lattice: i to the figure's left, j backward, k up."""
    trunk = Box(np.array((-SHIRT_I, -SHIRT_J, 0)) * n, np.array((SHIRT_I, SHIRT_J, SHIRT_K)) * n, 2,
                [V(0, 0.002, 0.660), V(0, -0.010, 0.750), V(0, -0.028, 0.880), V(0, -0.042, 0.990)],
                [0.080, 0.086, 0.094, 0.082], [0.062, 0.066, 0.066, 0.046], LEFT, BACK, cap=(0.0, 0.5))
    boxes = [trunk]
    arm_path = [SHOULDER + V(-0.03, 0, 0), ELBOW, CUFF + FORE * 0.004]
    for side in (1, -1):
        path = [q * V(side, 1, 1) for q in arm_path][::side]
        lo = (SHIRT_I if side > 0 else -SHIRT_I - SLEEVE_N, SLEEVE_J, SHIRT_K - SLEEVE)
        hi = (lo[0] + SLEEVE_N, lo[1] + SLEEVE, SHIRT_K)
        boxes.append(Box(np.array(lo) * n, np.array(hi) * n, 0, path, 0.026, 0.026, BACK, UP,
                         cap=(0.0, 0.2) if side > 0 else (0.2, 0.0)))
    return boxes


def shirt_seam(a, b, n=1):
    """Cut like the garment: front and back panels joined at the sides and shoulders, set-in sleeves seamed
    underneath."""
    def on(c):
        i, j, k = c[:, 0], c[:, 1], c[:, 2]
        ai = np.abs(i)
        side = (ai == SHIRT_I * n) & (j == 0) & (k <= (SHIRT_K - SLEEVE) * n)
        shoulder = (k == SHIRT_K * n) & (j == 0) & (ai <= SHIRT_I * n)
        hole = (ai == SHIRT_I * n) & (j >= SLEEVE_J * n) & (j <= (SLEEVE_J + SLEEVE) * n) & (k >= (SHIRT_K - SLEEVE) * n)
        under = (ai >= SHIRT_I * n) & (k == (SHIRT_K - SLEEVE) * n) & (j == 0)
        return side | shoulder | under, hole
    sa, ha = on(a)
    sb, hb = on(b)
    return (sa & sb) | (ha & hb)


# ---------------------------------------------------------------- short trousers

def _shorts_base(p):
    q = S.mirror_x(p)
    z = p[:, 2]
    body = S.smin(S.ellipsoid(p, V(0, 0.020, 0.645), V(0.106, 0.083, 0.088)),
                  S.ellipsoid(q, V(0.050, 0.072, 0.612), V(0.058, 0.052, 0.062)), 0.03)
    wob = fbm(p * V(14.0, 14.0, 9.0)) - 0.5
    body = body - 0.012 - 0.006 * wob - 0.0035 * bump(z, 0.555, 0.03) * (p[:, 1] > 0.05) * np.sin(2 * np.pi * z / 0.021 + 5.0 * wob)
    hs, _ = along(q, HIP, KNEE)
    leg_ = S.cone(q, HIP, lerp(HIP, KNEE, 0.85), 0.056, 0.040)
    hem = (HEM - HIP) @ THIGH
    leg_ = leg_ - 0.012 - 0.012 * smoothstep(0.05, 0.24, hs) - 0.007 * wob - 0.0018 * smoothstep(hem - 0.020, hem - 0.017, hs)
    leg_ = S.smax(leg_, (q - HEM) @ THIGH, 0.0015)
    d = S.smin(body, leg_, 0.03)
    d = d - 0.0022 * smoothstep(0.688, 0.691, z)
    return S.smax(d, z - 0.722, 0.003), hs


def shorts_parts(p):
    d, hs = _shorts_base(p)
    q = S.mirror_x(p)
    button = S.ellipsoid(q, V(0.050, -0.078, 0.706), V(0.0060, 0.0035, 0.0060))     # brace buttons on the waistband
    button = np.minimum(button, S.ellipsoid(p, V(0, 0.103, 0.706), V(0.0060, 0.0035, 0.0060)))
    return dict(d=np.minimum(d, button), button=button, hs=hs)


def shorts(p):
    return _shorts_base(p)[0]


def shorts_detail(p):
    P = shorts_parts(p)
    return P["d"] - 0.0010 * (fbm(p * 80.0, 2) - 0.5) * (P["button"] > 0.0005)


WOOL = V(0.150, 0.135, 0.125)
BRASS = V(0.72, 0.55, 0.27)


def shorts_paint(p):
    P = shorts_parts(p)
    z = p[:, 2]
    col = np.tile(WOOL, (len(p), 1)) * (0.80 + 0.40 * fbm(p * 32.0))[:, None]
    hem = (HEM - HIP) @ THIGH
    worn = smoothstep(hem - 0.05, hem, P["hs"]) * 0.6 + smoothstep(0.55, 0.80, fbm(p * 11.0 + 8.0)) * 0.5
    col = mix(col, V(0.27, 0.235, 0.20), 0.6 * worn)
    button = P["button"] < 0.0006
    col = np.where(button[:, None], BRASS, col)
    rough = np.where(button, 0.36, 0.95 - 0.1 * (z > 0.69))
    return col, rough, button.astype(np.float64), 1.0 - button


SHORTS_I, SHORTS_J, SHORTS_K, SHORTS_LEG = 8, 6, 12, 14


def shorts_boxes(n=1):
    """A seat with a leg from each half of its underside, a two-cell gusset between them."""
    seat = Box(np.array((-SHORTS_I, -SHORTS_J, 0)) * n, np.array((SHORTS_I, SHORTS_J, SHORTS_K)) * n, 2,
               [V(0, 0.030, 0.575), V(0, 0.022, 0.650), V(0, 0.010, 0.716)], [0.092, 0.098, 0.092], [0.078, 0.082, 0.072],
               LEFT, BACK, cap=(0.2, 0.0))
    boxes = [seat]
    for side in (1, -1):
        lo = (1, -SHORTS_J, -SHORTS_LEG) if side > 0 else (-SHORTS_I, -SHORTS_J, -SHORTS_LEG)
        hi = (lo[0] + SHORTS_I - 1, SHORTS_J, 0)
        path = [(HEM + THIGH * 0.003) * V(side, 1, 1), lerp(HIP, KNEE, 0.40) * V(side, 1, 1), V(side * 0.062, 0.040, 0.600)]
        boxes.append(Box(np.array(lo) * n, np.array(hi) * n, 2, path, [0.046, 0.040, 0.036], [0.050, 0.046, 0.044],
                         LEFT, BACK, cap=(0.2, 0.0)))
    return boxes


def shorts_seam(a, b, n=1):
    """Two halves joined down the centre front and back, each leg closed by its inseam."""
    def on(c):
        i, j, k = c[:, 0], c[:, 1], c[:, 2]
        centre = (i == 0) & (k >= 0)
        inseam = (np.abs(i) == n) & (j == 0) & (k <= 0)
        gusset = (np.abs(i) <= n) & (j == 0) & (k == 0)
        return centre | inseam | gusset
    return on(a) & on(b)

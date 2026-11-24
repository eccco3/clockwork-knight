"""The grinner's head: a ten-year-old's face with black eyes and a grin that runs past them.

Head frame as the knight's: origin between the eyes at the centre of the skull, +y out of the face,
+z up, metres; the sculpt is symmetric in x. `field` is the form the game mesh is fitted to,
`detail` adds hair strands and creases for the normal map, `paint` colours surface points.
The teeth and eyeballs are separate small meshes made by `teeth` and `eyeball`.
"""
import numpy as np
from sculpt import sdf as S
from sculpt.sdf import V
from . import body
from sculpt.num import smoothstep, bump, noise3, fbm, mix

H0 = V(0, -0.108, 1.130)                       # head frame origin in the figure's rest pose


def to_head(p):
    return (p - H0) * V(-1, -1, 1)


def from_head(p):
    return H0 + np.asarray(p) * V(-1, -1, 1)


EYE = V(0.0310, 0.0530, 0.0000)                # eyeball centre (mirrored)
EYE_R = 0.0142
LID_T = 0.0015
AP_W, AP_UP, AP_LO, AP_TILT = 1.04, 0.60, 0.46, 0.02       # held wide open: the eyes do not smile

# the mouth lies on an ellipse seen from above (the front of the teeth), measured by the angle th round it
MA, MB, MYC = 0.0470, 0.0500, 0.0280
TH_M = 1.318                                   # the corners: wider than the eyes
MZ0, RISE, MH = -0.0560, 0.0200, 0.0080        # height at the centre, lift at the corners, half-opening
RHO_LIP, RHO_IN = 1.050, 0.80                  # lips and back of the mouth, as fractions of the tooth ellipse
ARC = 0.05                                     # metres per unit of rho or radian of th, near enough

NECK_A, NECK_B = to_head(body.NECK_A), to_head(body.NECK_B)
EAR = V(0.0740, -0.0170, -0.0050)
EAR_R = S.euler(z=24.0)
HAIR_C, HAIR_R = V(0, -0.015, 0.032), V(0.0820, 0.1000, 0.0930)
WHORL = S.normalize(V(0.10, -0.42, 0.90))      # the crown the hair falls from
HAIRLINE_AZ = np.radians([0, 35, 62, 85, 105, 125, 150, 180])
HAIRLINE_Z = np.array([0.0355, 0.0345, 0.0300, 0.0200, 0.0100, -0.0200, -0.0420, -0.0500])


def _aperture(q):
    """Angular eye opening in the mirrored frame: < 0 inside (metres on the eyeball)."""
    d = q - EYE
    r = np.maximum(S.length(d), 1e-9)
    th = np.arctan2(d[:, 0], d[:, 1])
    ph = np.arcsin(np.clip(d[:, 2] / r, -1, 1))
    s = th / AP_W
    s2 = np.clip(1.0 - s * s, 0.0, 1.0)
    up = AP_UP * s2 ** 0.62 * (1.0 - 0.10 * s) + AP_TILT * s
    lo = -AP_LO * s2 ** 0.70 * (1.0 + 0.12 * s) + AP_TILT * s
    g = np.maximum(ph - up, lo - ph)
    g = np.where(np.abs(s) < 1.0, g, np.hypot((np.abs(s) - 1.0) * AP_W, ph - AP_TILT * np.sign(s)) + 0.004)
    return g * EYE_R, th, ph, up, lo


def _mouth(q):
    """Mouth opening in the mirrored frame: g < 0 inside, with the angle and radius on the tooth ellipse."""
    ex, ey = q[:, 0] / MA, (q[:, 1] - MYC) / MB
    th, rho = np.arctan2(ex, ey), np.hypot(ex, ey)
    s = th / TH_M
    zm = MZ0 + RISE * np.clip(s, 0.0, 1.0) ** 2.2
    hh = MH * np.clip(1.0 - s * s, 0.0, 1.0) ** 0.36
    g = np.where(s < 1.0, np.abs(q[:, 2] - zm) - hh, np.hypot((th - TH_M) * ARC, q[:, 2] - (MZ0 + RISE)) + 0.0004)
    return g, th, rho, zm, hh


def _hairline(q, rough=True):
    az = np.arctan2(q[:, 0], q[:, 1] - HAIR_C[1])
    z = np.interp(az, HAIRLINE_AZ, HAIRLINE_Z)
    if rough:                                                    # the fringe hangs in uneven locks
        lock = noise3(np.stack([az * 7.0, np.zeros(len(az)), np.zeros(len(az))], axis=1)) - 0.5
        fine = noise3(np.stack([az * 23.0, np.ones(len(az)), np.zeros(len(az))], axis=1)) - 0.5
        z = z + (0.010 * lock + 0.004 * fine) * smoothstep(2.6, 1.2, az)
    return z


def _parts(p, fine=True):
    q = S.mirror_x(p)
    z = p[:, 2]
    P = {}
    # ---- skull and the soft masses of a child's face
    d = S.smin(S.ellipsoid(p, V(0, -0.014, 0.030), V(0.0745, 0.0930, 0.0870)),
               S.ellipsoid(p, V(0, 0.018, -0.034), V(0.0520, 0.0620, 0.0620)), 0.032)
    jaw = S.tube(q, [V(0, 0.0600, -0.0830), V(0.0140, 0.0520, -0.0810), V(0.0280, 0.0280, -0.0740),
                     V(0.0365, 0.0040, -0.0590), V(0.0460, -0.0100, -0.0340), V(0.0510, -0.0140, -0.0040)],
                 [0.0115, 0.0112, 0.0108, 0.0105, 0.0120, 0.0125])
    d = S.smin(d, jaw, 0.024)
    d = S.smin(d, S.ellipsoid(p, V(0, 0.0690, -0.0850), V(0.0140, 0.0110, 0.0115)), 0.016)
    d = S.smin(d, S.ellipsoid(q, V(0.0360, 0.0450, -0.0230), V(0.0225, 0.0225, 0.0260)), 0.030)
    d = S.smin(d, S.ellipsoid(q, V(0.0500, 0.0200, -0.0140), V(0.0150, 0.0260, 0.0120)), 0.026)
    d = S.smin(d, S.ellipsoid(q, V(0.0290, 0.0570, 0.0225), V(0.0250, 0.0105, 0.0085), S.euler(z=-14, y=6)), 0.016)
    d = S.ssub(d, S.ellipsoid(q, V(0.0270, 0.0850, 0.0040), V(0.0215, 0.0215, 0.0135), S.euler(y=-10)), 0.014)
    d = S.ssub(d, S.ellipsoid(p, V(0, 0.0870, 0.0020), V(0.0190, 0.0115, 0.0095)), 0.010)
    # ---- nose: short, soft, turned up
    bridge = S.tube(p, [V(0, 0.0660, 0.0060), V(0, 0.0720, -0.0100), V(0, 0.0790, -0.0210), V(0, 0.0845, -0.0270)],
                    [0.0068, 0.0052, 0.0054, 0.0058])
    d = S.smin(d, bridge, 0.0110)
    nose = S.smin(S.ellipsoid(p, V(0, 0.0872, -0.0300), V(0.0074, 0.0068, 0.0062)),
                  S.ellipsoid(q, V(0.0102, 0.0780, -0.0330), V(0.0048, 0.0066, 0.0050), S.euler(z=-18)), 0.0060)
    nose = S.smin(nose, S.tube(p, [V(0, 0.0875, -0.0335), V(0, 0.0790, -0.0365)], [0.0032, 0.0034]), 0.0050)
    d = S.smin(d, S.smin(nose, bridge, 0.0070), 0.0060)
    nostril = S.ellipsoid(q, V(0.0058, 0.0822, -0.0372), V(0.0030, 0.0044, 0.0026), S.euler(z=-25, x=18))
    P["nostril"] = nostril
    d = S.ssub(d, nostril, 0.0030)
    # ---- the grin: skin drawn tight over a row of teeth, a thin lip round a slot cut back to the dark
    g, th, rho, zm, hh = _mouth(q)
    s = th / TH_M
    off = z - (zm - 0.003)
    band = np.maximum((rho - 1.040) * ARC + 0.0045 * (off / np.where(off > 0, 0.015, 0.022)) ** 2, (th - TH_M - 0.10) * ARC)
    band = np.maximum(band, (0.80 - rho) * ARC)                 # a rind over the teeth, not a solid
    d = S.smin(d, band, 0.012)
    apple = S.ellipsoid(q, V(0.0440, 0.0440, -0.0210), V(0.0150, 0.0150, 0.0130))  # the cheek the corner pushes up
    d = S.smin(d, apple, 0.014)
    lip_r = np.where(z > zm, 0.0025, 0.0036) * (0.55 + 0.45 * np.clip(1.0 - s * s, 0.0, 1.0))
    lip = np.hypot(g - 0.0016, (rho - RHO_LIP) * ARC) - lip_r
    d = S.smin(d, lip, 0.0035)
    d = S.smax(d, -np.maximum(g, (RHO_IN - rho) * ARC), 0.0008)
    dimple = S.tube(q, [V(0.0500, 0.0400, -0.0240), V(0.0545, 0.0345, -0.0350), V(0.0520, 0.0360, -0.0480)],
                    [0.0016, 0.0026, 0.0014])
    d = S.ssub(d, dimple, 0.0045)
    d = S.ssub(d, S.tube(p, [V(0, 0.0835, -0.0400), V(0, 0.0850, -0.0455)], [0.0018, 0.0022]), 0.0040)
    d = S.ssub(d, S.ellipsoid(p, V(0, 0.0830, -0.0770), V(0.0130, 0.0050, 0.0030)), 0.0060)
    P["lip"], P["mouth_g"], P["rho"], P["mouth_s"] = lip, g, rho, s
    # ---- eyelids: a shell over the eyeball, open across the aperture
    ga, tha, ph, up, lo = _aperture(q)
    r_eye = S.length(q - EYE)
    upper_side = ph > 0.5 * (up + lo)
    fade = np.clip((ga - 0.0025) / np.where(upper_side, 0.0100, 0.0050), 0.0, 1.0)
    shell = r_eye - (EYE_R + LID_T - 0.0065 * fade * fade * (3.0 - 2.0 * fade))
    d = S.smin(d, shell, 0.0080)
    fold_r = 0.0020 * np.clip(1.0 - (np.abs(tha / AP_W) / 0.95) ** 4, 0.0, 1.0)
    fold = np.hypot(r_eye - (EYE_R + LID_T + 0.0016), (ph - (up + 0.24)) * (EYE_R + LID_T)) - fold_r
    fold = np.where(fold_r > 1e-5, fold, 1.0)
    d = S.ssub(d, fold, 0.0020)
    bag = np.hypot(r_eye - (EYE_R + LID_T + 0.0012), (ph - (lo - 0.30)) * (EYE_R + LID_T)) - fold_r * 0.8
    bag = np.where(fold_r > 1e-5, bag, 1.0)
    d = S.ssub(d, bag, 0.0030)
    cut = np.maximum(np.maximum(ga, r_eye - (EYE_R + 0.0045)), (EYE_R - 0.0012) - r_eye)
    d = S.smax(d, -cut, 0.0005)
    P["lid_g"], P["lid_ph"], P["lid_up"], P["lid_lo"], P["lid_th"], P["r_eye"] = ga, ph, up, lo, tha, r_eye
    P["fold"] = np.minimum(fold, bag)
    # ---- ears that stand off the head
    e = (q - EAR) @ EAR_R
    ear = S.ellipsoid(e, V(0, 0, 0), V(0.0055, 0.0150, 0.0255))
    ear = S.ssub(ear, S.ellipsoid(e, V(0.0065, 0.0015, -0.0020), V(0.0055, 0.0085, 0.0160)), 0.0030)
    ear = S.smin(ear, S.tube(e, [V(0.0030, -0.0030, 0.0130), V(0.0034, 0.0010, 0.0020), V(0.0030, -0.0020, -0.0090)],
                             [0.0020, 0.0026, 0.0020]), 0.0030)
    ear = S.ssub(ear, S.ellipsoid(e, V(0.0050, 0.0050, -0.0040), V(0.0050, 0.0048, 0.0070)), 0.0025)
    ear = S.smin(ear, S.sphere(e, V(0.0020, 0.0110, -0.0040), 0.0034), 0.0030)
    d = S.smin(d, ear, 0.0090)
    P["skin"] = d
    # ---- neck
    d = S.smin(d, S.capsule(p, NECK_A, NECK_B, body.NECK_R), 0.028)
    cord = S.tube(q, [V(0.0420, -0.0260, -0.0420), V(0.0260, -0.0180, -0.1000), V(0.0100, -0.0260, -0.1500)], 0.0075)
    d = S.smin(d, cord, 0.014)
    d = S.smin(d, S.ellipsoid(p, V(0, 0.0240, -0.0780), V(0.0240, 0.0320, 0.0120)), 0.022)       # soft under the chin
    # ---- hair: a heavy bowl cut, the fringe low over the brows
    shell = S.ellipsoid(p, HAIR_C, HAIR_R)
    hair = S.smax(shell, _hairline(q) - z, 0.0035)
    hair = hair - _strands(p, fine)
    P["hair"], P["flesh"] = hair, d
    d = S.smin(d, hair, 0.0030)
    P["d"] = S.smax(d, -0.128 - z, 0.004)
    return P


def _strands(p, fine=True):
    """Height of the hair's locks above its smooth shell; fine adds the strands."""
    v = p - HAIR_C
    h = v @ WHORL
    side = v - np.outer(h, WHORL)
    ex = S.normalize(np.cross(WHORL, V(0, 1, 0)))
    ey = np.cross(WHORL, ex)
    az = np.arctan2(side @ ex, side @ ey)
    pol = np.arctan2(S.length(side), h)
    swirl = az + 0.9 * pol + 0.35 * np.sin(3.0 * pol + 2.0 * az)
    fall = smoothstep(0.05, 0.5, pol)
    cs, sn = np.cos(swirl), np.sin(swirl)                         # round the crown without a join
    lock = 0.0045 * fall * (noise3(np.stack([cs * 4.5, sn * 4.5, pol * 1.5], axis=1)) - 0.5)
    if not fine:
        return lock
    strand = noise3(np.stack([cs * 19.0, sn * 19.0, pol * 2.5 + 3.0], axis=1))
    hair_ = noise3(np.stack([cs * 60.0, sn * 60.0, pol * 4.0 + 7.0], axis=1))
    return lock + fall * (0.0012 * (strand - 0.5) + 0.0005 * (hair_ - 0.5))


def field(p):
    return _parts(p, False)["d"]


def detail(p):
    P = _parts(p)
    h = 0.00030 * (fbm(p * 300.0, 2) - 0.5) * (P["hair"] > P["flesh"])
    return P["d"] - h


def density(p):
    """Mesh density weight: finer quads over the eyes, the nose, the long mouth and the ears."""
    q = S.mirror_x(p)
    front = np.clip((p[:, 1] - 0.020) / 0.030, 0, 1) * np.clip((0.040 - p[:, 2]) / 0.015, 0, 1) \
        * np.clip((p[:, 2] + 0.100) / 0.015, 0, 1)
    eye = np.exp(-((q[:, 0] - EYE[0]) ** 2 + (p[:, 2] - EYE[2]) ** 2) / (2 * 0.018 ** 2))
    g, th, rho, zm, hh = _mouth(q)
    mouth = np.exp(-(np.maximum(g, 0.0) / 0.009) ** 2) * (p[:, 1] > 0.0)
    nose = np.exp(-(p[:, 0] ** 2 + (p[:, 2] + 0.032) ** 2) / (2 * 0.010 ** 2))
    ear = np.exp(-(S.length(q - EAR) / 0.028) ** 2)
    corner = np.exp(-(S.length(q - V(MA * np.sin(TH_M), MYC + MB * np.cos(TH_M), MZ0 + RISE)) / 0.012) ** 2)
    return 1.0 + front * (4.0 + 12.0 * eye + 10.0 * nose) + 12.0 * mouth + 9.0 * ear + 22.0 * corner


def face(p):
    """1 over the face, 0 elsewhere: the part of the head that deserves the most texels."""
    return smoothstep(0.0, 0.045, p[:, 1]) * smoothstep(0.050, 0.030, p[:, 2]) * smoothstep(-0.105, -0.090, p[:, 2])


# ---------------------------------------------------------------- edge loops for the mesher

def lid_edge(p):
    q = S.mirror_x(p)
    return np.maximum(_aperture(q)[0], S.length(q - EYE) - (EYE_R + 0.006))


def lid_inner(p):
    sx = np.where(p[:, 0] < 0, -1.0, 1.0)
    c = EYE * np.stack([sx, np.ones(len(p)), np.ones(len(p))], axis=1)
    return c + S.normalize(p - c) * (EYE_R - 0.0011)


def lip_edge(p):
    q = S.mirror_x(p)
    g, th, rho, zm, hh = _mouth(q)
    return np.maximum(g, 0.75 - rho)


def lip_inner(p):
    """Drop points just inside the lips straight back to the dark wall behind the teeth."""
    rho = np.hypot(p[:, 0] / MA, (p[:, 1] - MYC) / MB)
    k = (RHO_IN - 0.004) / np.maximum(rho, 1e-9)
    return np.stack([p[:, 0] * k, MYC + (p[:, 1] - MYC) * k, p[:, 2]], axis=1)


FEATURES = [(lid_edge, lid_inner, 5e-4), (lip_edge, lip_inner, 5e-4)]


# ---------------------------------------------------------------- paint

HAIR = V(0.075, 0.060, 0.055)
LIP = V(0.40, 0.235, 0.265)
MAW = V(0.045, 0.012, 0.015)
RIM = V(0.42, 0.22, 0.24)
SUNK = V(0.36, 0.28, 0.37)
FLUSH = V(0.76, 0.56, 0.57)
FRECKLE = V(0.52, 0.37, 0.28)
VEIN = V(0.44, 0.42, 0.56)
BROW_PTS = np.array([(0.0140, 0.0205), (0.0210, 0.0235), (0.0290, 0.0250), (0.0370, 0.0250), (0.0450, 0.0228), (0.0510, 0.0195)])
BROW_W = np.array([0.0016, 0.0020, 0.0019, 0.0015, 0.0010, 0.0004])


def _brow(x, z):
    best, along_ = np.full(len(x), 1e9), np.zeros(len(x))
    for k in range(len(BROW_PTS) - 1):
        a, b = BROW_PTS[k], BROW_PTS[k + 1]
        ab = b - a
        t = np.clip(((x - a[0]) * ab[0] + (z - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        dist = np.hypot(x - (a[0] + ab[0] * t), z - (a[1] + ab[1] * t)) - (BROW_W[k] + (BROW_W[k + 1] - BROW_W[k]) * t)
        better = dist < best
        best, along_ = np.where(better, dist, best), np.where(better, k + t, along_)
    lean = np.radians(58 - 9 * along_)
    v = -x * np.sin(lean) + z * np.cos(lean)
    hairs = 0.55 + 0.45 * noise3(np.stack([v * 3600.0, (x * np.cos(lean) + z * np.sin(lean)) * 400.0, np.zeros(len(x))], axis=1))
    return np.clip(-best / 0.0009, 0, 1) * hairs


def paint(p):
    """Albedo, roughness and metallic at points on the head's surface."""
    P = _parts(p)
    q = S.mirror_x(p)
    z = p[:, 2]
    col = body.skin_tone(p, 0.12)
    front = np.clip((p[:, 1] - 0.015) / 0.020, 0, 1)
    flush = bump(q[:, 0], 0.040, 0.016) * bump(z, -0.022, 0.014) + bump(p[:, 0], 0.0, 0.010) * bump(z, -0.030, 0.008)
    ear = np.exp(-(S.length(q - EAR) / 0.024) ** 2)
    col = mix(col, FLUSH, 0.40 * flush * front + 0.45 * ear)
    freckle = smoothstep(0.68, 0.76, noise3(p * 700.0)) * bump(z, -0.016, 0.018) * bump(q[:, 0], 0.014, 0.036) * front
    col = mix(col, FRECKLE, 0.42 * freckle)
    socket = np.exp(-(np.maximum(P["r_eye"] - EYE_R, 0.0) / 0.0105) ** 2) * front
    col = mix(col, SUNK, 0.62 * socket)
    web = smoothstep(0.035, 0.0, np.abs(fbm(p * 55.0, 2) - 0.5)) * (socket + bump(q[:, 0], 0.050, 0.012) * bump(z, -0.036, 0.016))
    col = mix(col, VEIN, 0.30 * web)
    g = P["lid_g"]
    on_lid = (P["r_eye"] < EYE_R + 0.0045) & (g > -0.0006)
    col = mix(col, RIM, np.clip(1.0 - (g - 0.0001) / 0.0011, 0, 1) * on_lid)
    col = mix(col, SUNK * 0.8, 0.5 * np.clip(1.0 - (P["fold"] + 0.0012) / 0.0012, 0, 1) * front)
    col = mix(col, HAIR, _brow(q[:, 0], z) * 0.75 * front)
    lip = smoothstep(0.0012, -0.0002, P["lip"])
    col = mix(col, LIP * (0.85 + 0.3 * fbm(p * 400.0))[:, None], lip)
    crack = smoothstep(0.62, 0.72, noise3(np.stack([P["mouth_s"] * 150.0, z * 60.0, np.zeros(len(z))], axis=1)))
    col = mix(col, LIP * 0.45, 0.6 * crack * lip)
    maw = (P["mouth_g"] < 0.0006) & (P["rho"] < 1.0)
    col = np.where(maw[:, None], MAW, col)
    col = mix(col, V(0.20, 0.10, 0.10), np.clip(1.0 - (P["nostril"] + 0.0005) / 0.0014, 0, 1) * 0.9)
    rough = 0.52 - 0.18 * lip - 0.10 * socket
    rough = np.where(maw, 0.30, rough)
    hair = P["hair"] < P["flesh"] + 0.0005
    strand = 0.75 + 0.9 * (_strands(p) / 0.0040 + 0.5).clip(0, 1) * fbm(p * 90.0)
    col = np.where(hair[:, None], HAIR * strand[:, None], col)
    rough = np.where(hair, 0.44, rough)
    return col, rough, np.zeros(len(p)), 1.0 - (hair | maw)


# ---------------------------------------------------------------- teeth and eyeballs

TEETH = 26                                     # per row: a third more than a mouth holds
IVORY = V(0.78, 0.745, 0.63)
STAIN = V(0.42, 0.33, 0.20)
GUM = V(0.42, 0.17, 0.20)


def teeth():
    """Both rows as separate pegs on the tooth ellipse. Returns verts, quads, normals and chart coordinates
    (u across a tooth, v from gum to biting edge); every tooth shares the one chart."""
    rng = np.random.default_rng(11)
    us = np.array([-1.0, -0.55, 0.0, 0.55, 1.0])
    vs = np.array([0.0, 0.5, 0.86, 1.0, 1.15])
    th_t = TH_M - 0.07
    step = 2.0 * th_t / TEETH
    verts, quads, normals, chart = [], [], [], []
    for row in (1.0, -1.0):
        for k in range(TEETH):
            th0 = -th_t + (k + 0.5) * step + rng.uniform(-0.04, 0.04) * step
            half = 0.46 * step * rng.uniform(0.92, 1.04)
            s = np.abs(th0) / TH_M
            zm = MZ0 + RISE * s ** 2.2
            hh = MH * (1.0 - s * s) ** 0.36
            root = zm + row * (hh + 0.0030)
            edge = zm + row * (0.0003 + rng.uniform(0.0, 0.0007))
            lean = rng.uniform(-0.05, 0.05)
            push = rng.uniform(-0.010, 0.010)
            U, Vv = np.meshgrid(us, vs, indexing="ij")
            vv = np.minimum(Vv, 1.0)
            th = th0 + U * half * (0.90 + 0.10 * vv) + lean * half * vv
            rho = 0.965 + push + 0.020 * (1.0 - U ** 4) * (0.5 + 0.5 * np.sin(np.pi * np.minimum(vv, 0.9))) \
                - 0.034 * (np.abs(U) == 1.0) - 0.014 * (Vv == 1.0) - 0.050 * (Vv > 1.0)
            zz = root + (edge + row * 0.0007 * U * U - root) * vv
            P = np.stack([MA * rho * np.sin(th), MYC + MB * rho * np.cos(th), zz], axis=-1)
            du = np.gradient(P, axis=0)
            dv = np.gradient(P, axis=1)
            n = S.normalize(np.cross(du, dv) * -row)
            base = len(verts) * 25
            verts.append(P.reshape(-1, 3))
            normals.append(n.reshape(-1, 3))
            chart.append(np.stack([(U + 1.0) / 2.0, Vv / 1.15], axis=-1).reshape(-1, 2))
            for i in range(4):
                for j in range(4):
                    a, b, c, e = base + i * 5 + j, base + (i + 1) * 5 + j, base + (i + 1) * 5 + j + 1, base + i * 5 + j + 1
                    quads.append((a, b, c, e) if row < 0 else (a, e, c, b))
    return np.concatenate(verts), np.array(quads), np.concatenate(normals), np.concatenate(chart)


def teeth_paint(c):
    u, v = c[:, 0], c[:, 1] * 1.15
    col = np.tile(IVORY, (len(c), 1))
    col = mix(col, STAIN, 0.55 * smoothstep(0.62, 1.0, np.abs(2.0 * u - 1.0)) + 0.35 * smoothstep(0.55, 0.0, v))
    col = mix(col, GUM, smoothstep(0.24, 0.16, v))
    col = mix(col, V(0.62, 0.60, 0.55), 0.5 * smoothstep(0.88, 1.0, v))
    return col, np.full(len(c), 0.24), np.zeros(len(c))


def eyeball(rings=9, segs=20):
    """The front of one eyeball about the origin, looking along +y. Returns verts, quads, normals, chart."""
    verts, quads = [(0.0, 1.0, 0.0)], []
    for i in range(1, rings + 1):
        a = np.radians(105.0) * i / rings
        for k in range(segs):
            b = 2 * np.pi * k / segs
            verts.append((np.sin(a) * np.cos(b), np.cos(a), np.sin(a) * np.sin(b)))
    for k in range(segs):
        k1 = (k + 1) % segs
        quads.append((0, 1 + k1, 1 + k, 1 + k))
        for i in range(rings - 1):
            a, b = 1 + i * segs, 1 + (i + 1) * segs
            quads.append((a + k, a + k1, b + k1, b + k))
    n = np.array(verts)
    return n * EYE_R, quads, n, n[:, [0, 2]] * 0.5 + 0.5


def eye_paint(c):
    """Black all through. Painted as a dark metal so that the eyes mirror almost nothing of the sky."""
    return np.tile(V(0.030, 0.030, 0.034), (len(c), 1)), np.full(len(c), 0.12), np.ones(len(c))

"""The grinner's head: a ten-year-old's face with black eyes and a grin that runs past them.

Head frame as the knight's: origin between the eyes at the centre of the skull, +y out of the face,
+z up, metres; the sculpt is symmetric in x. `field` is the form the game mesh is fitted to,
`detail` adds hair strands and creases for the normal map, `paint` colours surface points.
The eyes and the mouth are openings: slots cut back to a floor that comes up to the skin at each corner,
where the edges close to a slit. `wrap` meshes the head with edge loops round the openings and along the
cut of the hair. The teeth and eyeballs are separate small meshes made by `teeth` and `eyeball`.
"""
import numpy as np
from sculpt import sdf as S, mesher
from sculpt.sdf import V
from sculpt.mesher import Rail
from . import body
from sculpt.num import smoothstep, bump, noise3, fbm, mix

H0 = V(0, -0.108, 1.130)                       # head frame origin in the figure's rest pose


def to_head(p):
    return (p - H0) * V(-1, -1, 1)


def from_head(p):
    return H0 + np.asarray(p) * V(-1, -1, 1)


GAP = 0.0010                                   # the slit an opening closes to at its corners
EDGE, FOOT, WIDER = 0.00012, 0.0008, 0.0015    # an opening's loops: outside its edge, down its wall, clear of both

EYE = V(0.0310, 0.0530, 0.0000)                # eyeball centre (mirrored)
EYE_R = 0.0142
LID_T = 0.0015
AP_W, AP_UP, AP_LO, AP_TILT = 1.04, 0.60, 0.46, 0.02       # held wide open: the eyes do not smile
EYE_IN, EYE_OUT = EYE_R - 0.0012, EYE_R + 0.0040           # the floor behind the lids, and where it surfaces

# the mouth lies on an ellipse seen from above (the front of the teeth), measured by the angle th round it
MA, MB, MYC = 0.0470, 0.0500, 0.0280
TH_M = 1.318                                   # the corners: wider than the eyes
MZ0, RISE, MH, POINT = -0.0560, 0.0200, 0.0080, 0.45       # centre height, lift at the corners, half-opening, taper
RHO_LIP, RHO_IN, RHO_OUT = 1.050, 0.80, 1.12   # lips, back of the mouth and where it surfaces, on the tooth ellipse
ARC = 0.05                                     # metres per unit of rho or radian of th, near enough

NECK_A, NECK_B = to_head(body.NECK_A), to_head(body.NECK_B)
EAR = V(0.0730, -0.0170, -0.0080)
EAR_R = S.euler(x=12.0, z=24.0)
HAIR_C, HAIR_R = V(0, -0.015, 0.032), V(0.0820, 0.1000, 0.0930)
WHORL = S.normalize(V(0.10, -0.42, 0.90))      # the crown the hair falls from
HAIRLINE_AZ = np.radians([0, 35, 62, 85, 100, 112, 130, 150, 180])
HAIRLINE_Z = np.array([0.0390, 0.0380, 0.0330, 0.0250, 0.0225, 0.0130, -0.0170, -0.0400, -0.0480])
FRINGE = 0.0035                                # the roll of the hair's cut edge


def _eye(q):
    """An eye in the mirrored frame, measured on the eyeball: height above the opening's centre line, its
    half-height, s (1 at a corner) and the distance from the eye's centre."""
    d = q - EYE
    r = np.maximum(S.length(d), 1e-9)
    s = np.arctan2(d[:, 0], d[:, 1]) / AP_W
    c = np.clip(s, -1.0, 1.0)
    up = AP_UP * (1.0 - c * c) ** 0.62 * (1.0 - 0.10 * c) + AP_TILT * c
    lo = -AP_LO * (1.0 - c * c) ** 0.70 * (1.0 + 0.12 * c) + AP_TILT * c
    ph = np.arcsin(np.clip(d[:, 2] / r, -1, 1))
    return (ph - 0.5 * (up + lo)) * EYE_R, 0.5 * (up - lo) * EYE_R + 0.5 * GAP, s, r


def _grin(s):
    """Height of the mouth's centre line and its half-height at s: 0 in the middle, 1 at a corner."""
    s = np.clip(np.abs(s), 0.0, 1.0)
    return MZ0 + RISE * s ** 2.2, MH * (1.0 - s * s) ** POINT + 0.5 * GAP


def _mouth(q):
    """The mouth in the mirrored frame: height above its centre line, its half-height, s and the radius on
    the tooth ellipse."""
    ex, ey = q[:, 0] / MA, (q[:, 1] - MYC) / MB
    s = np.arctan2(ex, ey) / TH_M
    zm, hh = _grin(s)
    return q[:, 2] - zm, hh, s, np.hypot(ex, ey)


def _past(off, hh, along):
    """Distance outside an opening: `off` above its centre line, `along` metres past its corner."""
    edge = np.abs(off) - hh
    return np.where(along > 0, np.hypot(along, np.maximum(edge + 0.5 * GAP, 0.0)) - 0.5 * GAP, edge)


def _loops(hh):
    """Heights of an opening's four edge loops above its centre line, lowest first: one outside each edge
    and one at the foot of each wall."""
    foot = hh - np.minimum(FOOT, 0.6 * hh)
    return -(hh + EDGE), -foot, foot, hh + EDGE


def _hairline(q):
    """Height of the hair's cut edge, and the azimuth round the head."""
    az = np.arctan2(q[:, 0], q[:, 1] - HAIR_C[1])
    return np.interp(az, HAIRLINE_AZ, HAIRLINE_Z), az


def _wisps(az):
    """How far the uneven locks of the fringe hang below the cut edge."""
    lock = noise3(np.stack([az * 7.0, np.zeros(len(az)), np.zeros(len(az))], axis=1))
    fine = noise3(np.stack([az * 23.0, np.ones(len(az)), np.zeros(len(az))], axis=1))
    return (0.0060 * lock + 0.0030 * fine) * smoothstep(2.6, 1.2, az)


HELIX = body.curve([V(0.0026, 0.0085, 0.0040), V(0.0036, 0.0102, 0.0120), V(0.0036, 0.0070, 0.0205),
                    V(0.0036, 0.0000, 0.0245), V(0.0036, -0.0085, 0.0215), V(0.0036, -0.0138, 0.0130),
                    V(0.0036, -0.0152, 0.0020), V(0.0034, -0.0138, -0.0085), V(0.0020, -0.0095, -0.0160)],
                   [0.0015, 0.0022, 0.0024, 0.0025, 0.0025, 0.0024, 0.0022, 0.0018, 0.0010], 2)
ANTIHELIX = body.curve([V(0.0030, -0.0055, -0.0120), V(0.0040, -0.0088, -0.0040), V(0.0040, -0.0082, 0.0055),
                        V(0.0034, -0.0040, 0.0140), V(0.0026, 0.0020, 0.0175)],
                       [0.0016, 0.0022, 0.0022, 0.0017, 0.0010], 2)
CRUS = body.curve([V(0.0040, -0.0082, 0.0055), V(0.0034, -0.0020, 0.0085), V(0.0024, 0.0045, 0.0090)],
                  [0.0019, 0.0015, 0.0009], 2)


def _ear(e, fine):
    """An ear in its own frame, x out of the side of the head, y forward, z up: what it adds to the head and
    what it hollows out of it. Solid behind, so that no part hides another from the middle of the head.
    fine adds the folds inside the rim."""
    d = S.smin(S.ellipsoid(e, V(0, -0.0015, 0.0050), V(0.0032, 0.0148, 0.0198)),
               S.ellipsoid(e, V(0.0005, 0.0015, -0.0175), V(0.0036, 0.0075, 0.0085)), 0.008)
    d = S.smin(d, S.tube(e, *HELIX), 0.0022)
    d = S.smin(d, S.ellipsoid(e, V(-0.0100, -0.0005, -0.0020), V(0.0150, 0.0135, 0.0225)), 0.0030)
    hollow = S.ellipsoid(e, V(0.0040, 0.0010, -0.0030), V(0.0085, 0.0062, 0.0085))                    # concha
    if fine:
        d = S.smin(d, np.minimum(S.tube(e, *ANTIHELIX), S.tube(e, *CRUS)), 0.0020)
        d = S.smin(d, S.ellipsoid(e, V(0.0030, 0.0100, -0.0040), V(0.0024, 0.0028, 0.0048)), 0.0020)  # tragus
        d = S.smin(d, S.sphere(e, V(0.0034, -0.0025, -0.0135), 0.0028), 0.0024)                      # antitragus
        hollow = S.smin(hollow, S.ellipsoid(e, V(-0.0020, 0.0050, -0.0030), V(0.0050, 0.0028, 0.0034)), 0.0015)
    return d, hollow


def _parts(p, fine=True, wider=0.0):
    """The head's forms at p. fine adds what only the normal map can hold; `wider` opens the eyes and the
    mouth by that much more."""
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
    off, hh, s, rho = _mouth(q)
    edge = np.abs(off) - hh
    low = off + 0.003
    band = np.maximum((rho - 1.040) * ARC + 0.0045 * (low / np.where(low > 0, 0.015, 0.022)) ** 2,
                      ((s - 1.0) * TH_M - 0.10) * ARC)
    band = np.maximum(band, (0.80 - rho) * ARC)                 # a rind over the teeth, not a solid
    d = S.smin(d, band, 0.012)
    apple = S.ellipsoid(q, V(0.0440, 0.0440, -0.0210), V(0.0150, 0.0150, 0.0130))  # the cheek the corner pushes up
    d = S.smin(d, apple, 0.014)
    lip_r = np.where(off > 0, 0.0025, 0.0036) * (0.55 + 0.45 * np.clip(1.0 - s * s, 0.0, 1.0))
    lip = np.hypot(edge - 0.0016, (rho - RHO_LIP) * ARC) - lip_r + 0.008 * smoothstep(0.97, 1.09, s)
    d = S.smin(d, lip, 0.0035)
    floor = RHO_IN + (RHO_OUT - RHO_IN) * smoothstep(0.94, 1.0, s)
    slot = np.maximum(np.maximum(edge - wider, (floor - rho) * ARC), (s - 1.0) * TH_M * ARC)
    d = S.smax(d, -slot, 0.0008)
    dimple = S.tube(q, [V(0.0500, 0.0400, -0.0240), V(0.0545, 0.0345, -0.0350), V(0.0520, 0.0360, -0.0480)],
                    [0.0016, 0.0026, 0.0014])
    d = S.ssub(d, dimple, 0.0045)
    d = S.ssub(d, S.tube(p, [V(0, 0.0835, -0.0400), V(0, 0.0850, -0.0455)], [0.0018, 0.0022]), 0.0040)
    d = S.ssub(d, S.ellipsoid(p, V(0, 0.0830, -0.0770), V(0.0130, 0.0050, 0.0030)), 0.0060)
    P["lip"], P["maw"], P["mouth_s"] = lip, (edge < 0.0006) & (rho < 1.0) & (s < 1.0), s
    # ---- eyelids: a shell over the eyeball, open across the aperture
    off, hh, s, r_eye = _eye(q)
    ga = _past(off, hh, (np.abs(s) - 1.0) * AP_W * EYE_R)
    fade = np.clip((ga - 0.0025) / np.where(off > 0, 0.0100, 0.0050), 0.0, 1.0)
    lid = EYE_R + LID_T
    d = S.smin(d, r_eye - (lid - 0.0065 * fade * fade * (3.0 - 2.0 * fade)), 0.0080)
    fold_r = 0.0020 * np.clip(1.0 - (np.abs(s) / 0.95) ** 4, 0.0, 1.0)

    def furrow(past, at, proud):
        """A crease that follows a lid's edge, `at` radians past it."""
        return np.where(fold_r > 1e-5, np.hypot(r_eye - (lid + proud), (past / EYE_R - at) * lid), 1.0)
    fold = furrow(off - hh, 0.24, 0.0016) - fold_r
    d = S.ssub(d, fold, 0.0020)
    bag = furrow(-off - hh, 0.30, 0.0012) - 0.8 * fold_r
    d = S.ssub(d, bag, 0.0030)
    floor = EYE_IN + (EYE_OUT - EYE_IN) * smoothstep(0.88, 1.0, np.abs(s))
    slot = np.maximum(np.maximum(ga - wider, r_eye - (EYE_R + 0.0045)), floor - r_eye)
    d = S.smax(d, -slot, 0.0005)
    P["lid_g"], P["r_eye"], P["fold"] = ga, r_eye, np.minimum(fold, bag)
    # ---- ears that stand off the head
    near = S.length(q - EAR) < 0.042
    ear, hollow = np.ones(len(p)), np.ones(len(p))
    ear[near], hollow[near] = _ear((q[near] - EAR) @ EAR_R, fine)
    d = S.ssub(S.smin(d, ear, 0.0050), hollow, 0.0025)
    # ---- neck
    d = S.smin(d, S.capsule(p, NECK_A, NECK_B, body.NECK_R), 0.028)
    cord = S.tube(q, [V(0.0420, -0.0260, -0.0420), V(0.0260, -0.0180, -0.1000), V(0.0100, -0.0260, -0.1500)], 0.0075)
    d = S.smin(d, cord, 0.014)
    d = S.smin(d, S.ellipsoid(p, V(0, 0.0240, -0.0780), V(0.0240, 0.0320, 0.0120)), 0.022)       # soft under the chin
    # ---- hair: a heavy bowl cut, the fringe low over the brows
    line, az = _hairline(q)
    hair = S.smax(S.ellipsoid(p, HAIR_C, HAIR_R), line - z, FRINGE) - _strands(p, fine)
    if fine:                                                    # thin locks lie on the skin below the cut
        hair = np.minimum(hair, S.smax(d - 0.0011, line - _wisps(az) - z, 0.0008))
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


def face(p):
    """1 over the face, 0 elsewhere: the part of the head that deserves the most texels."""
    return smoothstep(0.0, 0.045, p[:, 1]) * smoothstep(0.050, 0.030, p[:, 2]) * smoothstep(-0.105, -0.090, p[:, 2])


# ---------------------------------------------------------------- the game mesh

RES = (32, 30, 50)                             # lattice: across the face, front to back, up
MOUTH_RING, EYE_RING, HAIR_RING = 8, 23, 32    # the lowest of each feature's rings
LEAN = 0.42                                    # the top of the lattice leans back as the cut of the hair does
CORNER = V(MA * np.sin(TH_M), MYC + MB * np.cos(TH_M), MZ0 + RISE)


def density(p):
    """Mesh density weight: finer quads over the face, finest at the eyes, the nose, the ears and the
    corners of the mouth."""
    q = S.mirror_x(p)
    eye = bump(S.length(q - EYE), 0.0, 0.022)
    nose = bump(np.hypot(p[:, 0], p[:, 2] + 0.032), 0.0, 0.014) * (p[:, 1] > 0)
    ear = bump(S.length(q - EAR), 0.0, 0.024)
    corner = bump(S.length(q - CORNER), 0.0, 0.010)
    return 1.0 + 1.2 * face(p) + 1.8 * eye + 2.0 * nose + 4.0 * ear + 3.0 * corner


def _open(p):
    """The head with its openings cut wider: the floor on which the feet of their walls stand."""
    return _parts(p, False, WIDER)["d"]


def _opening(measure, reach):
    """The four loops of an opening as rail arguments, lowest first. measure: mirrored points -> height
    above the centre line, half-height, s and one more; reach: the last two -> how firmly the edges are
    held. The feet are held only as far as the corners."""
    def loop(k):
        foot = k in (1, 2)

        def g(p):
            off, hh, *_ = measure(S.mirror_x(p))
            return np.sign(k - 1.5) * (off - _loops(hh)[k])

        def hold(p):
            off, hh, s, far = measure(S.mirror_x(p))
            return reach(s, far) * (smoothstep(1.0, 0.96, np.abs(s)) if foot else 1.0)
        return dict(g=g, hold=hold, floor=_open if foot else None)
    return [loop(k) for k in range(4)]


def rails(sub=1):
    """The edge loops of the game mesh: round the mouth, round the eyes, and three along the cut of the hair."""
    def cut(up, at):
        return dict(g=lambda p: up * (p[:, 2] - _hairline(S.mirror_x(p))[0]) - at)
    mouth = _opening(_mouth, lambda s, rho: smoothstep(1.16, 1.03, s))
    eyes = _opening(_eye, lambda s, r: smoothstep(1.40, 1.06, np.abs(s)) * smoothstep(EYE_R + 0.012, EYE_R + 0.005, r))
    hair = [cut(-1.0, FRINGE), cut(1.0, 0.0008), cut(1.0, 0.0045)]
    return [Rail((first + k) * sub, **loop) for first, loops in ((MOUTH_RING, mouth), (EYE_RING, eyes), (HAIR_RING, hair))
            for k, loop in enumerate(loops)]


def _lean(u):
    """Tilt the upper half of the lattice's starting sphere backward."""
    return u + np.outer(LEAN * u[:, 1] * smoothstep(0.0, 0.5, u[:, 2]), V(0, 0, 1))


def wrap(sub=1, relax=40):
    """The head's quad mesh: verts, quads, normals and lattice points."""
    dims = tuple(r * sub for r in RES)
    v, q, n = mesher.wrap(field, V(0, -0.012, 0.050), V(0, -0.024, -0.050), (0.095, 0.125, 0.150), dims,
                          relax=relax, density=density, rails=rails(sub), warp=_lean)
    unit = mesher.cube_lattice(*dims)[0]
    return v, q, n, np.rint((unit + 1.0) / 2.0 * np.array(dims)).astype(np.int64)


def seam(a, b, n=1):
    """One island, opened down the back of the skull."""
    def on(c):
        i, j, k = c[:, 0], c[:, 1], c[:, 2]
        return (i == RES[0] * n // 2) & ((j == 0) | ((j <= RES[1] * n // 2) & ((k == 0) | (k == RES[2] * n))))
    return on(a) & on(b)


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
    by_eye = P["r_eye"] < EYE_R + 0.0045
    col = mix(col, RIM, np.clip(1.0 - (g - 0.0001) / 0.0011, 0, 1) * by_eye)
    col = mix(col, SUNK * 0.8, 0.5 * np.clip(1.0 - (P["fold"] + 0.0012) / 0.0012, 0, 1) * front)
    col = mix(col, HAIR, _brow(q[:, 0], z) * 0.75 * front)
    lip = smoothstep(0.0012, -0.0002, P["lip"])
    col = mix(col, LIP * (0.85 + 0.3 * fbm(p * 400.0))[:, None], lip)
    crack = smoothstep(0.62, 0.72, noise3(np.stack([P["mouth_s"] * 150.0, z * 60.0, np.zeros(len(z))], axis=1)))
    col = mix(col, LIP * 0.45, 0.6 * crack * lip)
    maw = P["maw"]
    col = np.where(maw[:, None], MAW, col)
    col = mix(col, V(0.20, 0.10, 0.10), np.clip(1.0 - (P["nostril"] + 0.0005) / 0.0014, 0, 1) * 0.9)
    rough = 0.52 - 0.18 * lip - 0.10 * socket
    rough = np.where(maw | (by_eye & (g < 0.0001)), 0.30, rough)
    hair = P["hair"] < P["flesh"] + 0.0005
    strand = 0.75 + 0.9 * (_strands(p) / 0.0040 + 0.5).clip(0, 1) * fbm(p * 90.0)
    col = np.where(hair[:, None], HAIR * strand[:, None], col)
    rough = np.where(hair, 0.44, rough)
    return col, rough, np.zeros(len(p)), 1.0 - (hair | maw)


# ---------------------------------------------------------------- teeth and eyeballs

TEETH = 26                                     # per row: a third more than a mouth holds
TOOTH = (0.0048, 0.0125)                       # the room each tooth has on the chart: across, and gum to biting edge
CHART = (TEETH * TOOTH[0], 2 * TOOTH[1])       # the chart's size: a cell per tooth, a row of cells per row of teeth
INSET = 0.05                                   # of a cell, left clear round its tooth
IVORY = V(0.78, 0.745, 0.63)
AGED = V(0.70, 0.60, 0.38)
STAIN = V(0.42, 0.33, 0.20)
ROT = V(0.24, 0.20, 0.17)
GUM = V(0.42, 0.17, 0.20)


def teeth():
    """Both rows as separate pegs on the tooth ellipse. Returns verts, quads, normals and chart coordinates:
    within a tooth's own cell of the chart, u across it and v from gum to biting edge."""
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
            zm, hh = _grin(th0 / TH_M)
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
            within = np.stack([(U + 1.0) / 2.0, Vv / 1.15], axis=-1).reshape(-1, 2)
            chart.append((np.array((k, row < 0)) + INSET + (1.0 - 2.0 * INSET) * within) / (TEETH, 2))
            for i in range(4):
                for j in range(4):
                    a, b, c, e = base + i * 5 + j, base + (i + 1) * 5 + j, base + (i + 1) * 5 + j + 1, base + i * 5 + j + 1
                    quads.append((a, b, c, e) if row < 0 else (a, e, c, b))
    return np.concatenate(verts), np.array(quads), np.concatenate(normals), np.concatenate(chart)


def teeth_paint(c):
    """Every tooth wears differently: its cell of the chart draws its own yellowing, stains, gum line, chip
    and crack."""
    cell = c * (TEETH, 2)
    tooth = np.floor(cell)
    u, v = ((cell - tooth - INSET) / (1.0 - 2.0 * INSET)).T
    v = v * 1.15
    across = np.abs(2.0 * u - 1.0)
    number = tooth[:, 0] + TEETH * tooth[:, 1]

    def draw(k):
        """A number in 0..1 for each tooth, different for every k."""
        return noise3(np.stack([number, np.full(len(c), float(k)), np.zeros(len(c))], axis=1))
    grain = noise3(np.stack([u * 5.0, v * 7.0, number * 3.7], axis=1))
    col = mix(np.tile(IVORY, (len(c), 1)), AGED, 0.75 * draw(1) * (0.6 + 0.8 * grain))
    stain = (0.25 + 0.60 * draw(2)) * smoothstep(0.62, 1.0, across) + (0.15 + 0.45 * draw(3)) * smoothstep(0.55, 0.0, v)
    stain = stain + 0.5 * smoothstep(0.55, 0.75, noise3(np.stack([u * 9.0, v * 4.0, number * 1.3 + 40.0], axis=1))) * draw(4)
    col = mix(col, STAIN, stain)
    col = mix(col, ROT, 0.75 * smoothstep(0.86, 0.90, draw(5)) * (0.5 + 0.5 * grain))
    crack = smoothstep(0.016, 0.004, np.abs(u - (0.25 + 0.5 * draw(6)) - 0.05 * np.sin(9.0 * v + 6.0 * draw(7))))
    col = mix(col, ROT, 0.7 * crack * smoothstep(0.60, 0.70, draw(8)) * smoothstep(0.25 + 0.4 * draw(9), 0.55 + 0.4 * draw(9), v))
    chip = 0.16 * draw(10) * smoothstep(0.50, 0.60, draw(11)) * np.clip(1.0 - np.abs(u - (0.2 + 0.6 * draw(12))) / 0.22, 0, 1)
    worn = smoothstep(1.0 - chip - 0.02, 1.0 - chip + 0.02, v) * (chip > 0.01)
    col = mix(col, V(0.62, 0.60, 0.55), 0.5 * smoothstep(0.88, 1.0, v))
    col = mix(col, STAIN * 0.8, 0.85 * worn)
    line = 0.13 + 0.12 * draw(13) + 0.10 * across ** 2
    tartar = smoothstep(line + 0.14, line + 0.02, v) * (0.3 + 0.7 * draw(14))
    col = mix(col, STAIN * V(1.1, 1.0, 0.7), 0.6 * tartar)
    gum = smoothstep(line + 0.03, line - 0.03, v)
    col = mix(col, GUM * (0.8 + 0.4 * draw(15)), gum)
    return col, 0.24 + 0.30 * np.clip(stain + tartar, 0, 1) * (1.0 - gum) + 0.10 * gum + 0.3 * worn, np.zeros(len(c))


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

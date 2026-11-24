"""Her head: a soft oval face with almond eyes, a short nose and a faint smile, on a slender neck.

Head frame as the knight's: origin between the eyes at the centre of the skull, +y out of the face, +z up,
metres; the sculpt is symmetric in x. `field` is the carving, `paint` its lacquer (lips, brows, lashes,
blush) as a tint over the wood, and `wrap` meshes it with edge loops round the eyes and along the lips.
The lips part on a slot that runs back to a pocket, so a jaw can open them.
"""
import numpy as np
from sculpt import sdf as S, mesher, gen
from sculpt.sdf import V
from sculpt.mesher import Rail
from sculpt.num import smoothstep, bump, noise3, mix
from . import body

HEAD = body.HEAD

EYE = V(0.0278, 0.0515, 0.0000)                # eyeball centre (mirrored)
EYE_R = 0.0170
LID_T = 0.0016
LID_REACH = 0.0060                             # the opening is cut through whatever stands this far before the eyeball
AP_OUT, AP_IN = 1.04, 0.66                     # the opening's reach toward the temple and toward the nose (rad)
AP_UP, AP_LO, AP_TILT = 0.345, 0.320, 0.095    # large almond eyes, the outer corners lifted
IRIS = 0.40                                    # iris radius on the eyeball (rad): the lids rest on its top and bottom
EYE_TURN = 0.5 * (AP_OUT - AP_IN)              # each eyeball is turned out this far (rad), to look from the middle of its opening

AXIS_Y = -0.012                                # the meshing axis stands here, and the mouth is measured round it
AXIS = (V(0, AXIS_Y, 0.045), V(0, AXIS_Y, -0.105))
TH_M = 0.292                                   # the corners of the mouth, as an angle round the axis
MZ, RISE, BOW = -0.0612, 0.0013, 0.0005        # height of the parting, lift at the corners, dip under the cupid's bow
MH = 0.00035                                   # half the parting's height at the centre
POCKET = (0.0885, 0.0812)                      # distance of the pocket's back from the axis: centre, corners
NECK_CUT = -0.0012                             # the head ends this far along the neck from the choker

PAINT_X, PAINT_Z0, PAINT_Z1 = 0.064, -0.100, 0.044          # the front-projected paint texture covers this


def _aperture(q):
    """Angular eye opening in the mirrored frame: g < 0 inside (metres on the eyeball), the place across it
    (-1 inner corner .. 1 outer corner), the height on the eyeball and the heights of the two lids there."""
    d = q - EYE
    r = np.maximum(S.length(d), 1e-9)
    th = np.arctan2(d[:, 0], d[:, 1])
    ph = np.arcsin(np.clip(d[:, 2] / r, -1, 1))
    reach = np.where(th > 0, AP_OUT, AP_IN)
    s = th / reach
    s2 = np.clip(1.0 - s * s, 0.0, 1.0)
    up = AP_UP * s2 ** 0.52 * (1.0 - 0.20 * s) + AP_TILT * s
    lo = -AP_LO * s2 ** 0.58 * (1.0 + 0.28 * s) + AP_TILT * s
    g = np.maximum(ph - up, lo - ph)
    g = np.where(np.abs(s) < 1.0, g, np.hypot((np.abs(s) - 1.0) * reach, ph - AP_TILT * np.sign(s)) + 0.004)
    return g * EYE_R, s, ph, up, lo


def _round(q):
    """Angle round the meshing axis from straight ahead, and distance from it, in the mirrored frame."""
    return np.arctan2(q[:, 0], q[:, 1] - AXIS_Y), np.hypot(q[:, 0], q[:, 1] - AXIS_Y)


def _lip_line(th):
    """Height of the parting at an angle round the axis; past the corners it runs on level round the head."""
    s = np.minimum(th / TH_M, 1.0)
    return MZ + RISE * s ** 3 - BOW * np.exp(-(s / 0.30) ** 2) + 0.010 * smoothstep(TH_M, 2.0, th)


def _mouth(q):
    """The parting in the mirrored frame: g < 0 inside it, with its place along the mouth (0 centre .. 1
    corner), its half height there and the distance from the axis."""
    th, r = _round(q)
    s = th / TH_M
    off = q[:, 2] - _lip_line(th)
    hh = MH * np.sqrt(np.clip(1.0 - s * s, 0.0, 1.0))
    g = np.where(s < 1.0, np.abs(off) - hh, np.hypot((th - TH_M) * r, off) + 1e-4)
    return g, s, hh, r


def skull(p):
    """The bare skull: what her hair lies on."""
    return S.smin(S.ellipsoid(p, V(0, -0.012, 0.024), V(0.0715, 0.0910, 0.0860)),
                  S.ellipsoid(p, V(0, 0.016, -0.036), V(0.0500, 0.0625, 0.0660)), 0.034)


def _parts(p):
    q = S.mirror_x(p)
    P = {}
    # ---- skull and the large masses of the face
    d = skull(p)
    jaw = S.tube(q, [V(0.000, 0.0650, -0.0905), V(0.0090, 0.0590, -0.0890), V(0.0205, 0.0350, -0.0800),
                     V(0.0305, 0.0060, -0.0650), V(0.0385, -0.0100, -0.0370), V(0.0455, -0.0150, -0.0050)],
                 [0.0104, 0.0100, 0.0098, 0.0100, 0.0116, 0.0124])
    d = S.smin(d, jaw, 0.024)
    chin = S.ellipsoid(p, V(0, 0.0695, -0.0940), V(0.0100, 0.0098, 0.0105))
    d = S.smin(d, chin, 0.014)
    muzzle = S.ellipsoid(p, V(0, 0.0490, -0.0610), V(0.0280, 0.0320, 0.0235))
    d = S.smin(d, muzzle, 0.024)
    malar = S.ellipsoid(q, V(0.0360, 0.0480, -0.0215), V(0.0210, 0.0225, 0.0230))
    d = S.smin(d, malar, 0.032)
    zyg = S.ellipsoid(q, V(0.0495, 0.0210, -0.0150), V(0.0150, 0.0260, 0.0115))
    d = S.smin(d, zyg, 0.028)
    brow = S.ellipsoid(q, V(0.0280, 0.0590, 0.0225), V(0.0250, 0.0110, 0.0090), S.euler(z=-14, y=8))
    d = S.smin(d, brow, 0.020)
    d = S.smin(d, S.ellipsoid(p, V(0, 0.0590, 0.0240), V(0.0170, 0.0110, 0.0110)), 0.020)        # smooth between the brows
    # ---- eye sockets: shallow, deepest beside the bridge
    sock = S.ellipsoid(q, V(0.0245, 0.0875, 0.0030), V(0.0205, 0.0205, 0.0118), S.euler(y=-10))
    d = S.ssub(d, sock, 0.016)
    d = S.ssub(d, S.ellipsoid(q, V(0.0440, 0.0790, 0.0010), V(0.0120, 0.0170, 0.0100)), 0.012)   # back to the temple
    d = S.ssub(d, S.ellipsoid(q, V(0.0128, 0.0800, -0.0035), V(0.0080, 0.0150, 0.0100)), 0.006)  # in beside the nose
    nasion = S.ellipsoid(p, V(0, 0.0885, 0.0030), V(0.0190, 0.0110, 0.0095))
    d = S.ssub(d, nasion, 0.011)
    # ---- nose: short, a slim scooped bridge and a small tip turned a little up
    bridge = S.tube(p, [V(0, 0.0680, 0.0070), V(0, 0.0752, -0.0095), V(0, 0.0832, -0.0215), V(0, 0.0890, -0.0290)],
                    [0.0056, 0.0036, 0.0038, 0.0046])
    tip = S.ellipsoid(p, V(0, 0.0912, -0.0318), V(0.0060, 0.0060, 0.0052))
    ala = S.ellipsoid(q, V(0.0090, 0.0806, -0.0352), V(0.0038, 0.0060, 0.0042), S.euler(z=-18))
    d = S.smin(d, bridge, 0.0105)
    col = S.tube(p, [V(0, 0.0915, -0.0352), V(0, 0.0825, -0.0388)], [0.0029, 0.0031])
    lobe = S.ellipsoid(p, V(0, 0.0835, -0.0345), V(0.0104, 0.0080, 0.0056))
    nose = S.smin(S.smin(S.smin(lobe, tip, 0.0065), ala, 0.0055), col, 0.0045)
    nose = S.smin(nose, bridge, 0.0065)
    d = S.smin(d, nose, 0.0055)
    nostril = S.ellipsoid(q, V(0.0050, 0.0856, -0.0398), V(0.0021, 0.0036, 0.0014), S.euler(z=-25, x=22))
    P["nostril"] = nostril
    d = S.ssub(d, nostril, 0.0020)
    # ---- lips: a cupid's bow over a fuller lower lip, the corners tucked up into the cheeks
    up_l = S.ellipsoid(q, V(0.0078, 0.0796, -0.0570), V(0.0126, 0.0056, 0.0056), S.euler(z=-27, y=9))
    up_c = S.ellipsoid(p, V(0, 0.0820, -0.0588), V(0.0048, 0.0046, 0.0040))
    upper = S.smin(up_l, up_c, 0.003)
    lower = S.ellipsoid(q, V(0.0060, 0.0778, -0.0678), V(0.0116, 0.0066, 0.0070), S.euler(z=-25))
    lower = S.smin(lower, S.ellipsoid(p, V(0, 0.0786, -0.0682), V(0.0084, 0.0066, 0.0066)), 0.004)
    P["upper_lip"], P["lower_lip"] = upper, lower
    d = S.smin(d, S.smin(upper, lower, 0.0012), 0.0022)
    phil = S.tube(p, [V(0, 0.0868, -0.0440), V(0, 0.0876, -0.0520)], [0.0018, 0.0022])
    d = S.ssub(d, phil, 0.0038)
    crease = S.ellipsoid(p, V(0, 0.0850, -0.0775), V(0.0120, 0.0070, 0.0038))
    d = S.ssub(d, crease, 0.0060)
    g, s, hh, r = _mouth(q)
    P["mouth_g"] = g
    back = POCKET[0] + (POCKET[1] - POCKET[0]) * np.minimum(s, 1.0) ** 2
    d = S.smax(d, -np.maximum(g, back - r), 0.0004)
    # ---- eyelids: a shell over the eyeball, open across the aperture
    ga, across, ph, up, lo = _aperture(q)
    r_eye = S.length(q - EYE)
    upper_side = ph > 0.5 * (up + lo)
    fade = np.clip((ga - 0.0025) / np.where(upper_side, 0.0100, 0.0050), 0.0, 1.0)
    shell = r_eye - (EYE_R + LID_T - 0.0065 * fade * fade * (3.0 - 2.0 * fade))
    d = S.smin(d, shell, 0.0080)
    fold_r = 0.0020 * np.clip(1.0 - (np.abs(across) / 0.95) ** 4, 0.0, 1.0)
    fold = np.hypot(r_eye - (EYE_R + LID_T + 0.0016), (ph - (up + 0.23)) * (EYE_R + LID_T)) - fold_r
    fold = np.where(fold_r > 1e-5, fold, 1.0)                   # the lid's crease, which only the paint draws
    cut = np.maximum(np.maximum(ga, r_eye - (EYE_R + LID_REACH)), (EYE_R - 0.0012) - r_eye)
    d = S.smax(d, -cut, 0.0005)
    P["fold"], P["r_eye"] = fold, r_eye
    P["lid_g"], P["lid_ph"], P["lid_up"], P["lid_lo"], P["lid_s"] = ga, ph, up, lo, across
    # ---- soft under the chin, and on the neck the torso gives her, cut off inside the choker
    w = HEAD.w(p)
    d = S.smin(d, S.ellipsoid(p, V(0, 0.0250, -0.0850), V(0.0230, 0.0300, 0.0110)), 0.022)
    d = S.smin(d, body.torso(w), 0.022)
    P["d"] = S.smax(d, (body.CHOKER + body.NECK_DIR * NECK_CUT - w) @ body.NECK_DIR, 0.002)
    return P


def field(p):
    return _parts(p)["d"]


def density(p):
    """Mesh density weight: finer quads over the eyes, the nose and the mouth."""
    q = S.mirror_x(p)
    f = np.clip((p[:, 1] - 0.030) / 0.030, 0, 1) * np.clip((0.042 - p[:, 2]) / 0.015, 0, 1) \
        * np.clip((p[:, 2] + 0.106) / 0.015, 0, 1)
    eye = np.exp(-((q[:, 0] - EYE[0]) ** 2 + (p[:, 2] - EYE[2]) ** 2) / (2 * 0.019 ** 2))
    mouth = np.exp(-((q[:, 0] / 0.030) ** 2 + ((p[:, 2] - MZ) / 0.012) ** 2))
    nose = np.exp(-(p[:, 0] ** 2 + (p[:, 2] + 0.036) ** 2) / (2 * 0.010 ** 2))
    return 1.0 + f * (5.0 + 14.0 * eye + 12.0 * mouth + 14.0 * nose)


# ---------------------------------------------------------------- edge loops for the mesher

def lid_edge(p):
    """> 0 on the lids, < 0 in the eye opening."""
    q = S.mirror_x(p)
    return np.maximum(_aperture(q)[0], S.length(q - EYE) - (EYE_R + LID_REACH + 0.0015))


def lid_inner(p):
    """Drop points just inside the opening down the lid margin to behind the eyeball's surface."""
    sx = np.where(p[:, 0] < 0, -1.0, 1.0)
    c = EYE * np.stack([sx, np.ones(len(p)), np.ones(len(p))], axis=1)
    return c + S.normalize(p - c) * (EYE_R - 0.0011)


FEATURES = [(lid_edge, lid_inner, 5e-4)]
RES = (96, 76, 120)                            # lattice at full detail: across the face, front to back, up
LIP_RING = 0.335                               # the parting's ring, as a share of the lattice's height
LIP_STAND = 0.00012                            # how far each lip's edge loop stands back from the parting
LIP_GAP = 0.0022                               # spacing the three loops open to beyond the corners


def dims(detail):
    return tuple(2 * max(4, round(r * detail / 2)) for r in RES)


def rails(detail):
    """Three neighbouring loops: the edge of the upper lip, the back of the pocket, the edge of the lower lip."""
    def edge(side):
        def g(p):
            th, _ = _round(S.mirror_x(p))
            s = np.minimum(th / TH_M, 1.0)
            stand = MH * np.sqrt(1.0 - s * s) + LIP_STAND + LIP_GAP * smoothstep(TH_M, TH_M + 0.09, th)
            return side * (p[:, 2] - _lip_line(th)) - stand
        return g
    ring = round(LIP_RING * dims(detail)[2])
    return [Rail(ring - 1, edge(-1.0)), Rail(ring, lambda p: p[:, 2] - _lip_line(_round(S.mirror_x(p))[0])),
            Rail(ring + 1, edge(1.0))]


def wrap(detail=1.0):
    """The head's quad mesh in the head frame: verts, quads, normals and lattice points."""
    n = dims(detail)
    v, q, nrm = mesher.wrap(field, *AXIS, (0.085, 0.105, 0.150), n, relax=14, density=density, snap=FEATURES,
                            rails=rails(detail))
    unit = mesher.cube_lattice(*n)[0]
    lat = np.rint((unit + 1.0) / 2.0 * np.array(n)).astype(np.int64)
    ring = round(LIP_RING * n[2])
    mouth = (_round(S.mirror_x(v))[0] < TH_M) & (v[:, 1] > 0)
    out = S.normalize((v - V(0, AXIS_Y, 0)) * V(1, 1, 0))
    for k, turn in ((ring - 1, 0.75), (ring, 0.0), (ring + 1, -0.75)):          # the lips' edges turn into the parting,
        m = mouth & (lat[:, 2] == k)                                            # and the pocket's back faces out of it
        nrm[m] = S.normalize(out[m] + V(0, 0, turn))
    return v, q, nrm, lat


# ---------------------------------------------------------------- paint

LIP = V(0.90, 0.53, 0.51)
LIP_DEEP = V(0.72, 0.35, 0.36)
MOUTH = V(0.16, 0.07, 0.06)
BROW = V(0.50, 0.36, 0.20)
LASH = V(0.20, 0.13, 0.09)
SHADE = V(0.84, 0.66, 0.56)
BLUSH = V(1.0, 0.74, 0.70)
BROW_PTS = np.array([(0.0140, 0.0222), (0.0210, 0.0254), (0.0290, 0.0278), (0.0370, 0.0288), (0.0445, 0.0272),
                     (0.0515, 0.0230)])
BROW_W = np.array([0.0018, 0.0021, 0.0020, 0.0016, 0.0011, 0.0004])


def _brow(x, z):
    """Brow opacity in the front view: a tapered arch drawn as fine strokes."""
    best, along = np.full(len(x), 1e9), np.zeros(len(x))
    for k in range(len(BROW_PTS) - 1):
        a, b = BROW_PTS[k], BROW_PTS[k + 1]
        ab = b - a
        t = np.clip(((x - a[0]) * ab[0] + (z - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        dist = np.hypot(x - (a[0] + ab[0] * t), z - (a[1] + ab[1] * t)) - (BROW_W[k] + (BROW_W[k + 1] - BROW_W[k]) * t)
        better = dist < best
        best, along = np.where(better, dist, best), np.where(better, k + t, along)
    lean = np.radians(60 - 10 * along)
    u, v = x * np.cos(lean) + z * np.sin(lean), -x * np.sin(lean) + z * np.cos(lean)
    hairs = 0.60 + 0.40 * noise3(np.stack([v * 3800.0, u * 420.0, np.zeros(len(x))], axis=1))
    return np.clip(-best / 0.0009, 0, 1) * hairs * (0.70 + 0.30 * np.clip(along / 1.2, 0, 1))


def paint(p):
    """Lacquer tint multiplied over the wood at points on or near the surface. RGB in 0..1."""
    P = _parts(p)
    q = S.mirror_x(p)
    col = np.ones((len(p), 3))
    front = np.clip((p[:, 1] - 0.020) / 0.020, 0, 1)
    col = mix(col, BLUSH, 0.50 * bump(q[:, 0], 0.040, 0.017) * bump(q[:, 2], -0.028, 0.015) * front)
    lips = np.minimum(P["upper_lip"], P["lower_lip"])
    m = smoothstep(0.0012, 0.0001, lips)
    deep = np.exp(-np.maximum(P["mouth_g"], 0) / 0.0011) * 0.9 + 0.25 * np.clip((q[:, 0] - 0.012) / 0.012, 0, 1)
    col = mix(col, LIP * (1 - deep[:, None]) + LIP_DEEP * deep[:, None], m * 0.88)
    col = mix(col, MOUTH, smoothstep(0.00015, -0.00005, P["mouth_g"]))
    col = mix(col, V(0.50, 0.33, 0.26), np.clip(1.0 - (P["nostril"] + 0.0006) / 0.0014, 0, 1) * 0.8)
    col = mix(col, BROW, _brow(q[:, 0], q[:, 2]) * 0.85 * front)
    g = P["lid_g"]
    s = P["lid_s"]
    upper_side = P["lid_ph"] > 0.5 * (P["lid_up"] + P["lid_lo"])
    on_lid = (P["r_eye"] < EYE_R + 0.0045) & (g > -0.0006)
    col = mix(col, SHADE, 0.55 * np.exp(-np.maximum(g, 0) / 0.0034) * upper_side * on_lid * (np.abs(s) < 1.08))
    col = mix(col, SHADE, 0.45 * np.clip(1.0 - (P["fold"] + 0.0012) / 0.0010, 0, 1) * on_lid)
    lw = np.where(upper_side, 0.0011 + 0.0015 * np.clip((s + 0.3) / 1.3, 0, 1), 0.0006)
    lash = np.clip(1.0 - (g - 0.0002) / lw, 0, 1) * on_lid
    return mix(col, LASH, lash * np.where(upper_side, 1.0, 0.40 * np.clip((s + 0.2) / 0.8, 0, 1)))


# ---------------------------------------------------------------- eyeballs

PUPIL = 0.15                                   # pupil radius on the eyeball (rad)
EYE_RINGS = (0.0, 0.07, PUPIL - 0.01, PUPIL + 0.01, 0.27, IRIS - 0.02, IRIS + 0.02, 0.56, 0.76, 1.0, 1.28, 1.6, 1.95)


def eyeball(segs=32):
    """The front of one eyeball about the origin, looking along +z, with rings on the edges of pupil and iris.
    Returns verts, faces, normals and the colours Blender previews it in; the game's eye look draws its own."""
    v, faces = gen.lathe([(EYE_R * np.cos(a), EYE_R * np.sin(a)) for a in EYE_RINGS], segs)
    off = np.arccos(np.clip(v[:, 2] / EYE_R, -1, 1))
    tint = np.where((off < PUPIL)[:, None], V(0.02, 0.02, 0.02), np.where((off < IRIS)[:, None], V(0.24, 0.42, 0.58),
                                                                           V(0.90, 0.88, 0.84)))
    return v, faces, S.normalize(v), tint

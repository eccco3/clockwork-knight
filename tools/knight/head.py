"""The knight's carved face.

Head frame: origin between the eyes at the centre of the skull, +x to the
figure's left, +y out of the face, +z up, metres. `field` is the sculpt,
`paint` the lacquer colour mask (lips, brows, lash line, blush), and
`paint_texture` bakes that mask as a front projection for the game shader.

Proportions are life-size (eye line at z = 0, chin at z = -0.110).
"""
import numpy as np
from . import sdf as S
from .sdf import V

EYE = V(0.0315, 0.0550, 0.0000)   # eyeball centre (mirrored)
EYE_R = 0.0150                    # eyeball radius
LID_T = 0.0016                    # lid thickness over the eyeball
AP_W = 1.04                       # aperture half-width (rad)
AP_UP = 0.335                     # upper lid height (rad): rests a little over the iris
AP_LO = 0.34                      # lower lid height (rad): meets the bottom of the iris
AP_TILT = 0.07                    # outer corner lift (rad)
IRIS = 0.385                      # iris radius (rad), for the shader

# front-projected paint texture: x in [-PAINT_X, PAINT_X], z in [PAINT_Z0, PAINT_Z1]
PAINT_X, PAINT_Z0, PAINT_Z1 = 0.064, -0.100, 0.044


def _aperture(q):
    """Angular eye opening test in the mirrored frame. <0 inside the opening (in metres on the eyeball)."""
    d = q - EYE
    r = np.maximum(S.length(d), 1e-9)
    th = np.arctan2(d[:, 0], d[:, 1])
    ph = np.arcsin(np.clip(d[:, 2] / r, -1, 1))
    s = th / AP_W
    s2 = np.clip(1.0 - s * s, 0.0, 1.0)
    # upper lid arches highest slightly toward the nose; lower lid is a shallow bowl, lowest toward the temple
    up = AP_UP * s2 ** 0.70 * (1.0 - 0.16 * s) + AP_TILT * s
    lo = -AP_LO * s2 ** 0.80 * (1.0 + 0.22 * s) + AP_TILT * s
    g = np.maximum(ph - up, lo - ph)
    # beyond the corners: angular distance to the corner, so the lids close and thin out all round
    g = np.where(np.abs(s) < 1.0, g, np.hypot((np.abs(s) - 1.0) * AP_W, ph - AP_TILT * np.sign(s)) + 0.004)
    return g * EYE_R, th, ph, up, lo


PART_X = np.array([0.0, 0.0050, 0.0100, 0.0150, 0.0195, 0.0228, 0.0250])
PART_Z = np.array([-0.0656, -0.0652, -0.0651, -0.0654, -0.0658, -0.0661, -0.0663])
PART_R = [0.0014, 0.0014, 0.0014, 0.0013, 0.0012, 0.0010, 0.0007]
PART_OUT = np.array([0.0004, 0.0004, 0.0004, 0.0004, 0.0006, 0.0009, 0.0014])     # the groove lifts out of the surface at the corner
_part_cache = None


def _part_line():
    """The lip parting as points on the sculpted lips (found once by casting back from the front)."""
    global _part_cache
    if _part_cache is None:
        lo, hi = np.full(len(PART_X), 0.040), np.full(len(PART_X), 0.120)
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            inside = _parts(np.stack([PART_X, mid, PART_Z], axis=1), stage="lips")["d"] < 0
            lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
        _part_cache = [V(x, y, z) for x, y, z in zip(PART_X, 0.5 * (lo + hi) + PART_OUT, PART_Z)]
    return _part_cache


def _parts(p, stage=None):
    q = S.mirror_x(p)
    P = {}
    # ---- skull and the large masses of the face: few forms, wide blends
    cran = S.ellipsoid(p, V(0, -0.012, 0.022), V(0.073, 0.093, 0.088))
    face = S.ellipsoid(p, V(0, 0.016, -0.040), V(0.0505, 0.0640, 0.0700))
    d = S.smin(cran, face, 0.032)
    # mandible: one sweep from the chin round the angle of the jaw and up the ramus
    jaw = S.tube(q, [V(0.000, 0.0660, -0.0950), V(0.0140, 0.0570, -0.0925), V(0.0275, 0.0300, -0.0855),
                     V(0.0365, 0.0040, -0.0740), V(0.0440, -0.0100, -0.0400), V(0.0500, -0.0150, -0.0050)],
                 [0.0135, 0.0128, 0.0120, 0.0115, 0.0130, 0.0130])
    d = S.smin(d, jaw, 0.024)
    chin = S.ellipsoid(p, V(0, 0.0700, -0.0975), V(0.0140, 0.0115, 0.0125))
    d = S.smin(d, chin, 0.016)
    muzzle = S.ellipsoid(p, V(0, 0.0500, -0.0640), V(0.0300, 0.0318, 0.0250))
    d = S.smin(d, muzzle, 0.022)
    malar = S.ellipsoid(q, V(0.0350, 0.0455, -0.0260), V(0.0205, 0.0220, 0.0250))
    d = S.smin(d, malar, 0.030)
    zyg = S.ellipsoid(q, V(0.0500, 0.0220, -0.0160), V(0.0150, 0.0260, 0.0120))
    d = S.smin(d, zyg, 0.026)
    brow = S.ellipsoid(q, V(0.0290, 0.0605, 0.0200), V(0.0250, 0.0125, 0.0095), S.euler(z=-14, y=6))
    d = S.smin(d, brow, 0.016)
    # ---- eye sockets: deepest beside the bridge and under the brow
    sock = S.ellipsoid(q, V(0.0265, 0.0870, 0.0055), V(0.0205, 0.0205, 0.0110), S.euler(y=-10))
    d = S.ssub(d, sock, 0.014)
    nasion = S.ellipsoid(p, V(0, 0.0900, 0.0020), V(0.0200, 0.0115, 0.0100))
    d = S.ssub(d, nasion, 0.010)
    # ---- nose: straight narrow dorsum with a slight scoop, a small defined tip, soft wings
    bridge = S.tube(p, [V(0, 0.0700, 0.0070), V(0, 0.0808, -0.0120), V(0, 0.0892, -0.0260), V(0, 0.0930, -0.0335)],
                    [0.0062, 0.0040, 0.0043, 0.0050])
    tip = S.ellipsoid(p, V(0, 0.0942, -0.0368), V(0.0066, 0.0066, 0.0058))
    ala = S.ellipsoid(q, V(0.0098, 0.0836, -0.0402), V(0.0042, 0.0066, 0.0048), S.euler(z=-18))
    d = S.smin(d, bridge, 0.0105)                              # the sidewalls slope gently into the cheeks
    col = S.tube(p, [V(0, 0.0952, -0.0408), V(0, 0.0850, -0.0432)], [0.0032, 0.0034])
    lobe = S.ellipsoid(p, V(0, 0.0866, -0.0392), V(0.0116, 0.0088, 0.0064))   # one form from wing to wing
    nose = S.smin(S.smin(S.smin(lobe, tip, 0.0070), ala, 0.0060), col, 0.0050)
    nose = S.smin(nose, bridge, 0.0070)
    d = S.smin(d, nose, 0.0058)
    nostril = S.ellipsoid(q, V(0.0056, 0.0868, -0.0456), V(0.0028, 0.0046, 0.0026), S.euler(z=-25))
    P["nostril"] = nostril
    d = S.ssub(d, nostril, 0.0030)
    # ---- mouth: closed and level
    up_l = S.ellipsoid(q, V(0.0086, 0.0814, -0.0606), V(0.0136, 0.0054, 0.0049), S.euler(z=-27, y=4))
    up_c = S.ellipsoid(p, V(0, 0.0834, -0.0620), V(0.0052, 0.0042, 0.0038))
    upper = S.smin(up_l, up_c, 0.003)
    lower = S.ellipsoid(q, V(0.0066, 0.0792, -0.0708), V(0.0130, 0.0066, 0.0058), S.euler(z=-25))
    lower = S.smin(lower, S.ellipsoid(p, V(0, 0.0802, -0.0710), V(0.0090, 0.0064, 0.0058)), 0.004)
    P["upper_lip"], P["lower_lip"] = upper, lower
    d = S.smin(d, S.smin(upper, lower, 0.0012), 0.0028)
    if stage == "lips":
        return {"d": d}
    part = S.tube(q, _part_line(), PART_R)
    P["part"] = part
    d = S.ssub(d, part, 0.0020)
    phil = S.tube(p, [V(0, 0.0888, -0.0485), V(0, 0.0897, -0.0565)], [0.0020, 0.0024])
    d = S.ssub(d, phil, 0.0040)
    crease = S.ellipsoid(p, V(0, 0.0870, -0.0815), V(0.0130, 0.0075, 0.0042))
    d = S.ssub(d, crease, 0.0060)
    # ---- eyelids: a shell over the eyeball, open across the aperture
    g, th, ph, up, lo = _aperture(q)
    r_eye = S.length(q - EYE)
    upper_side = ph > 0.5 * (up + lo)
    fade = np.clip((g - 0.0025) / np.where(upper_side, 0.0100, 0.0050), 0.0, 1.0)
    shell = r_eye - (EYE_R + LID_T - 0.0065 * fade * fade * (3.0 - 2.0 * fade))   # lid thins away from the opening
    d = S.smin(d, shell, 0.0080)
    # upper lid fold: a fine groove a little above the lash line
    s = th / AP_W
    fold_r = 0.0022 * np.clip(1.0 - (np.abs(s) / 0.95) ** 4, 0.0, 1.0)
    fold = np.hypot(r_eye - (EYE_R + LID_T + 0.0016), (ph - (up + 0.26)) * (EYE_R + LID_T)) - fold_r
    fold = np.where(fold_r > 1e-5, fold, 1.0)
    d = S.ssub(d, fold, 0.0020)
    # the opening itself: cut everything in front of the eyeball inside the aperture
    cut = np.maximum(np.maximum(g, r_eye - (EYE_R + 0.0045)), (EYE_R - 0.0012) - r_eye)
    d = S.smax(d, -cut, 0.0005)
    P["fold"] = fold
    P["lid_g"], P["lid_ph"], P["lid_up"], P["lid_lo"], P["lid_th"] = g, ph, up, lo, th
    P["r_eye"] = r_eye
    # ---- underside: flatten beneath the jaw so the neck gap reads cleanly
    nrm = V(0, -0.50, -1.0) / np.linalg.norm(V(0, -0.50, -1.0))
    d = S.smax(d, S.plane(p, V(0, 0.066, -0.1125), nrm), 0.009)
    P["d"] = d
    return P


def field(p):
    return _parts(p)["d"]


def density(p):
    """Mesh density weight: finer quads over the features."""
    f = np.clip((p[:, 1] - 0.030) / 0.030, 0, 1) * np.clip((0.040 - p[:, 2]) / 0.015, 0, 1) \
        * np.clip((p[:, 2] + 0.110) / 0.015, 0, 1)
    eye = np.exp(-((np.abs(p[:, 0]) - EYE[0]) ** 2 + (p[:, 2] - EYE[2]) ** 2) / (2 * 0.019 ** 2))
    mouth = np.exp(-(p[:, 0] ** 2 + (p[:, 2] + 0.066) ** 2) / (2 * 0.022 ** 2))
    nose = np.exp(-(p[:, 0] ** 2 + (p[:, 2] + 0.043) ** 2) / (2 * 0.010 ** 2))
    seam = np.exp(-((p[:, 2] + 0.0656) / 0.0035) ** 2) * (np.abs(p[:, 0]) < 0.028)
    return 1.0 + f * (5.0 + 14.0 * eye + 8.0 * mouth + 16.0 * nose + 14.0 * seam)


# ---------------------------------------------------------------- lid edge loops for the mesher

def lid_edge(p):
    """Feature curve for the mesher: > 0 on the lids, < 0 in the eye opening."""
    q = S.mirror_x(p)
    return np.maximum(_aperture(q)[0], S.length(q - EYE) - (EYE_R + 0.006))


def lid_inner(p):
    """Drop points that sit just inside the opening straight down the lid margin, to behind the eyeball surface.
    With the outer loop on the lid this makes the margin a clean radial wall, so the eyeball meets it in a smooth line."""
    sx = np.where(p[:, 0] < 0, -1.0, 1.0)
    c = EYE * np.stack([sx, np.ones(len(p)), np.ones(len(p))], axis=1)
    v = p - c
    return c + S.normalize(v) * (EYE_R - 0.0011)


def lip_seam(p):
    """Feature curve along the lip parting: > 0 above it, < 0 in a narrow band just below."""
    q = S.mirror_x(p)
    band = np.interp(q[:, 0], PART_X, PART_Z) - q[:, 2]
    return np.maximum(np.maximum(-band, band - 0.004), np.maximum(q[:, 0] - PART_X[-2], 0.05 - q[:, 1]))


FEATURES = [(lid_edge, lid_inner, 5e-4), (lip_seam, None, 0.0)]


# ---------------------------------------------------------------- paint

WOOD = V(1.0, 1.0, 1.0)
LIP = V(0.92, 0.66, 0.60)
LIP_DEEP = V(0.72, 0.44, 0.39)
BROW = V(0.36, 0.23, 0.15)
LASH = V(0.17, 0.10, 0.075)
SHADE = V(0.74, 0.56, 0.44)
BLUSH = V(1.0, 0.84, 0.78)

BROW_PTS = np.array([(0.0155, 0.0208), (0.0220, 0.0228), (0.0300, 0.0243), (0.0385, 0.0247), (0.0465, 0.0230),
                     (0.0535, 0.0198)])
BROW_W = np.array([0.0019, 0.0022, 0.0021, 0.0017, 0.0011, 0.0004])


def _hash2(i, j):
    h = np.sin(i * 127.1 + j * 311.7) * 43758.5453
    return h - np.floor(h)


def _noise2(x, y):
    i, j = np.floor(x), np.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    return (_hash2(i, j) * (1 - fx) + _hash2(i + 1, j) * fx) * (1 - fy) \
        + (_hash2(i, j + 1) * (1 - fx) + _hash2(i + 1, j + 1) * fx) * fy


def _brow(x, z):
    """Brow opacity in the front projection: a tapered arch drawn as fine strokes."""
    best = np.full(len(x), 1e9)
    width = np.zeros(len(x))
    along = np.zeros(len(x))
    for k in range(len(BROW_PTS) - 1):
        a, b = BROW_PTS[k], BROW_PTS[k + 1]
        ab = b - a
        t = np.clip(((x - a[0]) * ab[0] + (z - a[1]) * ab[1]) / (ab @ ab), 0, 1)
        dist = np.hypot(x - (a[0] + ab[0] * t), z - (a[1] + ab[1] * t))
        w = BROW_W[k] + (BROW_W[k + 1] - BROW_W[k]) * t
        better = dist - w < best
        best = np.where(better, dist - w, best)
        width = np.where(better, w, width)
        along = np.where(better, k + t, along)
    body = np.clip(-best / 0.0009, 0, 1)                       # soft edge
    # strokes lean outward and upward, flattening toward the tail
    lean = np.radians(58 - 9 * along)
    u = x * np.cos(lean) + z * np.sin(lean)
    v = -x * np.sin(lean) + z * np.cos(lean)
    hairs = 0.62 + 0.38 * _noise2(v * 3800.0, u * 420.0)
    return body * hairs * (0.72 + 0.28 * np.clip(along / 1.2, 0, 1))


def paint(p):
    """Lacquer tint multiplied over the wood at points on (or near) the surface. RGB in 0..1."""
    P = _parts(p)
    q = S.mirror_x(p)
    col = np.tile(WOOD, (len(p), 1))

    def mix(c, m):
        nonlocal col
        m = np.clip(m, 0, 1)[:, None]
        col = col * (1 - m) + c * m

    front = np.clip((p[:, 1] - 0.020) / 0.020, 0, 1)
    blush = np.exp(-(((q[:, 0] - 0.041) / 0.017) ** 2 + ((q[:, 2] + 0.030) / 0.015) ** 2)) * front
    mix(BLUSH, 0.45 * blush)
    # lips: a soft stain, deeper along the parting and at the corners
    lips = np.minimum(P["upper_lip"], P["lower_lip"])
    m = np.clip(1.0 - (lips - 0.0001) / 0.0011, 0, 1)
    m = m * m * (3 - 2 * m)
    deep = np.exp(-np.maximum(P["part"] - 0.0004, 0) / 0.0009) * 0.9 + 0.25 * np.clip((q[:, 0] - 0.012) / 0.012, 0, 1)
    mix(LIP * (1 - deep[:, None]) + LIP_DEEP * deep[:, None], m * 0.85)
    mix(V(0.42, 0.27, 0.20), np.clip(1.0 - (P["nostril"] + 0.0006) / 0.0014, 0, 1) * 0.8)
    # brows
    mix(BROW, _brow(q[:, 0], q[:, 2]) * 0.80 * front)
    # eyes: a soft shadow over the upper lid, a lash line that thickens outward, a faint lower line
    g = P["lid_g"]
    s = P["lid_th"] / AP_W
    upper_side = P["lid_ph"] > 0.5 * (P["lid_up"] + P["lid_lo"])
    on_lid = (P["r_eye"] < EYE_R + 0.0045) & (g > -0.0006)
    mix(SHADE, 0.55 * np.exp(-np.maximum(g, 0) / 0.0032) * upper_side * on_lid * (np.abs(s) < 1.08))
    mix(SHADE, 0.50 * np.clip(1.0 - (P["fold"] + 0.0012) / 0.0010, 0, 1) * on_lid)
    lw = np.where(upper_side, 0.0009 + 0.0009 * np.clip((s + 0.3) / 1.3, 0, 1), 0.0005)
    lash = np.clip(1.0 - (g - 0.0002) / lw, 0, 1) * on_lid
    lash = lash * np.where(upper_side, 1.0, 0.45 * np.clip((s + 0.2) / 0.8, 0, 1))
    mix(LASH, lash)
    return col


def paint_texture(width=1024):
    """Bake `paint` as seen from the front: (H, W, 3) array, row 0 at z = PAINT_Z1, column 0 at x = -PAINT_X.
    Each texel is traced back along -y to the first surface it meets."""
    half = width // 2
    height = int(round(width * (PAINT_Z1 - PAINT_Z0) / (2 * PAINT_X)))
    xs = (np.arange(half) + 0.5) / half * PAINT_X
    zs = PAINT_Z1 - (np.arange(height) + 0.5) / height * (PAINT_Z1 - PAINT_Z0)
    X, Z = np.meshgrid(xs, zs)
    x, z = X.ravel(), Z.ravel()
    y = np.full(len(x), 0.112)
    live = np.arange(len(x))
    for _ in range(40):                                         # sphere tracing; converged texels drop out
        dd = field(np.stack([x[live], y[live], z[live]], axis=1))
        y[live] -= np.clip(dd, 0.0, None) * 0.85
        live = live[(dd > 2e-5) & (y[live] > 0.0)]
        if len(live) == 0:
            break
    rgb = paint(np.stack([x, y, z], axis=1)).reshape(height, half, 3)
    return np.concatenate([rgb[:, ::-1], rgb], axis=1)

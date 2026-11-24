"""Her dress: off the shoulder, a smocked bodice with short puffed sleeves, a sash, and a gathered skirt to the calf.

World frame as the body's. `cloth` is the form the game mesh is fitted to, `detail` adds the smocking, gathers
and frills for the normal map, and `paint` colours it chartreuse with butter-yellow trim. One polycube meshes
it: rings run round the bodice, the skirt and each sleeve, and columns run from neckline to hem, so it can
be skinned to the body under it.
"""
import numpy as np
from sculpt import sdf as S
from sculpt.sdf import V
from sculpt.lattice import Box
from sculpt.num import smoothstep, bump, lerp, noise3, fbm, along, mix
from . import body
from .body import SHOULDER, UPPER, LEFT, BACK, UP

Z_NECK, Z_WAIST, Z_HEM = 1.338, 1.085, 0.300
SASH = (1.064, 1.106)
FRILL, HEM_BAND = 0.017, 0.050                 # height of the frill under the neckline, and of the hem's yellow band
HEM_EDGE = 0.008                             # thickness of the skirt's rolled edge
CUFF = 0.172                                   # along the upper arm from the shoulder: the sleeve's gathered end
EASE = 0.0055
FOLDS = 13                                     # folds round the skirt
DIAMONDS, DIAMOND_Z = 64, 0.0105               # smocking: cells round the bodice, and their height

CHARTREUSE = V(0.60, 0.74, 0.12)
SHADOW = V(0.40, 0.54, 0.07)
BUTTER = V(0.97, 0.88, 0.58)


def _round(p):
    """Angle round the body from straight ahead."""
    return np.arctan2(p[:, 0], -(p[:, 1] - 0.008))


def _skirt(p):
    """The skirt hanging from the waist over the hips: distance, and how far its folds have opened (0..1)."""
    z = p[:, 2]
    hip = smoothstep(Z_WAIST, 0.930, z)
    low = smoothstep(0.930, Z_HEM, z)
    rx = lerp(0.106, 0.174, hip) + 0.200 * (0.930 - z) * smoothstep(1.00, 0.86, z)
    squash = lerp(0.74, 0.93, low)
    yc = lerp(0.008, 0.014, hip)
    y = (p[:, 1] - yc) / squash
    th = np.arctan2(p[:, 0], -y)
    open_ = smoothstep(1.03, 0.42, z)
    w = FOLDS * th + 1.3 * np.sin(3.0 * th + 0.7) + 0.8 * np.sin(5.0 * th + 2.1 + 2.0 * z)
    fold = (0.5 + 0.5 * np.cos(w)) ** 1.4 - 0.42
    return (np.hypot(p[:, 0], y) - rx - 0.024 * open_ * fold) * 0.85, open_


def _sleeve(q):
    """A short puffed sleeve round the upper arm: distance, and the distance along the arm."""
    s, r = along(q, SHOULDER, body.ELBOW)
    arm = lerp(0.0400, 0.0335, np.clip(s / 0.20, 0, 1))
    puff = 0.004 + 0.016 * bump(s, 0.120, 0.038) + 0.006 * smoothstep(CUFF - 0.004, CUFF + 0.008, s)
    return S.smax(r - arm - puff, s - (CUFF + 0.010), 0.0015), s


def _cloth(p, fine=True):
    """The dress. Returns distance and the measures its paint needs."""
    q = S.mirror_x(p)
    z = p[:, 2]
    th = _round(p)
    wob = noise3(p * 14.0)
    bodice = S.smax(body.trunk(p) - EASE, Z_WAIST - 0.03 - z, 0.01)
    skirt, open_ = _skirt(p)
    d = S.smin(bodice, S.smax(skirt, z - (Z_WAIST + 0.010), 0.008), 0.016)
    sleeve, s = _sleeve(q)
    d = S.smin(d, sleeve, 0.014)
    d = S.smin(d, S.ellipsoid(q, SHOULDER + V(-0.004, 0.0, -0.105), V(0.042, 0.046, 0.045)), 0.020)        # cloth across the armpit
    frill = smoothstep(Z_NECK - FRILL - 0.004, Z_NECK - FRILL + 0.003, z)
    sash = smoothstep(SASH[0] - 0.002, SASH[0] + 0.001, z) * smoothstep(SASH[1] + 0.002, SASH[1] - 0.001, z)
    d = d - 0.0030 * frill - 0.0026 * sash
    P = dict(th=th, s=s, sleeve=sleeve, frill=frill, sash=sash, open=open_)
    if fine:
        a, b = DIAMONDS * th / (2 * np.pi) + z / DIAMOND_Z, DIAMONDS * th / (2 * np.pi) - z / DIAMOND_Z
        on_bodice = smoothstep(SASH[1], SASH[1] + 0.006, z) * (1.0 - frill) * smoothstep(0.004, 0.012, sleeve)
        puff = np.minimum(np.abs(np.sin(np.pi * a)), np.abs(np.sin(np.pi * b))) ** 0.6
        P["knot"] = smoothstep(0.34, 0.16, np.hypot(np.sin(np.pi * a), np.sin(np.pi * b))) * on_bodice
        P["puff"], P["bodice"] = puff, on_bodice
        gather = smoothstep(SASH[0] - 0.16, SASH[0], z) * (z < SASH[0]) * np.sin(96.0 * th + 5.0 * wob)
        ripple = frill * np.sin(52.0 * th + 4.0 * wob) * smoothstep(Z_NECK - FRILL, Z_NECK, z)
        hem = smoothstep(Z_HEM + 0.030, Z_HEM, z) * np.sin(70.0 * th + 6.0 * wob)
        tuck = bump(s, 0.118, 0.045) * np.sin(22.0 * np.arctan2((q - SHOULDER) @ BACK, (q - SHOULDER) @ LEFT) + 5.0 * wob) \
            * smoothstep(0.012, 0.0, sleeve)
        d = d - 0.0013 * puff * on_bodice - 0.0014 * gather - 0.0016 * ripple - 0.0012 * hem - 0.0012 * tuck \
            - 0.0010 * (fbm(p * 60.0, 2) - 0.5)
    d = S.smax(d, z - Z_NECK, 0.0015)
    d = S.smax(d, Z_HEM - z, 0.0040)
    hollow = S.smax(skirt + HEM_EDGE, z - (Z_HEM + 0.050), 0.020)                # open underneath, the cloth a rolled edge
    return S.ssub(d, hollow, 0.0035), P


def cloth(p):
    return _cloth(p, False)[0]


def detail(p):
    return _cloth(p)[0]


def paint(p):
    d, P = _cloth(p)
    z = p[:, 2]
    col = np.tile(CHARTREUSE, (len(p), 1)) * (0.94 + 0.12 * fbm(p * 22.0))[:, None]
    col = mix(col, SHADOW, 0.55 * (1.0 - P["puff"]) * P["bodice"])
    trim = np.maximum(P["frill"], smoothstep(Z_HEM + HEM_BAND + 0.002, Z_HEM + HEM_BAND - 0.002, z))
    trim = np.maximum(trim, smoothstep(CUFF - 0.004, CUFF, P["s"]) * smoothstep(0.012, 0.004, P["sleeve"]))
    sash = P["sash"]
    stripe = bump(z, Z_HEM + HEM_BAND + 0.016, 0.0035)
    col = mix(col, BUTTER * (0.95 + 0.10 * fbm(p * 30.0))[:, None], np.clip(trim + sash + 0.9 * stripe + P["knot"], 0, 1))
    return col, 0.86 - 0.38 * sash, np.zeros(len(p)), 1.0 - 0.6 * sash


def grid(detail):
    c = lambda n: body.cells(n, detail, 2)
    return dict(i=c(24), j=c(18), k=c(150), arm=c(7), sleeve=c(26))


def boxes(detail=1.0):
    """A trunk from hem to neckline with a sleeve from each flank. Lattice: i to her left, j backward, k up."""
    g = grid(detail)
    out = [Box((-g["i"], -g["j"], 0), (g["i"], g["j"], g["k"]), 2,
               [V(0, 0.012, Z_HEM), V(0, 0.014, 0.930), V(0, 0.008, Z_WAIST), V(0, 0.004, 1.250), V(0, 0.004, Z_NECK)],
               [0.240, 0.130, 0.085, 0.100, 0.100], [0.210, 0.085, 0.058, 0.068, 0.068], LEFT, BACK, cap=(0.0, 0.0))]
    path = [SHOULDER + V(-0.055, 0.0, -0.105), SHOULDER + UPPER * 0.110, SHOULDER + UPPER * (CUFF + 0.012)]
    for side in (1, -1):
        lo = (g["i"] if side > 0 else -g["i"] - g["sleeve"], -g["arm"], g["k"] - 2 * g["arm"])
        hi = (lo[0] + g["sleeve"], g["arm"], g["k"])
        out.append(Box(lo, hi, 0, [x * V(side, 1, 1) for x in path][::side], 0.028, 0.028, BACK, UP,
                       cap=(0.0, 0.2) if side > 0 else (0.2, 0.0)))
    return out


def seam(a, b, detail=1.0):
    """Cut like the garment: front and back panels joined at the sides, sleeves seamed underneath; the edges of
    the neckline and the hem's underside come away as their own strips."""
    g = grid(detail)

    def on(c):
        ai, aj, k = np.abs(c[:, 0]), np.abs(c[:, 1]), c[:, 2]
        low = g["k"] - 2 * g["arm"]
        side = (ai == g["i"]) & (aj == 0) & (k <= low)
        hole = (ai == g["i"]) & (aj <= g["arm"]) & (k >= low)
        under = (ai >= g["i"]) & (k == low) & (aj == 0)
        hem = (k == 0) & ((ai == g["i"]) | (aj == g["j"]))
        neck = (k == g["k"]) & (((aj == g["j"]) & (ai <= g["i"])) | ((ai == g["i"]) & (aj >= g["arm"]))
                                | ((ai > g["i"]) & (aj == g["arm"])) | (ai == g["i"] + g["sleeve"]))
        return side | under, hole, hem, neck
    return np.any([x & y for x, y in zip(on(a), on(b))], axis=0)

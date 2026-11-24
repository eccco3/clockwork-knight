"""Her hair, carved and gilded: swept back from the brow over the ears into a low coil at the nape.

Head frame as head.py's. `field` is the form the game mesh is fitted to, `detail` adds the strands for the
normal map and `paint` colours them. The hair is one blob that holds the skull; what the head hides is culled,
and two edge loops run along its edge.
"""
import numpy as np
from sculpt import sdf as S, mesher
from sculpt.sdf import V
from sculpt.mesher import Rail
from sculpt.num import smoothstep, noise3, fbm, mix
from . import head

THICK = 0.0070                                 # how far the hair stands off the skull
CENTRE_Y = -0.014                              # the hairline is measured round this upright line
COIL = V(0, -0.1000, -0.0300)                  # the coil at the nape
COIL_R = V(0.0440, 0.0300, 0.0380)
COMB = S.normalize(COIL - V(0, 0.090, 0.000))  # the strands run back along this line toward the coil
LINE_AZ = np.radians([0, 25, 45, 62, 78, 92, 108, 128, 152, 180])
LINE_Z = np.array([0.0700, 0.0690, 0.0640, 0.0500, 0.0260, -0.0060, -0.0340, -0.0540, -0.0640, -0.0660])
ROLL = 0.0032                                  # the round of the hair's edge where it meets the skin
RES = (60, 64, 56)                             # lattice at full detail: across, front to back, up
EDGE_RING = 0.16                               # the upper loop along the edge, as a share of the lattice's height
LEAN = 0.70                                    # the lattice leans as the hairline does: high at the brow, low at the nape
AXIS = (V(0, -0.018, 0.088), V(0, -0.085, -0.020))

BLONDE = V(0.86, 0.69, 0.36)
PALE = V(0.95, 0.84, 0.56)
DEEP = V(0.56, 0.39, 0.16)


def _hairline(q):
    """Height of the hair's edge at each angle round the head from straight ahead (mirrored frame)."""
    az = np.arctan2(q[:, 0], q[:, 1] - CENTRE_Y)
    k = np.interp(az, LINE_AZ, np.arange(len(LINE_AZ)))
    i = np.clip(k.astype(int), 0, len(LINE_AZ) - 2)
    t = k - i
    t = t * t * (3.0 - 2.0 * t)                                 # eased, so the edge has no corners
    return LINE_Z[i] * (1.0 - t) + LINE_Z[i + 1] * t


def _strands(p, fine=True):
    """Height of the locks above the smooth hair; fine adds the strands. Combed back, coiled at the nape."""
    v = p - V(0, CENTRE_Y, 0.028)
    h = v @ COMB
    side = v - np.outer(h, COMB)
    ex = V(1.0, 0.0, 0.0)
    ey = np.cross(COMB, ex)
    turn = np.arctan2(side @ ex, side @ ey)
    back = np.arctan2(S.length(side), -h)
    wave = turn + 0.10 * np.sin(5.0 * back + 2.0 * np.sin(3.0 * turn))
    c = p - COIL
    coil = smoothstep(1.25, 0.85, S.length(c / COIL_R))
    twist = np.arctan2(c[:, 0], c[:, 2]) + 5.0 * S.length(c * V(1, 0, 1)) / COIL_R[0]
    cs, sn = np.cos(wave) * (1 - coil) + np.cos(twist) * coil, np.sin(wave) * (1 - coil) + np.sin(twist) * coil
    lock = 0.0050 * (noise3(np.stack([cs * 3.6, sn * 3.6, back * 0.9], axis=1)) - 0.5)
    if not fine:
        return lock
    strand = noise3(np.stack([cs * 17.0, sn * 17.0, back * 1.6 + 3.0], axis=1))
    hair = noise3(np.stack([cs * 58.0, sn * 58.0, back * 2.5 + 7.0], axis=1))
    return lock + 0.0013 * (strand - 0.5) + 0.0005 * (hair - 0.5)


def _parts(p, fine=True):
    q = S.mirror_x(p)
    d = head.skull(p) - THICK
    d = S.smin(d, S.ellipsoid(q, V(0.0560, -0.0320, 0.0040), V(0.0215, 0.0520, 0.0460)), 0.020)     # over the ears
    d = S.smin(d, S.ellipsoid(p, V(0, 0.0340, 0.0790), V(0.0500, 0.0360, 0.0240)), 0.022)           # lifted off the brow
    d = S.smin(d, S.ellipsoid(p, COIL, COIL_R), 0.012)
    rise = _strands(p, fine)
    return dict(d=S.smax(d - rise, _hairline(q) - p[:, 2], ROLL), rise=rise)


def field(p):
    return _parts(p, False)["d"]


def detail(p):
    return _parts(p)["d"]


def paint(p):
    rise = _parts(p)["rise"]
    t = np.clip(rise / 0.0045 + 0.5, 0, 1)
    col = mix(np.tile(DEEP, (len(p), 1)), BLONDE, smoothstep(0.15, 0.55, t))
    col = mix(col, PALE, smoothstep(0.55, 0.95, t) * (0.6 + 0.4 * fbm(p * 80.0)))
    return col, 0.34 + 0.16 * (1.0 - t), np.zeros(len(p)), np.ones(len(p))


def dims(detail):
    return tuple(2 * max(4, round(r * detail / 2)) for r in RES)


def rails(detail):
    """Two loops along the hair's edge: on its round, and a little way up the hair."""
    def above(by):
        return lambda p: p[:, 2] - _hairline(S.mirror_x(p)) - by
    ring = round(EDGE_RING * dims(detail)[2])
    return [Rail(ring - 1, above(0.0008)), Rail(ring, above(0.0050))]


def wrap(detail=1.0):
    """The hair's quad mesh in the head frame: verts, quads, normals and lattice points."""
    n = dims(detail)
    v, q, nrm = mesher.wrap(field, *AXIS, (0.095, 0.125, 0.115), n, relax=12, rails=rails(detail),
                            warp=lambda u: u + np.outer(LEAN * u[:, 1], V(0, 0, 1)))
    unit = mesher.cube_lattice(*n)[0]
    return v, q, nrm, np.rint((unit + 1.0) / 2.0 * np.array(n)).astype(np.int64)


def seam(a, b, detail=1.0):
    """One island, opened down the back of the head through the coil."""
    n = dims(detail)

    def on(c):
        return (c[:, 0] == n[0] // 2) & ((c[:, 1] == 0) | ((c[:, 2] == 0) & (c[:, 1] <= n[1] // 2)))
    return on(a) & on(b)

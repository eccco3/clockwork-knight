"""Signed-distance sculpting primitives (numpy, vectorised over (N,3) point arrays).

Shapes are callables p -> distance. They are combined with smooth unions /
subtractions and then meshed by `mesher.py`, which wraps an all-quad cube
lattice onto the zero level set.
"""
import numpy as np

V = lambda *a: np.array(a, dtype=np.float64)


def length(v):
    return np.sqrt((v * v).sum(-1))


def normalize(v):
    return v / np.maximum(length(v)[..., None], 1e-12)


def rot_x(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def euler(x=0.0, y=0.0, z=0.0):
    """Rotation matrix R (local -> world), angles in degrees, applied X then Y then Z."""
    return rot_z(np.radians(z)) @ rot_y(np.radians(y)) @ rot_x(np.radians(x))


# ---------------------------------------------------------------- primitives

def sphere(p, c, r):
    return length(p - c) - r


def ellipsoid(p, c, r, R=None):
    """Ellipsoid with radii r, optional orientation R (local->world)."""
    q = p - c
    if R is not None:
        q = q @ R  # world -> local  (R^T applied to column vectors)
    r = np.asarray(r, dtype=np.float64)
    k0 = length(q / r)
    k1 = length(q / (r * r))
    return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -r.min())


def capsule(p, a, b, r):
    pa, ba = p - a, b - a
    h = np.clip((pa * ba).sum(-1) / max((ba * ba).sum(), 1e-18), 0.0, 1.0)
    return length(pa - ba * h[..., None]) - r


def cone(p, a, b, r1, r2):
    """Capsule whose radius goes r1 -> r2 from a to b."""
    pa, ba = p - a, b - a
    h = np.clip((pa * ba).sum(-1) / max((ba * ba).sum(), 1e-18), 0.0, 1.0)
    return length(pa - ba * h[..., None]) - (r1 + (r2 - r1) * h)


def tube(p, pts, radii):
    """Round polyline through pts with per-point radii (scalar or list)."""
    pts = [np.asarray(q, dtype=np.float64) for q in pts]
    if np.isscalar(radii):
        radii = [radii] * len(pts)
    d = None
    for i in range(len(pts) - 1):
        di = cone(p, pts[i], pts[i + 1], radii[i], radii[i + 1])
        d = di if d is None else np.minimum(d, di)
    return d


def box(p, c, half, r=0.0, R=None):
    q = p - c
    if R is not None:
        q = q @ R
    q = np.abs(q) - (np.asarray(half, dtype=np.float64) - r)
    return length(np.maximum(q, 0.0)) + np.minimum(q.max(-1), 0.0) - r


def cylinder(p, a, b, r, rnd=0.0):
    """Capped cylinder from a to b, radius r, edge rounding rnd."""
    ba = b - a
    L = np.sqrt((ba * ba).sum())
    ax = ba / L
    pa = p - a
    h = (pa * ax).sum(-1)
    rad = length(pa - ax * h[..., None])
    dx = rad - (r - rnd)
    dy = np.abs(h - L * 0.5) - (L * 0.5 - rnd)
    return np.minimum(np.maximum(dx, dy), 0.0) + np.sqrt(np.maximum(dx, 0) ** 2 + np.maximum(dy, 0) ** 2) - rnd


def torus(p, c, axis, R, r):
    """Torus centred c, around unit `axis`, major R minor r."""
    q = p - c
    h = (q * axis).sum(-1)
    rad = length(q - axis * h[..., None])
    return np.sqrt((rad - R) ** 2 + h ** 2) - r


def plane(p, c, n):
    """Half-space: negative behind the plane (opposite n)."""
    return ((p - c) * n).sum(-1)


# ---------------------------------------------------------------- operators

def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


def ssub(a, b, k):
    """a with b carved out."""
    return smax(a, -b, k)


def union(*ds, k=0.0):
    d = ds[0]
    for e in ds[1:]:
        d = smin(d, e, k)
    return d


def mirror_x(p):
    q = p.copy()
    q[..., 0] = np.abs(q[..., 0])
    return q


def hug(f, c, ex, ey, n=40, a0=0.0, a1=np.pi, rmax=0.3, off=0.0008):
    """Points on the surface of `f` along rays from the inside point `c`, fanned in the plane (ex, ey)."""
    a = np.linspace(a0, a1, n)
    d = np.outer(np.cos(a), ex) + np.outer(np.sin(a), ey)
    lo, hi = np.zeros(n), np.full(n, rmax)
    for _ in range(34):
        mid = 0.5 * (lo + hi)
        inside = f(np.asarray(c) + d * mid[:, None]) < 0
        lo, hi = np.where(inside, mid, lo), np.where(inside, hi, mid)
    return np.asarray(c) + d * (0.5 * (lo + hi) + off)[:, None]


def gradient(f, p, eps=2e-5):
    g = np.empty_like(p)
    for i in range(3):
        e = np.zeros(3)
        e[i] = eps
        g[:, i] = f(p + e) - f(p - e)
    return normalize(g)

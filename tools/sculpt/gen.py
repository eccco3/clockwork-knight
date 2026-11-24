"""Hard-surface generators: lathe-turned parts, plates with thickness, gears, sweeps.

Everything returns (verts ndarray (N,3), faces list-of-tuples) in a local frame;
`Frame` places it in the figure's rest pose.
"""
import numpy as np


def _n(v):
    v = np.asarray(v, dtype=np.float64)
    return v / max(np.linalg.norm(v), 1e-12)


class Frame:
    """Orthonormal frame: local +z along `z`, local +x as close to x_hint as possible."""

    def __init__(self, o, z=(0, 0, 1), x_hint=(1, 0, 0)):
        z = _n(z)
        x = np.asarray(x_hint, dtype=np.float64)
        x = _n(x - z * np.dot(x, z))
        y = np.cross(z, x)
        self.o = np.asarray(o, dtype=np.float64)
        self.R = np.stack([x, y, z], axis=1)

    def w(self, p):
        return self.o + np.asarray(p, dtype=np.float64) @ self.R.T

    def l(self, p):
        return (np.asarray(p, dtype=np.float64) - self.o) @ self.R

    def dir(self, d):
        return np.asarray(d, dtype=np.float64) @ self.R.T


def smooth_profile(pts, sub=4):
    """Catmull-Rom through (z, r) control points."""
    P = np.asarray(pts, dtype=np.float64)
    out = []
    n = len(P)
    for i in range(n - 1):
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, n - 1)]
        for k in range(sub):
            t = k / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    out = np.array(out)
    out[:, 1] = np.maximum(out[:, 1], 0.0)
    return out


def turned(pts, sub=3):
    """A smooth profile whose ends stay on the axis where the control points put them."""
    p = smooth_profile(pts, sub)
    p[0, 1] = 0.0 if pts[0][1] == 0 else p[0, 1]
    p[-1, 1] = 0.0 if pts[-1][1] == 0 else p[-1, 1]
    return p


def arc(cz, r, a0, a1, n):
    """Profile points on a circle in the (z, r) plane, angles in degrees measured from +z."""
    a = np.radians(np.linspace(a0, a1, n))
    return [(cz + r * np.cos(t), abs(r * np.sin(t))) for t in a]


def lathe(prof, segs=32, sx=1.0, sy=1.0, phase=0.0):
    """Revolve (z, r) profile about local z. r == 0 at an end makes a pole, otherwise an n-gon cap."""
    verts, faces, rings = [], [], []
    for z, r in prof:
        if r <= 1e-7:
            rings.append([len(verts)])
            verts.append((0.0, 0.0, z))
        else:
            rings.append(list(range(len(verts), len(verts) + segs)))
            for k in range(segs):
                a = 2 * np.pi * (k + phase) / segs
                verts.append((r * np.cos(a) * sx, r * np.sin(a) * sy, z))
    for A, B in zip(rings[:-1], rings[1:]):
        if len(A) == 1 and len(B) == 1:
            continue
        for k in range(segs):
            k1 = (k + 1) % segs
            if len(A) == 1:
                faces.append((A[0], B[k], B[k1]))
            elif len(B) == 1:
                faces.append((A[k], B[0], A[k1]))
            else:
                faces.append((A[k], B[k], B[k1], A[k1]))
    if len(rings[0]) > 1:
        faces.append(tuple(rings[0]))
    if len(rings[-1]) > 1:
        faces.append(tuple(reversed(rings[-1])))
    return np.array(verts), faces


def capsule(length, r0, r1=None, segs=12, cap=3, squash=1.0):
    """Rounded rod along +z from 0 to length; end caps flattened by `squash`."""
    r1 = r0 if r1 is None else r1
    prof = []
    for i in range(cap + 1):
        t = np.pi / 2 * i / cap
        prof.append((r0 * squash * (1 - np.cos(t)), r0 * np.sin(t)))
    for i in range(cap, -1, -1):
        t = np.pi / 2 * i / cap
        prof.append((length - r1 * squash * (1 - np.cos(t)), r1 * np.sin(t)))
    return lathe(prof, segs)


def clip(verts, c, n):
    """Flatten everything beyond the plane (c, n) onto it (mitre cut for lathe parts)."""
    n = _n(n)
    d = (verts - np.asarray(c)) @ n
    return verts - np.outer(np.maximum(d, 0.0), n)


def patch(outer, inner, tol=1e-6):
    """Plate between two (nu, nv, 3) point grids. Coincident edges (seams, poles) are detected and
    left unrimmed so that a merge-by-distance afterwards yields a clean closed shell."""
    nu, nv = outer.shape[:2]
    verts = np.concatenate([outer.reshape(-1, 3), inner.reshape(-1, 3)])
    off = nu * nv
    idx = lambda i, j: i * nv + j
    faces = []
    for i in range(nu - 1):
        for j in range(nv - 1):
            faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
            faces.append((off + idx(i, j), off + idx(i, j + 1), off + idx(i + 1, j + 1), off + idx(i + 1, j)))
    same = lambda a, b: np.linalg.norm(a - b) < tol
    for j in (0, nv - 1):                      # rims along u
        for i in range(nu - 1):
            if same(outer[i, j], outer[i + 1, j]):
                continue
            q = (idx(i, j), idx(i + 1, j), off + idx(i + 1, j), off + idx(i, j))
            faces.append(q[::-1] if j == 0 else q)
    for j in range(nv - 1):                    # rims along v, unless the two u-edges meet (seam)
        if same(outer[0, j], outer[-1, j]) and same(outer[0, j + 1], outer[-1, j + 1]):
            continue
        for i in (0, nu - 1):
            if same(outer[i, j], outer[i, j + 1]):
                continue
            q = (idx(i, j), idx(i, j + 1), off + idx(i, j + 1), off + idx(i, j))
            faces.append(q if i == 0 else q[::-1])
    return verts, faces


def tube(points, radius, segs=8, closed=False, squash=1.0):
    """Sweep a circle (optionally flattened along the first normal) along a polyline."""
    P = np.asarray(points, dtype=np.float64)
    n = len(P)
    rad = np.full(n, radius) if np.isscalar(radius) else np.asarray(radius, dtype=np.float64)
    tang = np.empty_like(P)
    for i in range(n):
        a = P[(i - 1) % n] if (closed or i > 0) else P[i]
        b = P[(i + 1) % n] if (closed or i < n - 1) else P[i]
        tang[i] = _n(b - a)
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(up, tang[0])) > 0.9:
        up = np.array([1.0, 0.0, 0.0])
    nrm = _n(up - tang[0] * np.dot(up, tang[0]))
    verts, faces = [], []
    for i in range(n):
        nrm = _n(nrm - tang[i] * np.dot(nrm, tang[i]))      # parallel transport
        bi = np.cross(tang[i], nrm)
        for k in range(segs):
            a = 2 * np.pi * k / segs
            verts.append(P[i] + rad[i] * (np.cos(a) * nrm * squash + np.sin(a) * bi))
    last = n if closed else n - 1
    for i in range(last):
        i1 = (i + 1) % n
        for k in range(segs):
            k1 = (k + 1) % segs
            faces.append((i * segs + k, i1 * segs + k, i1 * segs + k1, i * segs + k1))
    if not closed:
        faces.append(tuple(range(segs - 1, -1, -1)))
        faces.append(tuple(range((n - 1) * segs, n * segs)))
    return np.array(verts), faces


def gear(teeth, r_root, r_tip, r_hole=0.0, spokes=0, rim=None, hub=None):
    """Flat spur-gear face set in the local xy plane (z = 0); the builder gives it thickness.
    With spokes > 0 the web is cut into windows between a hub and the toothed rim."""
    step = 2 * np.pi / teeth
    ang, rad = [], []
    for t in range(teeth):
        for da, r in ((0.00, r_root), (0.20, r_root), (0.34, r_tip), (0.66, r_tip), (0.80, r_root)):
            ang.append((t + da) * step)
            rad.append(r)
    m = len(ang)
    rim = r_root * 0.80 if rim is None else rim
    hub = max(r_hole * 1.9, r_root * 0.30) if hub is None else hub
    verts, faces = [], []

    def ring(radii):
        base = len(verts)
        for k in range(m):
            r = radii[k] if hasattr(radii, "__len__") else radii
            verts.append((r * np.cos(ang[k]), r * np.sin(ang[k]), 0.0))
        return base

    def band(a, b, keep=lambda k: True):
        for k in range(m):
            if keep(k):
                k1 = (k + 1) % m
                faces.append((a + k, b + k, b + k1, a + k1))

    o = ring(rad)
    if spokes:
        r1, r2 = ring(rim), ring(hub)
        band(r1, o)
        win = m / spokes
        band(r2, r1, lambda k: (k % win) < max(1.0, win * 0.22))
        inner = r2
    else:
        inner = o
    if r_hole > 0:
        r3 = ring(r_hole)
        band(r3, inner)
    else:
        c = len(verts)
        verts.append((0.0, 0.0, 0.0))
        for k in range(m):
            faces.append((c, inner + k, inner + (k + 1) % m))
    return np.array(verts), faces


def lathe_ring(section, segs=32, sx=1.0, sy=1.0):
    """Revolve a closed (z, r) polygon about local z: bands, bezels, cuffs."""
    n = len(section)
    verts, faces = [], []
    for z, r in section:
        for k in range(segs):
            a = 2 * np.pi * k / segs
            verts.append((r * np.cos(a) * sx, r * np.sin(a) * sy, z))
    for i in range(n):
        i1 = (i + 1) % n
        for k in range(segs):
            k1 = (k + 1) % segs
            faces.append((i * segs + k, i1 * segs + k, i1 * segs + k1, i * segs + k1))
    return np.array(verts), faces


def cap(R, thick, theta_max, nu=32, nv=8, radii=(1.0, 1.0, 1.0)):
    """Domed plate: part of a sphere of radius R about local +z, reaching polar angle
    theta_max(azimuth) (radians, array -> array). Returns outer/inner grids for `patch`."""
    az = np.linspace(0.0, 2 * np.pi, nu)
    tm = theta_max(az)
    tm[-1] = tm[0]
    v = np.linspace(1.0, 0.0, nv)                    # rim -> pole
    th = tm[:, None] * v[None, :]
    def grid(r):
        g = np.stack([r * np.sin(th) * np.cos(az)[:, None], r * np.sin(th) * np.sin(az)[:, None], r * np.cos(th)], axis=-1)
        g[-1] = g[0]
        return g * np.asarray(radii)
    return grid(R), grid(R - thick)


def box(half, bevel=0.0):
    hx, hy, hz = half
    v = np.array([(sx * hx, sy * hy, sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)])
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return v, f


def dome(r, h=None, segs=10, rings=3):
    """Rivet head / boss: spherical cap rising along +z from z=0."""
    h = r * 0.6 if h is None else h
    prof = [(h * np.sin(np.pi / 2 * i / rings), r * np.cos(np.pi / 2 * i / rings)) for i in range(rings + 1)]
    return lathe(prof, segs)

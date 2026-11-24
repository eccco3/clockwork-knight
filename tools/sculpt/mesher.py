"""All-quad meshing of a signed-distance sculpt.

A cube lattice (only extraordinary vertices: the 8 corners) is wrapped onto
the surface by casting rays outward from an inner axis segment, then relaxed
tangentially so quads stay even. Normals come from the field gradient, so
shading is exact rather than tessellation dependent.
"""
import numpy as np
from . import sdf as S


def cube_lattice(nx, ny, nz):
    idx, pts, quads = {}, [], []

    def vid(i, j, k):
        key = (i, j, k)
        if key not in idx:
            idx[key] = len(pts)
            pts.append((2.0 * i / nx - 1.0, 2.0 * j / ny - 1.0, 2.0 * k / nz - 1.0))
        return idx[key]

    for i in range(nx):
        for j in range(ny):
            quads.append((vid(i, j, 0), vid(i, j + 1, 0), vid(i + 1, j + 1, 0), vid(i + 1, j, 0)))
            quads.append((vid(i, j, nz), vid(i + 1, j, nz), vid(i + 1, j + 1, nz), vid(i, j + 1, nz)))
    for j in range(ny):
        for k in range(nz):
            quads.append((vid(0, j, k), vid(0, j, k + 1), vid(0, j + 1, k + 1), vid(0, j + 1, k)))
            quads.append((vid(nx, j, k), vid(nx, j + 1, k), vid(nx, j + 1, k + 1), vid(nx, j, k + 1)))
    for k in range(nz):
        for i in range(nx):
            quads.append((vid(i, 0, k), vid(i + 1, 0, k), vid(i + 1, 0, k + 1), vid(i, 0, k + 1)))
            quads.append((vid(i, ny, k), vid(i, ny, k + 1), vid(i + 1, ny, k + 1), vid(i + 1, ny, k)))
    return np.array(pts), np.array(quads, dtype=np.int64)


def _closest_on_segment(p, a, b):
    ba = b - a
    den = (ba * ba).sum()
    if den < 1e-18:
        return np.broadcast_to(a, p.shape).copy()
    h = np.clip(((p - a) * ba).sum(-1) / den, 0.0, 1.0)
    return a + ba * h[:, None]


def _cast(f, o, d, tmax, coarse=40, fine=14):
    """Outermost surface crossing along each ray o + t d, t in [0, tmax]."""
    n = len(o)
    ts = np.linspace(tmax, 0.0, coarse + 1)
    hi = np.full(n, tmax)
    lo = np.zeros(n)
    found = np.zeros(n, dtype=bool)
    prev = np.full(n, tmax)
    for t in ts:
        v = f(o + d * t) < 0.0
        new = v & ~found
        lo[new] = t
        hi[new] = prev[new]
        found |= v
        prev = np.where(found, prev, t)
        if found.all():
            break
    for _ in range(fine):
        mid = 0.5 * (lo + hi)
        inside = f(o + d * mid[:, None]) < 0.0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    t = 0.5 * (lo + hi)
    t[~found] = 0.0
    return o + d * t[:, None], found


class Rail:
    """A ring of the lattice held on a feature while the rest relaxes, so the feature gets an edge loop.

    ring: the loop's index along the lattice's third axis. g: points -> metres, zero on the feature's curve
    and growing away from the feature into the surface the loop borders."""

    def __init__(self, ring, g):
        self.ring, self.g = ring, g


def wrap(f, a, b, extent, dims, relax=10, tmax=None, density=None, snap=None, snap_inner=None, rails=(), warp=None):
    """Mesh sculpt f. a,b: inner axis segment (inside the shape). extent: rough
    half-size (x,y,z) of the shape about the segment midpoint. dims: lattice
    resolution (nx,ny,nz). density: optional p -> weight; quads shrink where
    it is large. rails: rings held on features. warp: optional reshaping of the unit sphere
    the lattice starts on. Returns verts (N,3), quads (Q,4), normals (N,3)."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    unit, quads = cube_lattice(*dims)
    # cube -> sphere for an even start
    x, y, z = unit[:, 0], unit[:, 1], unit[:, 2]
    sph = np.stack([
        x * np.sqrt(1 - y * y / 2 - z * z / 2 + y * y * z * z / 3),
        y * np.sqrt(1 - z * z / 2 - x * x / 2 + z * z * x * x / 3),
        z * np.sqrt(1 - x * x / 2 - y * y / 2 + x * x * y * y / 3)], axis=1)
    extent = np.asarray(extent, dtype=np.float64)
    mid = 0.5 * (a + b)
    p = mid + (sph if warp is None else warp(sph)) * extent
    if tmax is None:
        tmax = float(extent.max()) * 2.2

    edges = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    deg = np.zeros(len(p))
    np.add.at(deg, edges[:, 0], 1)
    np.add.at(deg, edges[:, 1], 1)

    def project(p, local=True):
        o = _closest_on_segment(p, a, b)
        v = p - o
        dist = S.length(v)
        d = v / np.maximum(dist, 1e-12)[:, None]
        if not local:
            return _cast(f, o, d, tmax)[0]
        # search a short bracket around the current surface distance first
        delta = tmax * 0.07
        base = np.maximum(dist - delta, 0.0)
        q, ok = _cast(f, o + d * base[:, None], d, 2.0 * delta, coarse=10, fine=13)
        ok &= f(o + d * (base + 2.0 * delta)[:, None]) >= 0.0
        if not ok.all():
            bad = ~ok
            q[bad] = _cast(f, o[bad], d[bad], tmax)[0]
        return q

    def slide(g, q, goal, place, steps=7):
        """Newton steps moving q along grad g to g = goal; `place` puts each step back where it belongs."""
        grad = np.zeros_like(q)
        for _ in range(steps):
            gq = g(q)
            for i in range(3):
                e = np.zeros(3)
                e[i] = 5e-5
                grad[:, i] = (g(q + e) - g(q - e)) / 1e-4
            n2 = np.maximum((grad * grad).sum(-1), 1e-9)
            q = place(q - grad * ((gq - goal) / n2)[:, None])
        return q, S.normalize(grad)

    lattice = np.rint((unit + 1.0) / 2.0 * np.array(dims)).astype(np.int64)
    side = np.flatnonzero((lattice[:, 0] % dims[0] == 0) | (lattice[:, 1] % dims[1] == 0))
    columns = side[np.lexsort(lattice[side].T[::-1])].reshape(-1, dims[2] + 1)
    held = columns[:, [r.ring for r in rails]].T.ravel()

    def settle(steps):
        """Slide the rails onto their curves. Returns the direction each point's g grows in."""
        def g(q):
            return np.concatenate([r.g(x) for r, x in zip(rails, np.split(q, len(rails)))])
        p[held], away = slide(g, p[held], 0.0, project, steps)
        return away

    p = project(p, local=False)
    if rails:                                                   # spread the rings between the rails evenly
        settle(7)
        rings = sorted({0, dims[2]} | {r.ring for r in rails})
        for lo, hi in zip(rings[:-1], rings[1:]):
            k = np.arange(lo + 1, hi)
            t = ((k - lo) / (hi - lo))[None, :, None]
            p[columns[:, k]] = p[columns[:, [lo]]] * (1.0 - t) + p[columns[:, [hi]]] * t
        p[side] = project(p[side], local=False)
    for _ in range(relax):
        acc = np.zeros_like(p)
        if density is None:
            np.add.at(acc, edges[:, 0], p[edges[:, 1]])
            np.add.at(acc, edges[:, 1], p[edges[:, 0]])
            tot = deg
        else:
            w = density(0.5 * (p[edges[:, 0]] + p[edges[:, 1]]))
            tot = np.zeros(len(p))
            np.add.at(acc, edges[:, 0], p[edges[:, 1]] * w[:, None])
            np.add.at(acc, edges[:, 1], p[edges[:, 0]] * w[:, None])
            np.add.at(tot, edges[:, 0], w)
            np.add.at(tot, edges[:, 1], w)
        p = project(0.5 * p + 0.5 * acc / tot[:, None])
        if rails:
            settle(1)
    away = settle(7) if rails else None
    n = S.gradient(f, p)
    if rails:
        n[held] = S.gradient(f, p[held] + away * 5e-4)
    feats = [] if snap is None else (list(snap) if isinstance(snap, (list, tuple)) else [(snap, snap_inner, 5e-4)])
    e0, e1 = edges[:, 0], edges[:, 1]
    target = 1.2e-4

    for g, inner, n_off in feats:
        # Put a clean edge loop on a feature curve g = 0 (g > 0 is the kept side):
        # every lattice edge that crosses the curve has its nearer end slid onto it.
        gv = g(p)
        cross = (gv[e0] > 0) != (gv[e1] > 0)
        pick = np.where(np.abs(gv[e0[cross]]) <= np.abs(gv[e1[cross]]), e0[cross], e1[cross])
        idx = np.unique(pick)
        q, gdir = slide(g, p[idx].copy(), target, project)
        p[idx] = q
        n[idx] = S.gradient(f, q + gdir * n_off)
        if inner is not None:
            # second loop: every vertex still across the curve from a snapped one is slid to just
            # inside it and handed to `inner`, which places it at the foot of the feature's wall
            gv = g(p)
            cross = (gv[e0] > 0) != (gv[e1] > 0)
            idx2 = np.unique(np.where(gv[e0[cross]] < 0, e0[cross], e1[cross]))
            q, gdir = slide(g, p[idx2].copy(), -target, inner)
            p[idx2] = q
            n[idx2] = -gdir                                      # the wall faces into the opening
    return p, quads, n


def catmull_once(verts, quads):
    """One linear quad subdivision (new verts are re-projected by the caller)."""
    edge_mid, new_pts = {}, list(verts)

    def mid(i, j):
        key = (i, j) if i < j else (j, i)
        if key not in edge_mid:
            edge_mid[key] = len(new_pts)
            new_pts.append(0.5 * (verts[i] + verts[j]))
        return edge_mid[key]

    out = []
    for q in quads:
        c = len(new_pts)
        new_pts.append(verts[q].mean(axis=0))
        m = [mid(q[i], q[(i + 1) % 4]) for i in range(4)]
        for i in range(4):
            out.append((q[i], m[i], c, m[i - 1]))
    return np.array(new_pts), np.array(out, dtype=np.int64)

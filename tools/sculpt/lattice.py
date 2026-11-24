"""All-quad meshing of branching sculpts.

mesher wraps one cube lattice onto a sculpt. Here several boxes share one integer lattice
(a polycube: a trunk with limbs extruded from its faces), each box is laid along its limb as a thin
tube, and the skin of the whole is shrunk onto the zero level set and relaxed. Edge loops ring every
limb, and the only extraordinary vertices are the box corners.
"""
import numpy as np
from . import sdf as S


class Box:
    """Cells lo..hi on the lattice, swept along `path` with the lattice axis `axis`.

    The other two lattice axes (in index order) span the section: the first points along `u`, the
    second along `v`, with half-widths ra and rb at each path point. Keep the tube inside the limb."""

    def __init__(self, lo, hi, axis, path, ra, rb, u, v, cap=(0.6, 0.6)):
        self.lo, self.hi, self.axis = np.array(lo), np.array(hi), axis
        self.path = np.array(path, dtype=np.float64)
        n = len(self.path)
        self.ra = np.full(n, ra, dtype=np.float64) if np.isscalar(ra) else np.array(ra, dtype=np.float64)
        self.rb = np.full(n, rb, dtype=np.float64) if np.isscalar(rb) else np.array(rb, dtype=np.float64)
        self.u, self.v, self.cap = np.array(u, dtype=np.float64), np.array(v, dtype=np.float64), cap
        seg = self.path[1:] - self.path[:-1]
        length = S.length(seg)
        self.s = np.concatenate([[0.0], np.cumsum(length)]) / length.sum()
        d = seg / length[:, None]
        self.tan = S.normalize(np.concatenate([d[:1], d[:-1] + d[1:], d[-1:]]))

    def embed(self, lattice):
        """Points for lattice coordinates, and the tube's half-width at each."""
        f = (lattice - self.lo) / (self.hi - self.lo)
        t = f[:, self.axis]
        a, b = [2.0 * f[:, k] - 1.0 for k in range(3) if k != self.axis]
        a, b = a * np.sqrt(1.0 - b * b / 2.0), b * np.sqrt(1.0 - a * a / 2.0)
        i = np.clip(np.searchsorted(self.s, t, side="right") - 1, 0, len(self.s) - 2)
        w = ((t - self.s[i]) / (self.s[i + 1] - self.s[i]))[:, None]
        c = self.path[i] * (1 - w) + self.path[i + 1] * w
        tan = S.normalize(self.tan[i] * (1 - w) + self.tan[i + 1] * w)
        ra = self.ra[i] * (1 - w[:, 0]) + self.ra[i + 1] * w[:, 0]
        rb = self.rb[i] * (1 - w[:, 0]) + self.rb[i + 1] * w[:, 0]
        u = S.normalize(self.u - tan * (tan @ self.u)[:, None])
        v = np.cross(tan, u)
        v *= np.sign((v * self.v).sum(-1))[:, None]
        dome = np.sqrt(np.clip(1.0 - a * a - b * b, 0.0, 1.0)) * np.minimum(ra, rb)
        end = self.cap[1] * (t > 1 - 1e-9) - self.cap[0] * (t < 1e-9)
        return c + u * (ra * a)[:, None] + v * (rb * b)[:, None] + tan * (dome * end)[:, None], np.minimum(ra, rb)


def polycube(boxes):
    """Skin of the union of the boxes: lattice points (N,3) int, quads (Q,4), and each point's box
    (the first that holds it, so list a trunk before its limbs)."""
    lo = np.min([b.lo for b in boxes], axis=0) - 1
    hi = np.max([b.hi for b in boxes], axis=0) + 1
    occ = np.zeros(hi - lo, dtype=bool)
    for b in boxes:
        occ[tuple(slice(l, h) for l, h in zip(b.lo - lo, b.hi - lo))] = True
    corners = []
    for ax in range(3):
        bx, cx = (ax + 1) % 3, (ax + 2) % 3
        for sign in (1, -1):
            cells = np.argwhere(occ & ~np.roll(occ, -sign, axis=ax)) + lo
            if sign > 0:
                cells[:, ax] += 1
            ring = ((0, 0), (1, 0), (1, 1), (0, 1))
            for db, dc in (ring if sign > 0 else ring[::-1]):
                c = cells.copy()
                c[:, bx] += db
                c[:, cx] += dc
                corners.append(c)
            # the four corner arrays of this direction are consecutive: regroup them per quad below
    per = [np.stack(corners[k:k + 4], axis=1) for k in range(0, len(corners), 4)]
    allq = np.concatenate(per)                                  # (Q, 4, 3)
    lattice, inv = np.unique(allq.reshape(-1, 3), axis=0, return_inverse=True)
    quads = inv.reshape(-1, 4)
    owner = np.full(len(lattice), -1)
    for k in range(len(boxes) - 1, -1, -1):
        inside = np.all((lattice >= boxes[k].lo) & (lattice <= boxes[k].hi), axis=1)
        owner[inside] = k
    return lattice, quads, owner


def grad(f, p, eps=1e-4):
    g = np.empty_like(p)
    for i in range(3):
        e = np.zeros(3)
        e[i] = eps
        g[:, i] = (f(p + e) - f(p - e)) / (2 * eps)
    return g


def project(f, p, steps=3, limit=0.006):
    """Newton steps toward the nearest point of the surface, each no longer than `limit`."""
    for _ in range(steps):
        g = grad(f, p)
        step = g * (f(p) / np.maximum((g * g).sum(-1), 1e-12))[:, None]
        p = p - step * np.minimum(1.0, limit / np.maximum(S.length(step), 1e-12))[:, None]
    return p


def edges_of(quads):
    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    return np.unique(np.sort(e, axis=1), axis=0)


def fit(f, boxes, relax=30, pin=None):
    """Mesh sculpt f with the polycube `boxes`. Returns verts, quads, normals, lattice points.
    pin: optional lattice -> bool mask of points that relaxation leaves where the embedding put them."""
    lattice, quads, owner = polycube(boxes)
    p, thick = np.empty((len(lattice), 3)), np.empty(len(lattice))
    for k, b in enumerate(boxes):
        m = owner == k
        p[m], thick[m] = b.embed(lattice[m].astype(np.float64))
    fixed = np.zeros(len(p), dtype=bool) if pin is None else pin(lattice)
    e = edges_of(quads)
    deg = np.zeros(len(p))
    np.add.at(deg, e[:, 0], 1)
    np.add.at(deg, e[:, 1], 1)
    p = project(f, p, 14)
    start = p.copy()
    for _ in range(relax):
        acc = np.zeros_like(p)
        np.add.at(acc, e[:, 0], p[e[:, 1]])
        np.add.at(acc, e[:, 1], p[e[:, 0]])
        d = acc / deg[:, None] - p
        n = S.normalize(grad(f, p))
        d = 0.55 * (d - n * (d * n).sum(-1)[:, None])
        # a step longer than the limb is thick would leave a thin curved limb and land back on one side of it
        d *= np.minimum(1.0, 0.5 * thick / np.maximum(S.length(d), 1e-12))[:, None]
        p = project(f, p + d, 2)
        p[fixed] = start[fixed]
    p = project(f, p, 3)
    n = S.gradient(f, p)
    a, b, c = p[quads[:, 0]], p[quads[:, 1]], p[quads[:, 2]]
    if (np.cross(b - a, c - a) * n[quads[:, 0]]).sum() < 0:
        quads = quads[:, ::-1].copy()
    return p, quads, n, lattice


def cull(verts, quads, hidden, extra=()):
    """Drop quads whose corners are all hidden, and the points nothing uses any more."""
    keep = ~hidden[quads].all(axis=1)
    quads = quads[keep]
    used = np.unique(quads)
    remap = np.full(len(verts), -1)
    remap[used] = np.arange(len(used))
    return (verts[used], remap[quads]) + tuple(x[used] for x in extra)

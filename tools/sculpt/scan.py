"""Solids from triangle meshes such as scans, for sculpting with and for carrying a mesh's shapes onto another.

A mesh of polygons is split into its connected shells and every hole in a shell is capped with a fan to a
point added at the hole's centre, so each shell is closed. `Solid` is the union of such shells: a field for
`mesher.wrap` and the pieces, and `bind`, which ties points to the surface so that they follow it when its
vertices move. Near a shell its field is exact, signed by the angle-weighted normal at the nearest place on
it, which tells inside from out for any closed shell (Baerentzen and Aanaes); further out it is interpolated
from exact values on a grid round the shell, made the first time the field is asked for, and keeps its sign.
"""
import itertools
import numpy as np
from mathutils.bvhtree import BVHTree

STEP = 0.004                                   # the grid's spacing (metres),
REACH = 0.08                                   # and how far it reaches round a shell, as far as an occluder looks
ERROR = STEP * np.sqrt(3.0) / 2.0              # interpolation is never further out than this
CHUNK = 65536


def _shells(faces):
    """The faces grouped by the connected shell they belong to."""
    parent = {}

    def root(i):
        while parent.setdefault(i, i) != i:
            parent[i] = i = parent[parent[i]]
        return i
    for f in faces:
        for i in f[1:]:
            parent[root(i)] = root(f[0])
    groups = {}
    for f in faces:
        groups.setdefault(root(f[0]), []).append(f)
    return list(groups.values())


def _holes(faces):
    """The loops of vertices round each hole of a shell."""
    edges = {(f[i - 1], f[i]) for f in faces for i in range(len(f))}
    after = {b: a for a, b in edges if (b, a) not in edges}
    loops = []
    while after:
        start, at = after.popitem()
        loop = [start]
        while at != start:
            loop.append(at)
            at = after.pop(at)
        loops.append(loop)
    return loops


def closed(faces, first):
    """Polygons, a corner of which may come twice (a triangle given as a quad with its last corner twice), as
    closed shells of triangles. Returns one (T, 3) array per shell and the loops of the holes; the fan over
    loop k meets at vertex first + k, which `centred` adds."""
    shells, loops = [], []
    for group in _shells([list(dict.fromkeys(f)) for f in faces]):
        tris = [(f[0], f[i], f[i + 1]) for f in group for i in range(1, len(f) - 1)]
        for loop in _holes(group):
            centre = first + len(loops)
            tris += [(centre, loop[i - 1], loop[i]) for i in range(len(loop))]
            loops.append(np.array(loop))
        shells.append(np.array(tris))
    return shells, loops


def centred(v, loops):
    """Vertices (..., N, 3), or their offsets, with the centre of each loop added after them."""
    return np.concatenate([v] + [v[..., loop, :].mean(-2, keepdims=True) for loop in loops], axis=-2)


def _dot(a, b):
    return (a * b).sum(-1)


def _nearest(p, a, b, c):
    """The nearest place to each point p on its triangle abc (all (N, 3)), and where on the triangle it lies:
    0 within it, 1 to 3 at the corners a, b and c, 4 to 6 on the sides ab, bc and ca."""
    ab, ac = b - a, c - a
    d1, d2 = _dot(ab, p - a), _dot(ac, p - a)
    d3, d4 = _dot(ab, p - b), _dot(ac, p - b)
    d5, d6 = _dot(ab, p - c), _dot(ac, p - c)
    va, vb, vc = d3 * d6 - d5 * d4, d5 * d2 - d1 * d6, d1 * d4 - d3 * d2
    with np.errstate(divide="ignore", invalid="ignore"):
        along = np.stack([d1 / (d1 - d3), (d4 - d3) / ((d4 - d3) + (d5 - d6)), d2 / (d2 - d6)], 1)
        v, w = vb / (va + vb + vc), vc / (va + vb + vc)
    where = np.select([(d1 <= 0) & (d2 <= 0), (d3 >= 0) & (d4 <= d3), (vc <= 0) & (d1 >= 0) & (d3 <= 0),
                       (d6 >= 0) & (d5 <= d6), (vb <= 0) & (d2 >= 0) & (d6 <= 0),
                       (va <= 0) & (d4 >= d3) & (d5 >= d6)], [1, 2, 4, 3, 6, 5], 0)
    places = [a, b, c, a + along[:, :1] * ab, b + along[:, 1:2] * (c - b), a + along[:, 2:] * ac]
    q = np.select([(where == k)[:, None] for k in range(1, 7)], places, a + v[:, None] * ab + w[:, None] * ac)
    return q, where


class _Shell:
    """One closed shell of triangles over the vertices v: their tree, the angle-weighted normals of its
    triangles' insides, corners and sides, and the grid its field is interpolated from further out."""

    def __init__(self, v, tris):
        self.tris = np.asarray(tris, dtype=np.int64)
        self.tree = BVHTree.FromPolygons(v.tolist(), self.tris.tolist())
        self.corners = v[self.tris]
        self.lo, self.hi = self.corners.min((0, 1)), self.corners.max((0, 1))
        face = np.cross(self.corners[:, 1] - self.corners[:, 0], self.corners[:, 2] - self.corners[:, 0])
        face /= np.maximum(np.linalg.norm(face, axis=1), 1e-30)[:, None]
        corner = np.zeros_like(v)
        for k in range(3):
            e1, e2 = self.corners[:, (k + 1) % 3] - self.corners[:, k], self.corners[:, (k + 2) % 3] - self.corners[:, k]
            angle = np.arctan2(np.linalg.norm(np.cross(e1, e2), axis=1), _dot(e1, e2))
            np.add.at(corner, self.tris[:, k], angle[:, None] * face)
        ends = np.sort(np.stack([self.tris, np.roll(self.tris, -1, axis=1)], -1).reshape(-1, 2), axis=1)
        _, side = np.unique(ends[:, 0] * len(v) + ends[:, 1], return_inverse=True)
        sides = np.zeros((side.max() + 1, 3))
        np.add.at(sides, side, np.repeat(face, 3, axis=0))
        self.normals = face, corner[self.tris], sides[side].reshape(-1, 3, 3)
        self.values = None

    def reach(self, p):
        """How far each point lies outside the shell's box: no nearer than this to the shell."""
        return np.linalg.norm(np.maximum(np.maximum(self.lo - p, p - self.hi), 0.0), axis=1)

    def nearest(self, p, cap=None):
        """The triangle each point is nearest to and the nearest place on it, and where on the triangle that
        lies (see _nearest); triangle -1 for points further than cap (N,) from the shell."""
        find = self.tree.find_nearest
        hits = map(find, p.tolist()) if cap is None else map(find, p.tolist(), cap.tolist())
        tri = np.fromiter((-1 if h[2] is None else h[2] for h in hits), np.int64, len(p))
        q, where = _nearest(p, *(self.corners[tri, k] for k in range(3)))
        return tri, q, where

    def exact(self, p, cap=None):
        """Signed distances, exact, of points whose nearest place on the shell is within cap (N,) of them."""
        out = np.empty(len(p))
        for k in range(0, len(p), CHUNK):
            x = p[k:k + CHUNK]
            tri, q, where = self.nearest(x, None if cap is None else cap[k:k + CHUNK])
            assert (tri >= 0).all(), "a point lay further from the shell than the grid allows"
            face, corner, side = self.normals
            n = np.where((where == 0)[:, None], face[tri], np.where(
                (where <= 3)[:, None], corner[tri, np.clip(where - 1, 0, 2)], side[tri, np.clip(where - 4, 0, 2)]))
            d = np.linalg.norm(x - q, axis=1)
            out[k:k + CHUNK] = np.where(_dot(x - q, n) < 0.0, -d, d)
        return out

    def interpolated(self, p):
        """The field from the grid: within ERROR of the exact one, and beyond the grid the distance to the box."""
        if self.values is None:
            self.origin = self.lo - REACH
            self.size = np.ceil((self.hi - self.lo + 2 * REACH) / STEP).astype(np.int64) + 1
            axes = [self.origin[k] + STEP * np.arange(self.size[k]) for k in range(3)]
            self.values = self.exact(np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, 3)).reshape(self.size)
        u = (p - self.origin) / STEP
        i = np.clip(np.floor(u).astype(np.int64), 0, self.size - 2)
        f = np.clip(u - i, 0.0, 1.0)
        g = np.zeros(len(p))
        for corner in itertools.product((0, 1), repeat=3):
            w = np.prod(np.where(corner, f, 1.0 - f), axis=1)
            g += w * self.values[i[:, 0] + corner[0], i[:, 1] + corner[1], i[:, 2] + corner[2]]
        beyond = ((u < 0) | (u > self.size - 1)).any(1)
        g[beyond] = self.reach(p[beyond])
        return g

    def field(self, p):
        d = self.interpolated(p)
        near = np.flatnonzero(np.abs(d) < 2.0 * ERROR)
        d[near] = self.exact(p[near], np.abs(d[near]) + ERROR + 1e-6)
        return d


class Solid:
    """The union of closed shells of triangles over the vertices v (metres)."""

    def __init__(self, v, shells):
        self.v = np.asarray(v, dtype=np.float64)
        self.shells = [_Shell(self.v, t) for t in sorted(shells, key=len, reverse=True)]

    def field(self, p):
        """Signed distance: negative inside any shell."""
        d = np.full(len(p), np.inf)
        inside = np.zeros(len(p), dtype=bool)
        for shell in self.shells:
            ask = np.flatnonzero(shell.reach(p) < d)
            near = shell.field(p[ask])
            d[ask] = np.minimum(d[ask], np.abs(near))
            inside[ask] |= near < 0.0
        return np.where(inside, -d, d)

    def bind(self, p):
        """Ties points to the surface. Returns the corners (N, 3) and weights (N, 3) of each point's nearest place
        on it, by which `carry` moves the points with the vertices."""
        d = np.full(len(p), np.inf)
        corners = np.zeros((len(p), 3), dtype=np.int64)
        foot = np.zeros((len(p), 3))
        for shell in self.shells:
            ask = np.flatnonzero(shell.reach(p) < d)
            tri, q, _ = shell.nearest(p[ask], d[ask])
            hit, tri, q = ask[tri >= 0], tri[tri >= 0], q[tri >= 0]
            d[hit], corners[hit], foot[hit] = np.linalg.norm(p[hit] - q, axis=1), shell.tris[tri], q
        a, b, c = (self.v[corners[:, k]] for k in range(3))
        n = np.cross(b - a, c - a)
        area = (n * n).sum(-1)
        wb = (np.cross(foot - a, c - a) * n).sum(-1) / area
        wc = (np.cross(b - a, foot - a) * n).sum(-1) / area
        return corners, np.stack([1.0 - wb - wc, wb, wc], axis=1)


def carry(v, corners, weights):
    """Where bound points lie on vertices (..., N, 3), or how far offsets of the vertices move them."""
    return (v[..., corners, :] * weights[..., None]).sum(-2)

"""Solids from triangle meshes such as scans, for sculpting with and for carrying a mesh's shapes onto another.

A mesh of polygons is split into its connected shells and every hole in a shell is capped with a fan to a
point added at the hole's centre, so each shell is closed. `Solid` is the union of such shells: a field for
`mesher.wrap` and the pieces, and `bind`, which ties points to the surface so that they follow it when its
vertices move.
"""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

RAYS = [Vector(d).normalized() for d in ((0.3713, 0.5477, 0.7497), (-0.6131, 0.7243, -0.3154), (0.5279, -0.2917, -0.7977))]
SKIP = 1e-7
FACING = 0.999                                 # a point this squarely before or behind its nearest triangle needs no ray


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
    """Polygons as closed shells of triangles. Returns one (T, 3) array per shell and the loops of the holes;
    the fan over loop k meets at vertex first + k, which `centred` adds."""
    shells, loops = [], []
    for group in _shells(faces):
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


def _enclosed(tree, at):
    """Whether a shell encloses a point: most rays from it cross the shell an odd number of times."""
    odd = 0
    for ray in RAYS:
        x, count = at, 0
        while True:
            hit = tree.ray_cast(x, ray)[0]
            if hit is None:
                break
            x, count = hit + ray * SKIP, count + 1
        odd += count % 2
    return 2 * odd > len(RAYS)


class Solid:
    """The union of closed shells of triangles over the vertices v."""

    def __init__(self, v, shells):
        self.v = np.asarray(v, dtype=np.float64)
        self.shells = sorted(shells, key=len, reverse=True)
        self.trees = [BVHTree.FromPolygons(self.v.tolist(), t.tolist()) for t in self.shells]
        self.boxes = [(self.v[np.unique(t)].min(0), self.v[np.unique(t)].max(0)) for t in self.shells]

    def _each(self, p, best):
        """Every shell with the points that may lie nearer to it than `best`, which the caller keeps up to date."""
        for tree, tris, (lo, hi) in zip(self.trees, self.shells, self.boxes):
            reach = np.linalg.norm(np.maximum(np.maximum(lo - p, p - hi), 0.0), axis=1)
            near = np.flatnonzero(reach < best)
            yield tree, tris, near, p[near].tolist()

    def field(self, p):
        """Signed distance in the units of v: negative inside any shell."""
        d = np.full(len(p), np.inf)
        inside = np.zeros(len(p), dtype=bool)
        for tree, _, near, points in self._each(p, d):
            for i, x in zip(near, points):
                foot, normal, _, dist = tree.find_nearest(x)
                d[i] = min(d[i], dist)
                out = (Vector(x) - foot).dot(normal)
                if abs(out) > FACING * dist:
                    inside[i] |= out < 0.0
                else:
                    inside[i] |= _enclosed(tree, Vector(x))
        return np.where(inside, -d, d)

    def bind(self, p):
        """Ties points to the surface. Returns the corners (N, 3) and weights (N, 3) of each point's nearest place
        on it, by which `carry` moves the points with the vertices."""
        d = np.full(len(p), np.inf)
        corners = np.zeros((len(p), 3), dtype=np.int64)
        foot = np.zeros((len(p), 3))
        for tree, tris, near, points in self._each(p, d):
            for i, x in zip(near, points):
                co, _, tri, dist = tree.find_nearest(x)
                if dist < d[i]:
                    d[i], corners[i], foot[i] = dist, tris[tri], co
        a, b, c = (self.v[corners[:, k]] for k in range(3))
        n = np.cross(b - a, c - a)
        area = (n * n).sum(-1)
        wb = (np.cross(foot - a, c - a) * n).sum(-1) / area
        wc = (np.cross(b - a, foot - a) * n).sum(-1) / area
        return corners, np.stack([1.0 - wb - wc, wb, wc], axis=1)


def carry(v, corners, weights):
    """Where bound points lie on vertices (..., N, 3), or how far offsets of the vertices move them."""
    return (v[..., corners, :] * weights[..., None]).sum(-2)

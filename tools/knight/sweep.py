"""Where the knight's pieces go as she moves, for carving what must keep clear of them.

A piece is held in balls as it rests: a limb by `along`, a plate by `over`. A `Sweep` carries such balls through
runs of poses, each pose given as how the piece's bone has moved from rest as the carved piece's bone sees it,
and through what lies between one pose and the next. Its `field` is then the distance to all they passed through.

Lengths are metres."""
import numpy as np
from mathutils import Matrix
from mathutils.kdtree import KDTree

GRAIN = 0.002                      # the balls are gathered on a grid this fine
SIZES = 0.004                      # and their radii rounded up to a multiple of this
STRIDE = 0.005                     # no ball goes further than this from one place it is put to the next
SPAN = 4096                        # the grid's cells along each side of the box, at most


def along(verts, a, b, step=0.012):
    """Balls on the line from a through b that together hold a limb, given its vertices, one to each `step` of it:
    centres (n, 3) and radii."""
    axis = (b - a) / np.linalg.norm(b - a)
    slices = np.floor((verts - a) @ axis / step).astype(int)
    centres = np.array([a + axis * (k + 0.5) * step for k in np.unique(slices)])
    return centres, np.array([np.linalg.norm(verts[slices == k] - c, axis=1).max() for k, c in zip(np.unique(slices), centres)])


def over(verts, faces, spacing=0.004):
    """Balls that together hold a surface, their centres spread over its faces `spacing` apart: centres (n, 3) and radii."""
    points = []
    for face in faces:
        for i in range(1, len(face) - 1):
            a, b, c = verts[face[0]], verts[face[i]], verts[face[i + 1]]
            n = max(int(np.ceil(max(np.linalg.norm(b - a), np.linalg.norm(c - b), np.linalg.norm(a - c)) / spacing)), 1)
            u, v = np.meshgrid(np.arange(n + 1) / n, np.arange(n + 1) / n, indexing="ij")
            inside = u + v <= 1.0 + 1e-9
            points.append(a + np.outer(u[inside], b - a) + np.outer(v[inside], c - a))
    points = np.unique(np.round(np.concatenate(points) / (0.25 * spacing)).astype(np.int64), axis=0) * (0.25 * spacing)
    return points, np.full(len(points), 0.75 * spacing)


class Sweep:
    """All that balls have passed through in and about the box from `lo` to `hi`."""

    def __init__(self, lo, hi):
        self.lo, self.hi = np.asarray(lo, dtype=np.float64), np.asarray(hi, dtype=np.float64)
        self.cells = {}                # for each radius the balls come in, the grid cells they were centred in
        self.trees = None

    def add(self, centres, radii, run):
        """Carries balls through a run of poses (n, 4, 4), in the order she takes them."""
        radii = np.ceil((radii + GRAIN) / SIZES) * SIZES       # a cell's centre is under a grain from any point in it
        was = None
        for pose in run:
            now = centres @ pose[:3, :3].T + pose[:3, 3]
            if was is not None:
                steps = 1 + int(np.linalg.norm(now - was[1], axis=1).max() / STRIDE)
                for t in np.arange(1, steps) / steps:
                    part = np.array(Matrix(was[0].tolist()).lerp(Matrix(pose.tolist()), t))
                    self._put(centres @ part[:3, :3].T + part[:3, 3], radii)
            self._put(now, radii)
            was = (pose, now)
        self.trees = None

    def _put(self, at, radii):
        kept = np.all((at > self.lo - radii[:, None]) & (at < self.hi + radii[:, None]), axis=1)
        cell = np.floor((at[kept] - self.lo) / GRAIN).astype(np.int64) + SPAN // 4
        keys = (cell[:, 0] * SPAN + cell[:, 1]) * SPAN + cell[:, 2]
        for radius in np.unique(radii[kept]):
            self.cells[radius] = np.union1d(self.cells.get(radius, keys[:0]), keys[radii[kept] == radius])

    def field(self, p):
        """Distance from each point to what was swept, negative inside it."""
        if self.trees is None:
            self.trees = []
            for radius, keys in self.cells.items():
                cells = np.stack([keys // (SPAN * SPAN), keys // SPAN % SPAN, keys % SPAN], axis=1) - SPAN // 4
                tree = KDTree(len(cells))
                for i, centre in enumerate((self.lo + (cells + 0.5) * GRAIN).tolist()):
                    tree.insert(centre, i)
                tree.balance()
                self.trees.append((radius, tree))
        d = np.full(len(p), np.inf)
        points = p.tolist()
        for radius, tree in self.trees:
            d = np.minimum(d, [tree.find(point)[2] - radius for point in points])
        return d

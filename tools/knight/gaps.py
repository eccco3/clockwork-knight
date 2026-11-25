"""How close the knight's pieces come to one another as she moves.

`report` takes her pieces as objects in the rest pose, each bound to one bone or weighted on several, and
measures the air between every pair of a mover and another piece, in every pose it is shown: vertex to
surface, both ways. A paired piece is only measured against its own side's pieces and the unpaired ones."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

REACH = 0.03                       # metres; wider gaps than this are not measured
RIGHT = "_R"
SIGHTS = [Vector(d).normalized() for d in ((0.26, 0.53, 0.81), (-0.26, -0.53, -0.81), (0.87, -0.47, 0.03))]


class _Piece:
    def __init__(self, ob):
        me = ob.data
        self.name, self.bones = ob.name, [g.name for g in ob.vertex_groups]
        self.rest = np.array([v.co for v in me.vertices])
        self.faces = [tuple(p.vertices) for p in me.polygons]
        self.weights = np.zeros((len(self.rest), len(self.bones)))
        for v in me.vertices:
            for g in v.groups:
                self.weights[v.index, g.group] = g.weight
        self.weights /= self.weights.sum(axis=1, keepdims=True)
        self._shape(self.rest)

    def _shape(self, verts):
        self.tree = BVHTree.FromPolygons(verts.tolist(), self.faces)
        self.lo, self.hi = verts.min(0) - REACH, verts.max(0) + REACH

    def pose(self, at):
        """Puts the piece where the rig has it: `at` maps each bone to how it has moved from rest."""
        if len(self.bones) == 1:               # a rigid piece keeps its shape, and is measured where it rests
            moved = at[self.bones[0]]
            self.verts, self.seen = self.rest @ moved[:3, :3].T + moved[:3, 3], np.linalg.inv(moved)
        else:
            moved = np.stack([self.rest @ at[b][:3, :3].T + at[b][:3, 3] for b in self.bones], axis=1)
            self.verts, self.seen = (moved * self.weights[:, :, None]).sum(axis=1), np.eye(4)
            self._shape(self.verts)

    def clearance(self, pts):
        """Distance from this piece's surface to the nearest of the posed `pts`, negative if it is inside; at most REACH."""
        pts = pts @ self.seen[:3, :3].T + self.seen[:3, 3]
        best = REACH
        for p in pts[np.all((pts > self.lo) & (pts < self.hi), axis=1)]:
            dist = self.tree.find_nearest(p, REACH)[3]
            if dist is not None:
                best = min(best, -dist if self._holds(p) else dist)
        return best

    def _holds(self, p):
        """Whether p is inside this closed piece: rays from it meet the back of a face first. Every way it looks
        must agree, since a mitred part has faces folded flat on its cut that face either way."""
        for sight in SIGHTS:
            normal = self.tree.ray_cast(p, sight)[1]
            if normal is None or normal.dot(sight) <= 0.0:
                return False
        return True


def _matches(name, prefixes):
    return any(name.startswith(p) for p in prefixes)


def _same_side(a, b, names):
    """False for a right piece and the left one of a pair, whichever way round."""
    for x, y in ((a, b), (b, a)):
        if x.endswith(RIGHT) and not y.endswith(RIGHT) and y + RIGHT in names:
            return False
    return True


def report(arm, objects, movers, others, poses):
    """Print the smallest gap between each piece named in `movers` and each named in `others` (both lists of
    name prefixes), where it was, and in how many poses they met. `poses` yields a label each time it has put
    the rig in the next pose to measure."""
    names = {ob.name for ob in objects}
    pieces = [_Piece(ob) for ob in objects if _matches(ob.name, movers + others)]
    pairs = [(m, o) for m in pieces if _matches(m.name, movers) for o in pieces
             if _matches(o.name, others) and m.bones != o.bones and _same_side(m.name, o.name, names)]
    rest = {b.name: np.array(b.matrix_local.inverted()) for b in arm.data.bones}
    least, met, shown = {}, {pair: 0 for pair in pairs}, 0
    for label in poses:
        shown += 1
        at = {bone: np.array(arm.pose.bones[bone].matrix) @ rest[bone] for pc in pieces for bone in pc.bones}
        for pc in pieces:
            pc.pose(at)
        for m, o in pairs:
            gap = min(o.clearance(m.verts), m.clearance(o.verts))
            met[m, o] += gap < 0.0
            if gap < least.get((m, o), (REACH, None))[0]:
                least[m, o] = (gap, label)
    for m, o in pairs:
        gap, label = least.get((m, o), (REACH, None))
        print("GAP %-22s %-22s %s" % (m.name, o.name, "%6.1f mm at %s, met in %d of %d poses" % (gap * 1e3, label, met[m, o], shown)
                                      if label else "over %d mm" % (REACH * 1e3)))

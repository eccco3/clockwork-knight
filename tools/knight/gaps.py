"""How close the knight's rigid pieces come to one another as she moves.

`report` takes her pieces as objects in the rest pose, each bound to one bone, and measures the air between
every pair of a mover and another piece, in every pose it is shown: vertex to surface, both ways. A paired
piece is only measured against its own side's pieces and the unpaired ones."""
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

REACH = 0.03                       # metres; wider gaps than this are not measured
RIGHT = "_R"
SIGHTS = [Vector(d).normalized() for d in ((0.26, 0.53, 0.81), (-0.26, -0.53, -0.81), (0.87, -0.47, 0.03))]


class _Piece:
    def __init__(self, ob):
        me = ob.data
        self.name, self.bone = ob.name, ob.vertex_groups[0].name
        self.verts = np.array([v.co for v in me.vertices])
        self.tree = BVHTree.FromPolygons(self.verts.tolist(), [tuple(p.vertices) for p in me.polygons])
        self.lo, self.hi = self.verts.min(0) - REACH, self.verts.max(0) + REACH

    def clearance(self, pts):
        """Distance from this piece's surface to the nearest of `pts`, negative if it is inside; at most REACH."""
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
             if _matches(o.name, others) and m.bone != o.bone and _same_side(m.name, o.name, names)]
    rest = {b.name: np.array(b.matrix_local.inverted()) for b in arm.data.bones}
    least, met, shown = {}, {pair: 0 for pair in pairs}, 0
    for label in poses:
        shown += 1
        at = {pc.bone: np.array(arm.pose.bones[pc.bone].matrix) @ rest[pc.bone] for pc in pieces}
        for m, o in pairs:
            to_o = np.linalg.inv(at[o.bone]) @ at[m.bone]
            to_m = np.linalg.inv(to_o)
            gap = min(o.clearance(m.verts @ to_o[:3, :3].T + to_o[:3, 3]),
                      m.clearance(o.verts @ to_m[:3, :3].T + to_m[:3, 3]))
            met[m, o] += gap < 0.0
            if gap < least.get((m, o), (REACH, None))[0]:
                least[m, o] = (gap, label)
    for m, o in pairs:
        gap, label = least.get((m, o), (REACH, None))
        print("GAP %-22s %-22s %s" % (m.name, o.name, "%6.1f mm at %s, met in %d of %d poses" % (gap * 1e3, label, met[m, o], shown)
                                      if label else "over %d mm" % (REACH * 1e3)))

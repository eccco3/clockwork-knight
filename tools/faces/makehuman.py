"""MakeHuman's hand-made face shapes, carried onto the face model's head.

The scans the model is learnt from barely vary in some features people notice at once, such as how far the
nose tip droops or how the nostrils face. MakeHuman's targets (CC0, tools/fetch_assets.ps1) are artists'
shape changes of its base head, one feature each. Its head is laid onto the model's mean: scaled and turned
onto it, then bent onto its surface, coarse to fine. Each vertex of the model then takes a smooth average of
the movements of the bent head's vertices near it that landed on the mean and face its way, so a target
becomes a direction the model's faces can move in, without tearing where the two heads' details differ.

Where the head lies is kept in laid.json: it was laid onto the first lattice's mean, and every lattice since
binds to the same laying, so that each feature keeps its meaning and the dev's answers stay valid. Without
the file the head is laid again, onto this lattice's mean.
"""
import json, os
import numpy as np
from .model import MIRROR, mirrored, normals, twins

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads", "makehuman")
LAID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "laid.json")
BODY = 13380                                   # the base mesh's skin; helper geometry follows
DECIMETRE = 0.1
EYE_Y = 0.0515                                 # the model's eyeball centres stand this far before its origin
FACE = dict(front=0.015, top=0.06, bottom=-0.135)   # the part of the model's mean the heads are matched over
LANDED = 0.0015                                # MakeHuman vertices that didn't land this close to the mean carry nothing
REACH = 0.8                                    # a model vertex takes the movements of those about this many of
                                               # their edges' mean length near it,
FADE = 2.0                                     # fading out where they are fewer than within this many REACHes,
NEIGHBOURS = 48                                # from at most this many,
FACING = 0.5                                   # facing its way to within 60 degrees
CHUNK = 2048
# The shapes the model's faces take: the targets each sums, as stems that end one way for more and the other
# for less, and the share of MakeHuman's full slider that is one unit of it, about as far as people commonly
# differ. Left out are the targets the scans' components already span (the whole nose, mouth or head moved
# or scaled, the chin's height), those that all but repeat one kept here, and the eyes': the model's lids
# end in edge loops on its eyeballs, which those tear before they move them far enough to see.
SHAPES = {
    "nose tip up": (("nose/nose-point",), "up", "down", 0.6),
    "septum low": (("nose/nose-septumangle",), "incr", "decr", 0.6),
    "nostrils flared": (("nose/nose-flaring",), "incr", "decr", 0.6),
    "nostrils wide": (("nose/nose-nostrils-width",), "incr", "decr", 0.6),
    "bridge wide": (("nose/nose-width1", "nose/nose-width2"), "incr", "decr", 0.7),
    "nose tip wide": (("nose/nose-point-width", "nose/nose-volume"), "incr", "decr", 0.8),
    "nose convex": (("nose/nose-curve",), "convex", "concave", 0.4),
    "nose root full": (("nose/nose-greek",), "incr", "decr", 1.0),
    "upper lip full": (("mouth/mouth-upperlip-volume",), "incr", "decr", 0.8),
    "lower lip full": (("mouth/mouth-lowerlip-volume",), "incr", "decr", 0.8),
    "upper lip tall": (("mouth/mouth-upperlip-height",), "incr", "decr", 0.6),
    "lower lip tall": (("mouth/mouth-lowerlip-height",), "incr", "decr", 0.6),
    "mouth wide": (("mouth/mouth-scale-horiz",), "incr", "decr", 0.4),
    "mouth corners up": (("mouth/mouth-angles",), "up", "down", 0.4),
    "chin wide": (("chin/chin-width",), "incr", "decr", 0.5),
    "jaw wide": (("chin/chin-bones",), "incr", "decr", 0.5),
    "jaw corners low": (("chin/chin-jaw-drop",), "incr", "decr", 0.8),
    "cheekbones": (("cheek/l-cheek-bones", "cheek/r-cheek-bones"), "incr", "decr", 0.5),
    "cheeks full": (("cheek/l-cheek-inner", "cheek/r-cheek-inner"), "incr", "decr", 0.7),
    "brow ridge slanted up": (("eyebrows/eyebrows-angle",), "up", "down", 0.6),
    "forehead rounded": (("forehead/forehead-nubian",), "incr", "decr", 0.55),
    "temples full": (("forehead/forehead-temple",), "incr", "decr", 0.5),
}


def _read():
    v, quads, eyes = [], [], {}
    group = None
    with open(os.path.join(FOLDER, "3dobjs", "base.obj")) as f:
        for line in f:
            if line.startswith("v "):
                v.append(line.split()[1:4])
            elif line.startswith("g "):
                group = line.split()[1]
            elif line.startswith("f "):
                corners = [int(c.split("/")[0]) - 1 for c in line.split()[1:]]
                if group == "body":
                    quads.append(corners)
                elif group in ("joint-l-eye", "joint-r-eye"):
                    eyes.setdefault(group, set()).update(corners)
    v = np.array(v, dtype=np.float64)
    eye = np.mean([v[sorted(i)].mean(0) for i in eyes.values()], 0)
    return v[:BODY], np.array(quads)[:, ::-1], eye                  # wound for the model's frame, a mirror of its own


def _frame(p):
    """MakeHuman's frame (y up, z out of the face, decimetres) in the model's (+y out, +z up, metres)."""
    return p[..., [0, 2, 1]] * DECIMETRE


def target(name):
    """A target's movement of every base vertex, in the model's frame and MakeHuman's scale."""
    d = np.zeros((BODY, 3))
    with open(os.path.join(FOLDER, "targets", name + ".target")) as f:
        for line in f:
            if line.strip() and not line.startswith("#"):
                i, x, y, z = line.split()
                if int(i) < BODY:                   # not the helper geometry (lashes, teeth), which the model lacks
                    d[int(i)] = float(x), float(y), float(z)
    return _frame(d)


def _nearest(p, q):
    """Index of the point of q nearest each point of p."""
    return np.concatenate([np.argmin(((p[k:k + CHUNK, None] - q[None]) ** 2).sum(-1), 1) for k in range(0, len(p), CHUNK)])


def _similarity(p, q):
    """Scale s, rotation R and shift t minimising |s R p + t - q|."""
    mp, mq = p.mean(0), q.mean(0)
    u, sv, vt = np.linalg.svd((q - mq).T @ (p - mp))
    flip = np.diag([1.0, 1.0, np.sign(np.linalg.det(u @ vt))])
    R = u @ flip @ vt
    s = (sv * np.diag(flip)).sum() / ((p - mp) ** 2).sum()
    return s, R, mq - s * R @ mp


def _smooth(field, weight, edges, rounds):
    """Normalised averaging over the mesh's edges: field spread from where weight is."""
    f, w = field * weight[:, None], weight.copy()
    for _ in range(rounds):
        for a, b in (edges, edges[::-1]):
            nf, nw = f.copy(), w.copy()
            np.add.at(nf, a, f[b]); np.add.at(nw, a, w[b])
        count = np.bincount(edges.ravel(), minlength=len(w)) + 1.0
        f, w = nf / count[:, None], nw / count
    return f / np.maximum(w, 1e-9)[:, None]


def lay(raw, quads, eye, mean):
    """MakeHuman's base vertices raw, wound into quads, laid onto the model's mean head: the scale and the turn
    taking its movements into the model's frame, the vertices that landed on the mean (LANDED), where they
    lie, which way they face and how far each reaches (REACH)."""
    p = _frame(raw - eye)
    p[:, 1] += EYE_Y
    surface = mean[_on_face(mean)]
    head = np.where(p[:, 2] > FACE["bottom"] - 0.03)[0]
    mine = _on_face(p[head])

    s, R, few = 1.0, np.eye(3), surface[::4]
    for _ in range(30):                                 # scaled and turned onto the mean, matched both ways
        q = p[head][mine]
        a = np.concatenate([q, q[_nearest(few, q)]])
        b = np.concatenate([few[_nearest(q, few)], few])
        s1, R1, t1 = _similarity(np.concatenate([a, a * MIRROR]), np.concatenate([b, b * MIRROR]))
        p = s1 * p @ R1.T + t1
        s, R = s * s1, R1 @ R

    edges = np.unique(np.sort(np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)]), 1), axis=0)
    index = np.full(BODY, -1)
    index[head] = np.arange(len(head))
    edges = index[edges]
    edges = edges[(edges >= 0).all(1)].T
    x = p[head]
    for rounds in (64, 32, 16, 8, 4, 2, 1):             # then bent onto it, coarse to fine
        for _ in range(4):
            gap = surface[_nearest(x, surface)] - x
            weight = (mine & (np.linalg.norm(gap, axis=1) < 0.012)).astype(float)
            x = x + _smooth(gap, weight, edges, rounds)
    p[head] = x
    gap = np.linalg.norm(surface[_nearest(x[mine], surface)] - x[mine], axis=1)
    landed = head[mine][gap < LANDED]
    sides = np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)])
    length = np.linalg.norm(p[sides[:, 0]] - p[sides[:, 1]], axis=1)
    reach = REACH * np.bincount(sides[:, 0], length, BODY) / np.maximum(np.bincount(sides[:, 0], minlength=BODY), 1)
    return s, R, landed, p[landed], normals(p, quads)[landed], reach[landed]


def keep(scale, turn, landed, at, facing, reach):
    """Writes laid.json: the scale and the turn, and a landed vertex to a row: its index, where it lies, which
    way it faces and its reach."""
    rows = ",\n".join("  [%d, %s]" % (i, ", ".join("%.7g" % x for x in np.concatenate([a, f, [r]])))
                      for i, a, f, r in zip(landed, at, facing, reach))
    with open(LAID, "w", encoding="utf-8", newline="\n") as f:
        f.write('{"scale": %r,\n"turn": %s,\n"landed": [\n%s]}\n'
                % (float(scale), json.dumps(np.asarray(turn).tolist()), rows))


class Fit:
    """MakeHuman's head as laid.json lays it on the model's mean (lay): the scale and turn taking its movements
    into the model's frame, the base vertices that landed on the mean, where they lie, which way they face and
    how far each reaches; and each model vertex's place among them."""

    def __init__(self, model):
        raw, quads, eye = _read()
        self.twin = twins(raw)
        if not os.path.exists(LAID):
            keep(*lay(raw, quads, eye, model.mean))
        with open(LAID, encoding="utf-8") as f:
            laid = json.load(f)
        rows = np.array(laid["landed"])
        self.scale, self.turn = laid["scale"], np.array(laid["turn"])
        self.landed, self.at, self.facing, self.reach = rows[:, 0].astype(int), rows[:, 1:4], rows[:, 4:7], rows[:, 7]
        self.bind(model)

    def carry(self, movement):
        """A movement of MakeHuman's base vertices (BODY, 3), made symmetric, as one of the model's vertices."""
        movement = mirrored(movement, self.twin) * self.scale @ self.turn.T
        return (self.weights[:, :, None] * movement[self.neighbours]).sum(1)

    def bind(self, model):
        """For each model vertex, the MakeHuman vertices and the weights it averages their movements with."""
        mean, normal = model.mean, normals(model.mean, model.quads)
        x, n, reach = self.at, self.facing, self.reach
        neighbours = np.zeros((len(mean), NEIGHBOURS), int)
        weights = np.zeros((len(mean), NEIGHBOURS))
        for k in range(0, len(mean), 1024):
            pts = mean[k:k + 1024]
            d = ((pts[:, None] - x[None]) ** 2).sum(-1)
            few = np.argpartition(d, NEIGHBOURS, axis=1)[:, :NEIGHBOURS]
            w = np.exp(-np.take_along_axis(d, few, 1) / (2 * reach[few] ** 2))
            w *= np.clip(((n[few] * normal[k:k + 1024, None]).sum(-1) - FACING) / (1 - FACING), 0, 1)
            neighbours[k:k + 1024] = self.landed[few]
            weights[k:k + 1024] = w / (w.sum(1, keepdims=True) + np.exp(-FADE ** 2 / 2))
        self.neighbours, self.weights = neighbours, weights


def _on_face(p):
    return (p[:, 1] > FACE["front"]) & (p[:, 2] < FACE["top"]) & (p[:, 2] > FACE["bottom"])


def shapes(fit):
    """SHAPES as a Fit carries them onto the model: their names and each one's movement of the model's
    vertices (F, N, 3), in metres per unit."""
    def end(stem, way):
        return fit.carry(target("%s-%s" % (stem, way)))
    return list(SHAPES), np.stack([0.5 * unit * sum(end(stem, more) - end(stem, less) for stem in stems)
                                   for stems, more, less, unit in SHAPES.values()])

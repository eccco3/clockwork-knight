"""MakeHuman's hand-made face shapes, carried onto the face model's head.

The scans the model is learnt from barely vary in some features people notice at once, such as how far the
nose tip droops or how the nostrils face. MakeHuman's targets (CC0, tools/fetch_assets.ps1) are artists'
shape changes of its base head, one feature each. Its head is laid onto the model's mean: scaled and turned
onto it, then bent onto its surface, coarse to fine. Each vertex of the model then takes a smooth average of
the movements of the bent head's vertices near it that landed on the mean and face its way, so a target
becomes a direction the model's faces can move in, without tearing where the two heads' details differ.
"""
import os
import numpy as np
from .model import MIRROR, mirrored, normals, twins

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads", "makehuman")
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


class Fit:
    """MakeHuman's head laid onto the model's mean: its base vertices where they landed (BODY, 3), the
    scale and turn taking its movements into the model's frame, how far its face landed from the mean's
    (gap), and each model vertex's place on it: a triangle of base vertices and weights, if one is near."""

    def __init__(self, model):
        raw, quads, eye = _read()
        self.twin = twins(raw)
        p = _frame(raw - eye)
        p[:, 1] += EYE_Y
        mean = model.mean
        surface = mean[_on_face(mean)]
        head = np.where(p[:, 2] > FACE["bottom"] - 0.03)[0]
        mine = _on_face(p[head])

        s, R, few = 1.0, np.eye(3), surface[::4]
        for _ in range(30):                             # scaled and turned onto the mean, matched both ways
            q = p[head][mine]
            a = np.concatenate([q, q[_nearest(few, q)]])
            b = np.concatenate([few[_nearest(q, few)], few])
            s1, R1, t1 = _similarity(np.concatenate([a, a * MIRROR]), np.concatenate([b, b * MIRROR]))
            p = s1 * p @ R1.T + t1
            s, R = s * s1, R1 @ R
        self.scale, self.turn = s, R

        edges = np.unique(np.sort(np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)]), 1), axis=0)
        index = np.full(BODY, -1)
        index[head] = np.arange(len(head))
        edges = index[edges]
        edges = edges[(edges >= 0).all(1)].T
        x = p[head]
        for rounds in (64, 32, 16, 8, 4, 2, 1):         # then bent onto it, coarse to fine
            for _ in range(4):
                gap = surface[_nearest(x, surface)] - x
                weight = (mine & (np.linalg.norm(gap, axis=1) < 0.012)).astype(float)
                x = x + _smooth(gap, weight, edges, rounds)
        p[head] = x
        self.verts = p
        self.gap = np.linalg.norm(surface[_nearest(x[mine], surface)] - x[mine], axis=1)

        self.quads = quads
        self.landed = np.zeros(BODY, bool)
        self.landed[head[mine]] = self.gap < LANDED
        self.bind(model)

    def carry(self, movement):
        """A movement of MakeHuman's base vertices (BODY, 3), made symmetric, as one of the model's vertices."""
        movement = mirrored(movement, self.twin) * self.scale @ self.turn.T
        return (self.weights[:, :, None] * movement[self.neighbours]).sum(1)

    def bind(self, model):
        """For each model vertex, the MakeHuman vertices and the weights it averages their movements with."""
        mean, normal = model.mean, normals(model.mean, model.quads)
        source = np.where(self.landed)[0]
        x, n = self.verts[source], normals(self.verts, self.quads)[source]
        edges = np.concatenate([self.quads[:, [k, (k + 1) % 4]] for k in range(4)])
        length = np.linalg.norm(self.verts[edges[:, 0]] - self.verts[edges[:, 1]], axis=1)
        reach = REACH * (np.bincount(edges[:, 0], length, BODY) / np.maximum(np.bincount(edges[:, 0], minlength=BODY), 1))[source]
        neighbours = np.zeros((len(mean), NEIGHBOURS), int)
        weights = np.zeros((len(mean), NEIGHBOURS))
        for k in range(0, len(mean), 1024):
            pts = mean[k:k + 1024]
            d = ((pts[:, None] - x[None]) ** 2).sum(-1)
            few = np.argpartition(d, NEIGHBOURS, axis=1)[:, :NEIGHBOURS]
            w = np.exp(-np.take_along_axis(d, few, 1) / (2 * reach[few] ** 2))
            w *= np.clip(((n[few] * normal[k:k + 1024, None]).sum(-1) - FACING) / (1 - FACING), 0, 1)
            neighbours[k:k + 1024] = source[few]
            weights[k:k + 1024] = w / (w.sum(1, keepdims=True) + np.exp(-FADE ** 2 / 2))
        self.neighbours, self.weights = neighbours, weights


def _on_face(p):
    return (p[:, 1] > FACE["front"]) & (p[:, 2] < FACE["top"]) & (p[:, 2] > FACE["bottom"])

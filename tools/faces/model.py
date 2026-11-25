"""The morphable model of human faces: a mean head, uncorrelated shape components, and hand-made features.

A face is the mean plus the components weighted by its coefficients, which are independent and unit normal
over the people the model was learnt from; `sample` draws them closer to the mean than that. The scans
vary little in some features people notice at once, so the coefficients go on to weigh hand-made shapes of
those (makehuman.py), each in units of about what people commonly differ by. Coefficients left off the end
are zero, so a face written before a feature was added is still that face. Every such face is symmetric;
`lopsided` adds the slight ways the scanned heads' two halves differ, which no coefficient holds. A face
has the topology `fit.py` gave the mean, a lattice wrapped by the sculpt toolkit's mesher, in the head
frame the figures sculpt in: +y out of the face, +z up, metres.
"""
import os
import numpy as np

SPREAD = 0.65                                  # faces are drawn at this share of the people's standard deviation
KEEP = 0.999                                   # the components kept explain this share of the variance
MIRROR = np.array([-1.0, 1.0, 1.0])


def mirrored(x, twin):
    """Shapes (..., N, 3) averaged with their mirror images; twin: each vertex's partner across the midline."""
    return 0.5 * (x + x[..., twin, :] * MIRROR)


def twins(v):
    """Each vertex's partner across the midline of a symmetric mesh: the vertex nearest its mirror image."""
    image = v * MIRROR
    twin = np.concatenate([np.linalg.norm(image[k:k + 256, None] - v[None], axis=-1).argmin(1) for k in range(0, len(v), 256)])
    assert (twin[twin] == np.arange(len(v))).all(), "the mesh is not symmetric"
    return twin


def principal(modes, keep=KEEP):
    """Principal components of the heads spanned by modes (M, N, 3) with independent unit normal weights,
    largest first, each scaled to one standard deviation: how each mixes the modes (K, M), and the share of
    the variance each explains."""
    flat = modes.reshape(len(modes), -1)
    variance, turn = np.linalg.eigh(flat @ flat.T)
    variance, turn = variance[::-1], turn[:, ::-1]
    share = variance / variance.sum()
    count = int(np.searchsorted(np.cumsum(share), keep)) + 1
    return turn[:, :count].T, share[:count]


def normals(v, quads):
    """Vertex normals of a quad mesh, weighted by the area of the quads round each vertex."""
    n = np.zeros_like(v)
    across = np.cross(v[quads[:, 2]] - v[quads[:, 0]], v[quads[:, 3]] - v[quads[:, 1]])
    for k in range(4):
        np.add.at(n, quads[:, k], across)
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


class Model:
    """mean (N, 3), components (K, N, 3) in metres per standard deviation, share (K,) of the variance each
    explains, and the lattice the vertices lie on: quads (Q, 4) and lattice points lat (N, 3). Then the
    features (F, N, 3), in metres per unit, with their names, and the asymmetries (A, N, 3), the largest
    first, in metres per standard deviation of the scanned heads; fitted is the version of fit.py that
    made the lattice, and eyes (N,) which of its vertices lie on the eyeballs, between the lids."""

    def __init__(self, mean, components, share, quads, lat, asymmetries=None, names=(), features=None, fitted=1,
                 eyes=None):
        blank = np.zeros((0,) + mean.shape)
        self.mean, self.share, self.quads, self.lat, self.fitted, self.eyes = mean, share, quads, lat, fitted, eyes
        self.asymmetries = blank if asymmetries is None else asymmetries
        self.names, self.directions = list(names), np.concatenate([components, blank if features is None else features])

    @property
    def components(self):
        return self.directions[:len(self.share)]

    @property
    def features(self):
        return self.directions[len(self.share):]

    def sample(self, rng, spread=SPREAD):
        """The coefficients on the components of a random face."""
        return rng.normal(0.0, spread, len(self.share))

    def shape(self, coefficients, lopsided=()):
        """A face's vertices; `lopsided` weighs the first of the asymmetries."""
        weights = np.asarray(coefficients, float)[:len(self.directions)]
        return (self.mean + np.tensordot(weights, self.directions[:len(weights)], axes=1)
                + np.tensordot(np.asarray(lopsided, float), self.asymmetries[:len(lopsided)], axes=1))

    def mesh(self, coefficients, lopsided=()):
        """A face as a piece's mesh: verts, quads, normals and lattice points."""
        v = self.shape(coefficients, lopsided)
        return v, self.quads, normals(v, self.quads), self.lat

    def save(self, path):
        """Writes the model whole or not at all, since the rating tool may be reading it."""
        with open(path + ".part", "wb") as f:
            np.savez_compressed(f, mean=self.mean.astype(np.float32), components=self.components.astype(np.float32),
                                share=self.share, quads=self.quads.astype(np.int32), lat=self.lat.astype(np.int32),
                                asymmetries=self.asymmetries.astype(np.float32), names=np.array(self.names, dtype=str),
                                features=self.features.astype(np.float32), fitted=self.fitted, eyes=self.eyes)
        os.replace(path + ".part", path)

    @classmethod
    def load(cls, path):
        with np.load(path) as f:
            more = [f[key].astype(np.float64) if key in f.files else None for key in ("asymmetries", "features")]
            return cls(f["mean"].astype(np.float64), f["components"].astype(np.float64), f["share"],
                       f["quads"].astype(np.int64), f["lat"].astype(np.int64), more[0],
                       f["names"].tolist() if "names" in f.files else (), more[1],
                       int(f["fitted"]) if "fitted" in f.files else 1, f["eyes"] if "eyes" in f.files else None)

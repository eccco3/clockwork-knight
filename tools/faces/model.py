"""The morphable model of human faces: a mean head and uncorrelated shape components.

A face is the mean plus the components weighted by its coefficients, which are independent and unit normal
over the people the model was learnt from; `sample` draws them closer to the mean than that. Every face is
symmetric and has the topology `fit.py` gave the mean, a lattice wrapped by the sculpt toolkit's mesher,
in the head frame the figures sculpt in: +y out of the face, +z up, metres.
"""
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


def components(modes, keep=KEEP):
    """Principal components of the heads spanned by modes (M, N, 3) with independent unit normal weights,
    largest first, each scaled to one standard deviation, and the share of the variance each explains."""
    flat = modes.reshape(len(modes), -1)
    variance, turn = np.linalg.eigh(flat @ flat.T)
    variance, turn = variance[::-1], turn[:, ::-1]
    share = variance / variance.sum()
    count = int(np.searchsorted(np.cumsum(share), keep)) + 1
    return (turn[:, :count].T @ flat).reshape(count, *modes.shape[1:]), share[:count]


def normals(v, quads):
    """Vertex normals of a quad mesh, weighted by the area of the quads round each vertex."""
    n = np.zeros_like(v)
    across = np.cross(v[quads[:, 2]] - v[quads[:, 0]], v[quads[:, 3]] - v[quads[:, 1]])
    for k in range(4):
        np.add.at(n, quads[:, k], across)
    return n / np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]


class Model:
    """mean (N, 3), components (K, N, 3) in metres per standard deviation, share (K,) of the variance each
    explains, and the lattice the vertices lie on: quads (Q, 4) and lattice points lat (N, 3)."""

    def __init__(self, mean, components, share, quads, lat):
        self.mean, self.components, self.share, self.quads, self.lat = mean, components, share, quads, lat

    def sample(self, rng, spread=SPREAD):
        """Coefficients of a random face."""
        return rng.normal(0.0, spread, len(self.components))

    def shape(self, coefficients):
        return self.mean + np.tensordot(coefficients, self.components, axes=1)

    def mesh(self, coefficients):
        """A face as a piece's mesh: verts, quads, normals and lattice points."""
        v = self.shape(coefficients)
        return v, self.quads, normals(v, self.quads), self.lat

    def save(self, path):
        np.savez_compressed(path, mean=self.mean.astype(np.float32), components=self.components.astype(np.float32),
                            share=self.share, quads=self.quads.astype(np.int32), lat=self.lat.astype(np.int32))

    @classmethod
    def load(cls, path):
        with np.load(path) as f:
            return cls(f["mean"].astype(np.float64), f["components"].astype(np.float64), f["share"],
                       f["quads"].astype(np.int64), f["lat"].astype(np.int64))

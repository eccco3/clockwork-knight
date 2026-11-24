"""The female-male direction in the face model's coefficients, and faces drawn on either side of it.

ICT-FaceKit's scans carry no sex labels, so the direction is measured. Landmarks are found on the mean
head, and between them distances that are larger in men than in women: brow ridge and forehead slope,
the widths of cheekbones, jaw and neck, the heights of face, chin and nose, and the nose's width and
protrusion. Each is linear in the coefficients, so it grows along one direction in them; the measures'
correlations over the people are those directions' cosines. The female-male direction is the measures'
common factor, their correlations' first principal component, and every measure loads on it in the
male sense. One unit along it is one standard deviation of the people toward men.

  python -I sexes.py        each measure's correlation with the direction, and the components it is made of
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces.model import Model, SPREAD

SEXES = {"women": -1.0, "men": 1.0}            # each sex's side of the direction
MARGIN = 0.8                                   # a sex's faces lie at least this far along the direction on its side
X, Y, Z = 0, 1, 2
ANY = (-1.0, 1.0)
# Landmarks on the mean in the head frame (see model.py), each the vertex furthest along `axis`, in
# direction `sign`, within a box: x on the midline or on +x, y and z ranges.
LANDMARKS = dict(
    glabella=(Y, +1, "mid", (0.05, 1.0), (0.010, 0.040)),
    nasion=(Y, -1, "mid", (0.05, 1.0), (-0.010, 0.015)),
    forehead=(Y, +1, "mid", ANY, (0.055, 0.060)),
    pronasale=(Y, +1, "mid", (0.05, 1.0), (-0.060, 0.0)),
    subnasale=(Y, -1, "mid", (0.05, 1.0), (-0.060, -0.040)),
    stomion=(Y, -1, "mid", (0.05, 1.0), (-0.080, -0.065)),
    menton=(Z, -1, "mid", (0.04, 1.0), ANY),
    zygion=(X, +1, "side", (0.02, 0.06), (-0.030, 0.0)),
    gonion=(X, +1, "side", (0.0, 0.03), (-0.110, -0.090)),
    jaw=(X, +1, "side", (0.03, 0.05), (-0.100, -0.085)),
    alare=(X, +1, "side", (0.07, 1.0), (-0.050, -0.030)),
    neck=(X, +1, "side", (-0.02, 0.02), (-0.145, -0.135)),
)
# Each measure is landmark a minus landmark b, or a alone (a half width), along an axis.
MEASURES = (
    ("brow ridge", "glabella", "nasion", Y),
    ("forehead slope", "glabella", "forehead", Y),
    ("cheekbone width", "zygion", None, X),
    ("jaw angle width", "gonion", None, X),
    ("jaw width", "jaw", None, X),
    ("face height", "nasion", "menton", Z),
    ("chin height", "stomion", "menton", Z),
    ("nose height", "nasion", "subnasale", Z),
    ("nose width", "alare", None, X),
    ("nose protrusion", "pronasale", "subnasale", Y),
    ("neck width", "neck", None, X),
)


def landmarks(mean):
    """Each landmark's vertex on the mean."""
    found = {}
    for name, (axis, sign, x, y, z) in LANDMARKS.items():
        inside = (np.abs(mean[:, X]) < 1e-4) if x == "mid" else (mean[:, X] > 0)
        for a, (low, high) in ((Y, y), (Z, z)):
            inside &= (mean[:, a] >= low) & (mean[:, a] <= high)
        index = np.flatnonzero(inside)
        assert len(index), "no vertex for the landmark " + name
        found[name] = index[np.argmax(sign * mean[index, axis])]
    return found


def measures(model):
    """Each measure's growth per unit of each coefficient (M, K)."""
    at = landmarks(model.mean)
    rows = []
    for _, a, b, axis in MEASURES:
        g = model.components[:, at[a], axis]
        rows.append(g - model.components[:, at[b], axis] if b else g)
    return np.array(rows)


def direction(model):
    """The unit female-male direction in the coefficients, toward men, and each measure's correlation with it."""
    unit = measures(model)
    unit /= np.linalg.norm(unit, axis=1, keepdims=True)
    factor = np.linalg.eigh(unit @ unit.T)[1][:, -1]
    d = unit.T @ (factor * np.sign(factor.sum()))
    d /= np.linalg.norm(d)
    return d, unit @ d


class Sex:
    """The faces of one sex: drawn as the model draws them, but with their place along the female-male
    direction folded onto the sex's side and moved MARGIN further out, so the spread is otherwise the same."""

    def __init__(self, model, name):
        self.model, self.name, self.side = model, name, SEXES[name]
        self.direction = direction(model)[0]

    def sample(self, rng, spread=SPREAD):
        c = self.model.sample(rng, spread)
        along = c @ self.direction
        return c + (self.side * (MARGIN + abs(along)) - along) * self.direction


if __name__ == "__main__":
    model = Model.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.npz"))
    d, loading = direction(model)
    for (name, *_), r in zip(MEASURES, loading):
        print("%-16s %+.2f" % (name, r))
    order = np.argsort(-np.abs(d))[:8]
    print("components:", ", ".join("%d %+.2f" % (k, d[k]) for k in order))

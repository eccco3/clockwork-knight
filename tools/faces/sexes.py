"""The female-male direction in the face model's coefficients, learnt from the dev's labels, and faces drawn
on either side of it.

He labels the label set, LABEL_COUNT random faces drawn at the people's full spread so that both sexes
show, woman, androgynous, man or unclear (dev/labels.tscn); every answer goes to labels.jsonl at once. A
logistic regression over the coefficients and a constant learns from them the odds that he calls a face a
man rather than a woman: androgynous counts as even odds, so those faces mark the middle, and unclear
ones are left out. Its prior is isotropic in shape (logistic.shape_prior). The direction is the weights'
unit vector, toward men, so one unit along it is one standard deviation of the people; the middle is
where the odds are even.

A sex's faces are drawn as the model draws them, but with their place along the direction folded onto the
sex's side and moved MARGIN further out, so that they vary as much as before in every other way.

  python -I sexes.py      what the labels teach: the direction, its middle, and where the pools lie on it

Once he has labelled, one command rebuilds both pools from the labels (taste.py; about 50 minutes):

  toolchain\\blender\\blender.exe --background --python tools/faces/build_faces.py -- --pool
"""
import os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces.files import HERE, Log
from faces.logistic import Posterior, shape_prior, sigmoid
from faces.model import Model, SPREAD

SEXES = {"women": -1.0, "men": 1.0}            # each sex's side of the direction
MARGIN = 1.2                                   # a sex's faces lie at least this far from the middle on its side
LABELS = os.path.join(HERE, "labels.jsonl")
KINDS = {"woman": 0.0, "androgynous": 0.5, "man": 1.0, "unclear": None}    # the odds each label gives a man
LABEL_SEED, LABEL_COUNT, LABEL_SPREAD = 11, 120, 1.0
LABEL_LOGIT = 3.0                              # the prior's spread of the logit over the label set
MIDDLE_LOGIT = 3.0                             # and of the logit at the model's mean face
FEWEST = 20                                    # labels of a sex or androgynous needed to learn the direction


def label_set(model):
    """Coefficients of the faces the dev labels."""
    rng = np.random.default_rng(LABEL_SEED)
    return np.stack([model.sample(rng, LABEL_SPREAD) for _ in range(LABEL_COUNT)])


class Labels(Log):
    """The labels file: each line is one label, {"face"} its index in the label set, its "coefficients",
    "label" one of KINDS, "seconds" he took and "at", the time."""

    def label(self, face, coefficients, label, seconds):
        self.add(dict(face=int(face), label=label, coefficients=np.round(coefficients, 5).tolist(),
                      seconds=round(seconds, 2), at=time.strftime("%Y-%m-%dT%H:%M:%S")))

    def counts(self):
        return {kind: sum(line["label"] == kind for line in self.lines) for kind in KINDS}

    def judged(self):
        """The coefficients (N, K) of the faces labelled anything but unclear, and the odds each was called a man."""
        lines = [line for line in self.lines if KINDS[line["label"]] is not None]
        return (np.array([line["coefficients"] for line in lines], float).reshape(len(lines), -1),
                np.array([KINDS[line["label"]] for line in lines], float))


class Direction:
    """What the labels teach: the unit direction toward men, the middle along it, and the slope, the logit's
    growth per unit along it."""

    def __init__(self, share, labels):
        faces, odds = labels.judged()
        if len(faces) < FEWEST:
            sys.exit("%d faces are labelled woman, androgynous or man; the direction needs %d. Label them with "
                     "the playtest launcher's Face labels." % (len(faces), FEWEST))
        prior = np.append(shape_prior(share, LABEL_LOGIT / LABEL_SPREAD), MIDDLE_LOGIT ** 2)
        self.posterior = Posterior(prior, np.hstack([faces, np.ones((len(faces), 1))]), odds)
        w, constant = self.posterior.mean[:-1], self.posterior.mean[-1]
        self.slope = np.linalg.norm(w)
        self.unit, self.middle = w / self.slope, -constant / self.slope

    def along(self, coefficients):
        """Places along the direction, from the middle, in standard deviations of the people."""
        return coefficients @ self.unit - self.middle

    def man(self, coefficients):
        """The odds he would call each face a man rather than a woman."""
        return sigmoid(self.slope * self.along(coefficients))


class Sex:
    """The faces of one sex: drawn as the model draws them, but with their place along the female-male
    direction folded onto the sex's side and moved MARGIN further out, so the spread is otherwise the same."""

    def __init__(self, model, name, labels=LABELS):
        self.model, self.name, self.side = model, name, SEXES[name]
        self.direction = Direction(model.share, Labels(labels))

    def sample(self, rng, spread=SPREAD):
        c = self.model.sample(rng, spread)
        along = self.direction.along(c)
        return c + (self.side * (MARGIN + abs(along)) - along) * self.direction.unit


def report(model, labels, pools):
    """What the labels teach, and where each sex's faces, coefficients in `pools`, lie along the direction."""
    print("labels:", ", ".join("%s %d" % kv for kv in labels.counts().items()))
    d = Direction(model.share, labels)
    print("slope %.2f logits per standard deviation, middle %+.2f, direction settled %.3f" % (
        d.slope, d.middle, d.posterior.settled(np.random.default_rng(0), slice(0, -1))))
    print("components:", ", ".join("%d %+.2f" % (k, d.unit[k]) for k in np.argsort(-np.abs(d.unit))[:8]))
    for name, faces in pools.items():
        along, own = d.along(faces), d.man(faces) if SEXES[name] > 0 else 1.0 - d.man(faces)
        print("%-6s along %+.2f to %+.2f, mean %+.2f; called %s: least %.2f, mean %.2f" % (
            name, along.min(), along.max(), along.mean(), name, own.min(), own.mean()))


if __name__ == "__main__":
    from faces import taste
    model = Model.load(os.path.join(HERE, "model.npz"))
    labels = Labels(sys.argv[1] if len(sys.argv) > 1 else LABELS)
    report(model, labels, {name: taste.pool(Sex(model, name, labels.path)) for name in SEXES})

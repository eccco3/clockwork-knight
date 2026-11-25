"""The dev's taste in faces, learnt from his choices between pairs of them (numpy only).

A Bradley-Terry model over the face model's coefficients: he prefers face a to face b with probability
sigmoid(w . (a - b)), a logistic regression (logistic.py) whose prior is isotropic in shape, scaled so that
two random faces differ by about PRIOR_LOGIT. His first CLEAR pairs are the clearest: of random pairs of
faces not yet shown, those he is expected to prefer one of most strongly, or, before he has answered, the
most different. After that each next pair is the one whose answer is expected to tell the most about w
(BALD), which is soon one near even; about REPEAT of them instead re-show an earlier pair, sides swapped,
to measure his consistency.

Women's and men's faces are rated apart, each sex with its own pool of faces and answers file. The pools
are drawn from the labels (sexes.py); answers given on an earlier pool are discarded with it.
"""
import os, time
import numpy as np

from .files import HERE, Log, folder, rendered
from .logistic import Posterior, shape_prior
from .sexes import SEXES

POOL_SEED, POOL_SIZE = 7, 240
# The pools' faces are drawn this close to the average face: about half as far as the model draws faces,
# since a face drawn at random in some sixty directions lands far out along many of them at once and looks
# extreme. Their place along the female-male direction is kept (sexes.MARGIN), so they still read as a sex.
POOL_SPREAD = 0.35
PRIOR_LOGIT = 2.0
CLEAR = 20
REPEAT = 0.05
FIRST_REPEAT = 10                              # no pair is re-shown before this many answers
CANDIDATES = 4000


def answers(name):
    """The answers file of the sex of that name ("women" or "men")."""
    return os.path.join(HERE, "taste_%s.jsonl" % name)


def pool(sex, size=POOL_SIZE):
    """Coefficients of the faces of a sex (sexes.Sex) the dev is shown."""
    rng = np.random.default_rng((POOL_SEED, list(SEXES).index(sex.name)))
    return np.stack([sex.sample(rng, POOL_SPREAD) for _ in range(size)])


def load_pool(name):
    """The rendered pool's faces of the sex of that name and the prior on w for them."""
    faces, share, spread = rendered(folder(name))
    return faces, prior(share, spread)


def prior(share, spread):
    """Prior variances of w, for faces drawn at `spread`."""
    return shape_prior(share, PRIOR_LOGIT / (np.sqrt(2) * spread))


def best(posterior, sex, rng, count, draws=4000):
    """The `count` faces, of `draws` random ones of the sex, furthest along the learnt direction, best first:
    faces the pool could hold, with their other features left to chance. Returns their coefficients and the
    logits of his preferring each to the mean face."""
    faces = np.stack([sex.sample(rng, POOL_SPREAD) for _ in range(draws)])
    score = faces @ posterior.mean
    keep = np.argsort(-score)[:count]
    return faces[keep], score[keep]


class Answers(Log):
    """The answers file: each line is one answer, {"left", "right", "winner"} pool indices, the coefficients
    of the winning face "won" and the losing one "lost", "repeat_of" the line it re-asks or null, "seconds"
    he took and "at", the time."""

    def consistency(self):
        """How many re-shown pairs he answered as he did the first time, and how many were re-shown."""
        again = [line for line in self.lines if line["repeat_of"] is not None]
        return sum(line["winner"] == self.lines[line["repeat_of"]]["winner"] for line in again), len(again)

    def posterior(self, prior_var):
        won, lost = ([line[key] for line in self.lines] for key in ("won", "lost"))
        return Posterior(prior_var, np.subtract(won, lost, dtype=float), 1.0)


class Session:
    """A sitting: shows pairs from the pool's faces (coefficients (P, K)) and records the answers."""

    def __init__(self, faces, prior_var, answers, rng):
        self.faces, self.prior_var, self.answers, self.rng = faces, prior_var, answers, rng
        self.posterior = answers.posterior(prior_var)
        self.pair = None

    def repeatable(self):
        """Earlier first-time answers on this pool's faces that have not been re-shown."""
        again = {line["repeat_of"] for line in self.answers.lines}
        return [k for k, line in enumerate(self.answers.lines)
                if line["repeat_of"] is None and k not in again and line["left"] < len(self.faces)
                and line["right"] < len(self.faces)
                and np.allclose(self.faces[line["winner"]], line["won"], atol=1e-3)]

    def candidates(self):
        """Random pairs not asked yet, during the first CLEAR answers of faces not shown yet."""
        i, j = self.rng.integers(0, len(self.faces), (2, CANDIDATES))
        asked = {frozenset((line["left"], line["right"])) for line in self.answers.lines}
        shown = {line[side] for line in self.answers.lines for side in ("left", "right")}
        clear = len(self.answers) < CLEAR
        fresh = np.array([a != b and frozenset((a, b)) not in asked and not (clear and (a in shown or b in shown))
                          for a, b in zip(i, j)])
        return i[fresh], j[fresh]

    def next(self):
        """The next pair: (left, right, repeat_of)."""
        repeatable = self.repeatable() if len(self.answers) >= FIRST_REPEAT else []
        if repeatable and self.rng.random() < REPEAT:
            k = int(self.rng.choice(repeatable))
            line = self.answers.lines[k]
            self.pair = (line["right"], line["left"], k)
            return self.pair
        i, j = self.candidates()
        if len(self.answers) < CLEAR:
            mean, var = self.posterior.logit(self.faces[i] - self.faces[j])
            k = int(np.argmax(mean ** 2 + var))
        else:
            k = int(np.argmax(self.posterior.information(self.faces[i] - self.faces[j])))
        self.pair = (int(i[k]), int(j[k]), None)
        return self.pair

    def answer(self, pick, seconds):
        """Records that he picked the "left" or "right" face of the pair shown."""
        left, right, repeat_of = self.pair
        winner, loser = (left, right) if pick == "left" else (right, left)
        self.answers.add(dict(left=left, right=right, winner=winner, repeat_of=repeat_of,
                              won=np.round(self.faces[winner], 5).tolist(), lost=np.round(self.faces[loser], 5).tolist(),
                              seconds=round(seconds, 2), at=time.strftime("%Y-%m-%dT%H:%M:%S")))
        self.posterior = self.answers.posterior(self.prior_var)

    def undo(self):
        """Takes back the last answer and shows its pair again."""
        line = self.answers.undo()
        if line:
            self.posterior = self.answers.posterior(self.prior_var)
            self.pair = (line["left"], line["right"], line["repeat_of"])
        return self.pair

    def status(self):
        agreed, again = self.answers.consistency()
        return dict(answers=len(self.answers), agreed=agreed, repeats=again,
                    settled=round(self.posterior.settled(self.rng), 3))

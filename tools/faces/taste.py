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

Pool pairs are mostly ordinary faces against ordinary ones, which teach what he dislikes more than what
makes a face he likes better still. So once he has rated the pool, refinement rounds (refine) replace it
with REFINE_SIZE faces each likely to be among his favourites, differing where his taste is still unclear.
Every round's answers join the same file, each line naming its set, and all of them teach w.
"""
import os, time
import numpy as np

from .files import HERE, Log, exists, folder, rendered
from .logistic import Posterior, shape_prior
from .sexes import SEXES

POOL_SEED, POOL_SIZE = 7, 240
# A face drawn at random in all of the model's sixty-odd directions lands far out along many of them at once
# and looks extreme, where a real face is near the average in most ways and distinctive in a few. So a pool's
# face is drawn at BASE of the people's spread in every direction, and at BOLD in FEATURES of the first FROM
# directions, picked at random; the rest hold little a viewer sees. Its place along the female-male direction
# is kept (sexes.MARGIN), so it still reads as a sex.
BASE, BOLD, FEATURES, FROM = 0.30, 0.75, 4, 30
PRIOR_LOGIT = 2.0
CLEAR = 20
REPEAT = 0.05
FIRST_REPEAT = 10                              # no pair is re-shown before this many answers
CANDIDATES = 4000
REFINE_SIZE, REFINE_DRAWS = 60, 500


def answers(name):
    """The answers file of the sex of that name ("women" or "men")."""
    return os.path.join(HERE, "taste_%s.jsonl" % name)


def draw(sex, rng):
    """One face of a sex (sexes.Sex) as the pools hold them: near the average, distinctive in a few ways."""
    spread = np.full(len(sex.model.share), BASE)
    spread[rng.choice(min(FROM, len(spread)), FEATURES, replace=False)] = BOLD
    return sex.sample(rng, spread)


def spread(count):
    """The spread a pool's faces are drawn at along each of `count` directions, on average."""
    bold = min(FROM, count)
    s = np.full(count, BASE)
    s[:bold] = np.sqrt(BASE ** 2 + FEATURES / bold * (BOLD ** 2 - BASE ** 2))
    return s


def pool(sex, size=POOL_SIZE):
    """Coefficients of the faces of a sex (sexes.Sex) the dev is shown."""
    rng = np.random.default_rng((POOL_SEED, list(SEXES).index(sex.name)))
    return np.stack([draw(sex, rng) for _ in range(size)])


def refine_folder(name):
    """Where the latest refinement round of the sex of that name is rendered."""
    return folder(name + "_refine")


def current(name):
    """The set of faces of the sex of that name he rates now, the latest refinement round's or else the
    pool's: its folder, its faces' coefficients, the prior on w and the set's name."""
    where = refine_folder(name) if exists(refine_folder(name)) else folder(name)
    faces, share, _, set_name = rendered(where)
    return where, faces, prior(share, spread(len(share))), set_name


def refine(posterior, sex, rng, size=REFINE_SIZE, draws=REFINE_DRAWS):
    """A refinement round's faces (Thompson sampling): for each, a taste drawn from the posterior and the
    best of `draws` faces of the sex under it. They are faces he likely likes, and differ most where the
    posterior is least sure of his taste, so his answers on them teach what makes the best faces best."""
    faces = []
    for w in rng.multivariate_normal(posterior.mean, posterior.cov, size):
        drawn = np.stack([draw(sex, rng) for _ in range(draws)])
        faces.append(drawn[np.argmax(drawn @ w)])
    return np.stack(faces)


def prior(share, spread):
    """Prior variances of w, for faces drawn at `spread`, one number or one per direction."""
    return shape_prior(share, PRIOR_LOGIT / (np.sqrt(2) * spread))


def best(posterior, sex, rng, count, draws=4000):
    """The `count` faces, of `draws` random ones of the sex, furthest along the learnt direction, best first:
    faces the pool could hold, with their other features left to chance. Returns their coefficients and the
    logits of his preferring each to the mean face."""
    faces = np.stack([draw(sex, rng) for _ in range(draws)])
    score = faces @ posterior.mean
    keep = np.argsort(-score)[:count]
    return faces[keep], score[keep]


class Answers(Log):
    """The answers file: each line is one answer, "set" the set of faces shown (files.rendered; "pool" if
    missing), {"left", "right", "winner"} indices in it, the coefficients of the winning face "won" and the
    losing one "lost", "repeat_of" the line it re-asks or null, "seconds" he took and "at", the time."""

    def consistency(self):
        """How many re-shown pairs he answered as he did the first time, and how many were re-shown."""
        again = [line for line in self.lines if line["repeat_of"] is not None]
        return sum(line["winner"] == self.lines[line["repeat_of"]]["winner"] for line in again), len(again)

    def posterior(self, prior_var):
        won, lost = ([line[key] for line in self.lines] for key in ("won", "lost"))
        return Posterior(prior_var, np.subtract(won, lost, dtype=float), 1.0)


class Session:
    """A sitting: shows pairs from a set of faces (coefficients (P, K)), named `set_name`, and records the
    answers. It learns from every answer in the file, but asks and re-shows pairs of this set only."""

    def __init__(self, faces, prior_var, answers, rng, set_name="pool"):
        self.faces, self.prior_var, self.answers, self.rng, self.set = faces, prior_var, answers, rng, set_name
        self.posterior = answers.posterior(prior_var)
        self.pair = None

    def mine(self, line):
        """Whether an answer was given on this set."""
        return line.get("set", "pool") == self.set

    def repeatable(self):
        """Earlier first-time answers on this set's faces that have not been re-shown."""
        again = {line["repeat_of"] for line in self.answers.lines}
        return [k for k, line in enumerate(self.answers.lines)
                if self.mine(line) and line["repeat_of"] is None and k not in again
                and line["left"] < len(self.faces) and line["right"] < len(self.faces)
                and np.allclose(self.faces[line["winner"]], line["won"], atol=1e-3)]

    def candidates(self):
        """Random pairs not asked yet, during the first CLEAR answers of faces not shown yet."""
        i, j = self.rng.integers(0, len(self.faces), (2, CANDIDATES))
        lines = [line for line in self.answers.lines if self.mine(line)]
        asked = {frozenset((line["left"], line["right"])) for line in lines}
        shown = {line[side] for line in lines for side in ("left", "right")}
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
        self.answers.add(dict(set=self.set, left=left, right=right, winner=winner, repeat_of=repeat_of,
                              won=np.round(self.faces[winner], 5).tolist(), lost=np.round(self.faces[loser], 5).tolist(),
                              seconds=round(seconds, 2), at=time.strftime("%Y-%m-%dT%H:%M:%S")))
        self.posterior = self.answers.posterior(self.prior_var)

    def undo(self):
        """Takes back the last answer, if given on this set, and shows its pair again."""
        if not (self.answers.lines and self.mine(self.answers.lines[-1])):
            return self.pair
        line = self.answers.undo()
        if line:
            self.posterior = self.answers.posterior(self.prior_var)
            self.pair = (line["left"], line["right"], line["repeat_of"])
        return self.pair

    def status(self):
        agreed, again = self.answers.consistency()
        return dict(set=self.set, answers=len(self.answers), agreed=agreed, repeats=again,
                    settled=round(self.posterior.settled(self.rng), 3))

"""The dev's taste in faces, learnt from his choices between pairs of them (numpy only).

A face is its numbers: the face model's coefficients, on the scans' components and then on its hand-made
features (model.py), and then its brow numbers (brows.py). His taste weighs those numbers and their squares
(terms), so that he can like a number best somewhere between its extremes rather than only more or less of
it, which foresaw far more of his answers than the numbers alone. A Bradley-Terry model over them: he
prefers face a to face b with probability sigmoid(w . (terms(a) - terms(b))), a logistic regression
(logistic.py). Its prior on the components is isotropic in shape, scaled so that two random faces differ by
about PRIOR_LOGIT; the features and brows, which move little of the head but are what a viewer looks at,
each get an equal share of NEW times as much again; and each square as much as its number. His first CLEAR pairs are the clearest: of random pairs of faces not yet shown, those
he is expected to prefer one of most strongly, or, before he has answered, the most different. After that
each next pair is the one whose answer is expected to tell the most about w (BALD), which is soon one near
even; about REPEAT of them instead re-show an earlier pair, sides swapped, to measure his consistency.

Women's and men's faces are rated apart, each sex with its own pool of faces and answers file. The pools
are drawn from the labels (sexes.py). An answer holds the numbers of its two faces, so it teaches w
whatever set it was given on, and whatever numbers faces have gained since: those it lacks are zero.

Pool pairs are mostly ordinary faces against ordinary ones, which teach what he dislikes more than what
makes a face he likes better still. So after FIRST or so answers on the pool, refinement rounds (refine)
replace it with REFINE_SIZE faces each likely to be among his favourites, differing where his taste is
still unclear, a new round every ROUND or so answers; the rating tool renders each in the background and
switches to it once rendered (rate.py). Every round's answers join the same file, each line naming its
set, and all of them teach w. simulate.py measures what these choices cost in answers.
"""
import functools, json, os, shutil, sys, time
import numpy as np

from . import brows
from .files import HERE, Log, complete, exists, folder, rendered
from .logistic import Posterior
from .model import Model
from .sexes import SEXES, Sex
from .widths import Widths

POOL, POOL_SEED, POOL_SIZE = "pool 2", 7, 240  # the pool's name in the answers: the second, whose faces have features and brows
# A face drawn at random in all of its numbers lands far out along many of them at once and looks extreme,
# where a real face is near the average in most ways and distinctive in a few. So a pool's face is drawn at
# BASE of the people's spread in every number, and at BOLD in FEATURES of those a viewer sees, picked at
# random: the first FROM components, the features and the brows, none of these two past LIMIT units, about
# the artists' full sliders. Its place along the female-male direction
# is kept (sexes.MARGIN), so it still reads as a sex.
BASE, BOLD, FEATURES, FROM, LIMIT = 0.30, 0.75, 8, 30, 2.0
# Yet a woman's face drawn so can still be broad in jaw, cheeks or head, which reads as a man's whatever her
# place along that direction, and pairs of such faces hide the finer things he judges. So the sexes named
# here keep only faces no broader in any of widths.py's measures than this many standard deviations past
# the average of the faces drawn so, a share of them; the rest are drawn again.
NARROW = {"women": 0.3}
TRIED = 4000                                   # faces drawn to learn how a sex's faces vary
PRIOR_LOGIT, NEW = 2.0, 0.25
CLEAR = 20
REPEAT = 0.05
FIRST_REPEAT = 10                              # no pair is re-shown before this many answers
CANDIDATES = 4000
FIRST, ROUND = 40, 40
REFINE_SIZE, REFINE_DRAWS = 60, 500
RECENT = 40                                    # his latest answers the status tells how many were foreseen of


def answers(name):
    """The answers file of the sex of that name ("women" or "men")."""
    return os.path.join(HERE, "taste_%s.jsonl" % name)


def padded(face, size):
    """A face's numbers at the length faces have now: those it was written without are zero."""
    return np.pad(np.asarray(face, float), (0, size - len(face)))


def terms(faces):
    """What his taste weighs of faces (..., n): their numbers, then their squares."""
    faces = np.asarray(faces, float)
    return np.concatenate([faces, faces ** 2], -1)


def shares(model):
    """The share of his taste each of a face's numbers is expected to hold, as the prior has it: the
    components', by the variance each explains, sum to one, and the features and brows' to NEW."""
    new = len(model.names) + len(brows.NAMES)
    return np.concatenate([model.share / model.share.sum(), np.full(new, NEW / new)])


def seen(model):
    """Which of a face's numbers a pool's face may be bold in."""
    return np.r_[:min(FROM, len(model.share)), len(model.share):len(shares(model))]


def spread(model):
    """The spread a pool's faces are drawn at in each number, on average."""
    s, bold = np.full(len(shares(model)), BASE), seen(model)
    s[bold] = np.sqrt(BASE ** 2 + FEATURES / len(bold) * (BOLD ** 2 - BASE ** 2))
    return s


def draw(sex, rng):
    """One face of a sex (sexes.Sex) as the pools hold them: near the average, distinctive in a few ways."""
    model = sex.model
    s = np.full(len(shares(model)), BASE)
    s[rng.choice(seen(model), FEATURES, replace=False)] = BOLD
    scans = len(model.share)
    return np.concatenate([sex.sample(rng, s[:scans]), np.clip(rng.normal(0.0, s[scans:]), -LIMIT, LIMIT)])


@functools.cache
def tried(sex):
    """TRIED faces of a sex (sexes.Sex) drawn as `draw` draws them, the same each time."""
    rng = np.random.default_rng(0)
    return np.stack([draw(sex, rng) for _ in range(TRIED)])


@functools.cache
def broadest(sex):
    """How a sex's faces are measured (widths.Widths) and the broadest each measure may be (NARROW)."""
    measure = Widths(sex.model)
    widths = measure(tried(sex))
    return measure, widths.mean(0) + NARROW[sex.name] * widths.std(0)


def sample(sex, rng, count):
    """`count` faces of a sex (sexes.Sex) as the pools hold them (draw), none broader than NARROW lets it be."""
    kept = []
    while sum(map(len, kept)) < count:
        faces = np.stack([draw(sex, rng) for _ in range(count)])
        if sex.name in NARROW:
            measure, most = broadest(sex)
            faces = faces[(measure(faces) <= most).all(1)]
        kept.append(faces)
    return np.concatenate(kept)[:count]


def pool(sex, size=POOL_SIZE):
    """The faces of a sex (sexes.Sex) the dev is shown first."""
    return sample(sex, np.random.default_rng((POOL_SEED, list(SEXES).index(sex.name))), size)


def refine_folder(name):
    """Where the latest refinement round of the sex of that name is rendered."""
    return folder(name + "_refine")


def next_folder(name):
    """Where the next refinement round of the sex of that name is rendered while he rates the latest."""
    return folder(name + "_next")


def advance(name):
    """Puts the sex's next refinement round in place of the latest once every face of it is rendered;
    returns whether it did."""
    if not complete(next_folder(name)):
        return False
    if os.path.exists(refine_folder(name)):
        shutil.rmtree(refine_folder(name))
    os.replace(next_folder(name), refine_folder(name))
    return True


def best_picture(name):
    """Where the best faces of the sex of that name are rendered (build_faces.py --best), their numbers
    beside it: a .json holding how many answers they were learnt from."""
    return os.path.join(HERE, "pool", name + "_best.png")


def best_answers(name):
    """How many answers the sex's best faces were rendered from, or None if they are not rendered."""
    numbers = os.path.splitext(best_picture(name))[0] + ".json"
    if not (os.path.exists(best_picture(name)) and os.path.exists(numbers)):
        return None
    with open(numbers, encoding="utf-8") as f:
        return json.load(f)["answers"]


def current(name):
    """The set of faces of the sex of that name he rates now, the latest refinement round's or else the
    pool's: its folder, its faces, the prior on w and the set's name."""
    where = refine_folder(name) if exists(refine_folder(name)) else folder(name)
    if not exists(where):
        sys.exit("no %s's faces are rendered in %s: rate in the main checkout, which holds the dev's faces and answers"
                 % (name, os.path.dirname(os.path.dirname(HERE))))
    faces, share, spread, set_name = rendered(where)
    return where, faces, prior(share, spread, Sex(Model.load(os.path.join(HERE, "model.npz")), name)), set_name


def refine(posterior, sex, rng, size=REFINE_SIZE, draws=REFINE_DRAWS):
    """A refinement round's faces (Thompson sampling): for each, a taste drawn from the posterior and the
    best of `draws` faces of the sex under it. They are faces he likely likes, and differ most where the
    posterior is least sure of his taste, so his answers on them teach what makes the best faces best."""
    faces = []
    for w in rng.multivariate_normal(posterior.mean, posterior.cov, size):
        drawn = sample(sex, rng, draws)
        faces.append(drawn[np.argmax(terms(drawn) @ w)])
    return np.stack(faces)


def prior(share, spread, sex):
    """Prior variances of w, for faces of a sex (sexes.Sex) drawn at `spread`, one number or one per number
    of a face: two such faces' logits differ by PRIOR_LOGIT for each unit the shares sum to, in each number
    and as much again in its square, by how the faces' numbers and squares vary (tried)."""
    numbers = share * (PRIOR_LOGIT / (np.sqrt(2) * spread)) ** 2
    faces = tried(sex)[:, :len(numbers)]
    return np.concatenate([numbers, numbers * faces.var(0) / np.maximum((faces ** 2).var(0), 1e-12)])


def best(posterior, sex, rng, count, draws=4000):
    """The `count` faces, of `draws` random ones of the sex, furthest along the learnt direction, best first:
    faces the pool could hold, with their other features left to chance. Returns the faces and the logits
    of his preferring each to the mean face."""
    faces = sample(sex, rng, draws)
    score = terms(faces) @ posterior.mean - terms(faces.mean(0)) @ posterior.mean
    keep = np.argsort(-score)[:count]
    return faces[keep], score[keep]


class Answers(Log):
    """The answers file: each line is one answer, "set" the set of faces shown (files.rendered; "pool" if
    missing), {"left", "right", "winner"} indices in it, the numbers of the winning face "won" and the
    losing one "lost", "repeat_of" the line it re-asks or null, "seconds" he took and "at", the time. When
    he liked neither face, "winner" is null and both lose to the set's average face: "won" holds that face,
    "lost" the left one and "lost_too" the right, so that a flaw that spoils a face teaches w directly."""

    def consistency(self):
        """How many re-shown pairs he answered as he did the first time, and how many were re-shown."""
        again = [line for line in self.lines if line["repeat_of"] is not None]
        return sum(line["winner"] == self.lines[line["repeat_of"]]["winner"] for line in again), len(again)

    def rounds(self):
        """How many refinement rounds he has answered on."""
        return max([int(line["set"].split()[1]) for line in self.lines if line.get("set", "").startswith("refine")], default=0)

    def differences(self, prior_var, lines):
        """The rows the answers `lines` give the logistic regression: the winners' terms less the losers'."""
        size = len(prior_var) // 2
        pairs = [(line["won"], lost) for line in lines for lost in [line["lost"]] + ([line["lost_too"]] if "lost_too" in line else [])]
        won, lost = (terms(np.array([padded(pair[k], size) for pair in pairs]).reshape(-1, size)) for k in (0, 1))
        return won - lost

    def posterior(self, prior_var, count=None):
        """What his first `count` answers, or all, teach of w."""
        return Posterior(prior_var, self.differences(prior_var, self.lines[:count]), 1.0)

    def foresaw(self, prior_var, k):
        """Whether his answers before the k-th foresaw it."""
        return bool(self.posterior(prior_var, k).logit(self.differences(prior_var, self.lines[k:k + 1]))[0][0] > 0)


class Session:
    """A sitting: shows pairs from a set of faces (P, their numbers), named `set_name`, and records the
    answers. It learns from every answer in the file, but asks and re-shows pairs of this set only."""

    def __init__(self, faces, prior_var, answers, rng, set_name=POOL):
        self.faces, self.prior_var, self.answers, self.rng, self.set = faces, prior_var, answers, rng, set_name
        self.terms = terms(faces)
        self.foreseen_lines = {}                # answer index: (the answer, whether it was foreseen)
        self.posterior = answers.posterior(prior_var)
        self.pair = None

    def mine(self, line):
        """Whether an answer was given on this set."""
        return line.get("set", "pool") == self.set

    def here(self):
        """How many answers were given on this set."""
        return sum(map(self.mine, self.answers.lines))

    def quota(self):
        """The answers on this set after which the next refinement round is due: FIRST on the pool, ROUND
        on a round."""
        return ROUND if self.set.startswith("refine") else FIRST

    def repeatable(self):
        """Earlier first-time answers on this set's faces that have not been re-shown."""
        again = {line["repeat_of"] for line in self.answers.lines}
        return [k for k, line in enumerate(self.answers.lines)
                if self.mine(line) and line["repeat_of"] is None and k not in again and line["winner"] is not None
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
            mean, var = self.posterior.logit(self.terms[i] - self.terms[j])
            k = int(np.argmax(mean ** 2 + var))
        else:
            k = int(np.argmax(self.posterior.information(self.terms[i] - self.terms[j])))
        self.pair = (int(i[k]), int(j[k]), None)
        return self.pair

    def answer(self, pick, seconds):
        """Records that he picked the "left" or "right" face of the pair shown, or "neither"."""
        left, right, repeat_of = self.pair
        numbers = lambda face: np.round(face, 5).tolist()
        if pick == "neither":
            faces = dict(winner=None, won=numbers(self.faces.mean(0)), lost=numbers(self.faces[left]),
                         lost_too=numbers(self.faces[right]))
        else:
            winner, loser = (left, right) if pick == "left" else (right, left)
            faces = dict(winner=winner, won=numbers(self.faces[winner]), lost=numbers(self.faces[loser]))
        self.answers.add(dict(set=self.set, left=left, right=right, repeat_of=repeat_of, **faces,
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

    def foreseen(self, recent=RECENT):
        """Of his last `recent` picks of a face on pairs not re-shown, how many the answers before each
        foresaw: how well w is known, where settled tells only how sure it is. Each pair was picked for being
        near even, so a w known well foresees fewer of them than it would of random pairs."""
        lines = self.answers.lines
        asked = [k for k, line in enumerate(lines) if line["repeat_of"] is None and line["winner"] is not None][-recent:]
        for k in asked:
            if self.foreseen_lines.get(k, (None,))[0] is not lines[k]:
                self.foreseen_lines[k] = (lines[k], self.answers.foresaw(self.prior_var, k))
        return sum(self.foreseen_lines[k][1] for k in asked), len(asked)

    def status(self):
        agreed, again = self.answers.consistency()
        foreseen, recent = self.foreseen()
        return dict(set=self.set, answers=len(self.answers), here=self.here(), quota=self.quota(), agreed=agreed,
                    repeats=again, settled=round(self.posterior.settled(self.rng), 3), foreseen=foreseen, recent=recent)

"""Tests the face tools' learning with simulated raters, who answer by hidden directions of their own.

  python -I simulate.py [--sex women|men] [--raters 8] [--answers 300] [--strength 2.0] [--lapse 0.05]
                        [--first 40] [--round 40] [--random] [--his]
  python -I simulate.py --labels [--raters 8] [--slope 4.0] [--lapse 0.05] [--truth d.npy]

Taste (taste.py): each rater has a hidden preference direction, answers by the Bradley-Terry model with
it, and now and then presses a key at random. He rates the pool for --first answers and then refinement
rounds of --round answers each, as the dev is meant to; --first at least --answers keeps him on the pool,
and --random picks pairs at random instead, for comparison. Prints, as the answers come in, how close the
learnt direction comes to the hidden one (the cosine), how good the faces it would generate are (of 4000
faces the 25 it likes best, by the rater's own taste, as a share of the 25 he likes best), the loop's own
estimate of the cosine, and the consistency on re-shown pairs. Each sex's pool, drawn from labels a
simulated labeller gives, is tested in turn, or --sex alone, on two kinds of rater: one whose direction is
drawn from the loop's prior, and one that cares more for the small components than the prior expects.
--strength is how far two pool faces' logits differ. --his tests the women instead as the dev rates them:
with his labels, raters drawn from what his answers so far say of his taste, who have given those answers.

Labels (sexes.py): each labeller has a hidden female-male direction, `--truth` or drawn as the raters'
are, and a middle; along it his logit grows by --slope per standard deviation, and he calls faces within
BAND logits of even androgynous, a few unclear, and lapses at random. Prints how close the learnt
direction and middle come as the label set is labelled, and how far each sex's pool, drawn from the
learnt direction, lies along the hidden one, with the chance he would call its faces their sex.
"""
import argparse, os, sys, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import taste
from faces.files import HERE
from faces.logistic import cosine, sigmoid
from faces.model import Model
from faces.sexes import SEXES, LABEL_COUNT, Direction, Labels, Sex, label_set

MODEL = os.path.join(HERE, "model.npz")
CHECK = 25                                     # answers between the lines printed
JUDGED, KEPT = 4000, 25
LABEL_CHECKS = (25, 50, 75, 100, LABEL_COUNT)
BAND, UNCLEAR = 1.0, 0.04


def hidden(variance, rng):
    w = rng.normal(0.0, np.sqrt(variance))
    return w / np.linalg.norm(w)


class Memory(taste.Answers):
    """A simulated rater's answers, which no file keeps, after those he starts with."""

    def __init__(self, lines=()):
        self.lines = list(lines)

    def add(self, line):
        self.lines.append(line)


class Rater:
    """Answers by the hidden taste w over a face's terms (taste.terms; one over its numbers alone weighs no
    squares), scaled so that the logits of two of the faces `faces` differ by about `strength`."""

    def __init__(self, w, faces, strength, lapse, rng):
        w = np.pad(w, (0, 2 * faces.shape[1] - len(w)))
        self.w = w * strength / (np.sqrt(2) * (taste.terms(faces) @ w).std())
        self.lapse, self.rng = lapse, rng

    def pick(self, left, right):
        if self.rng.random() < self.lapse:
            return "left" if self.rng.random() < 0.5 else "right"
        return "left" if self.rng.random() < sigmoid(self.w @ (taste.terms(left) - taste.terms(right))) else "right"


class Labeller:
    def __init__(self, unit, middle, slope, lapse, rng):
        self.unit, self.middle, self.slope, self.lapse, self.rng = unit, middle, slope, lapse, rng

    def logit(self, faces):
        return self.slope * (faces[..., :len(self.unit)] @ self.unit - self.middle)

    def label(self, face):
        r = self.rng.random()
        if r < UNCLEAR:
            return "unclear"
        if r < UNCLEAR + self.lapse:
            return self.rng.choice(["woman", "androgynous", "man"])
        s = self.logit(face)
        woman, man = sigmoid(-BAND - s), sigmoid(s - BAND)
        r = self.rng.random()
        return "woman" if r < woman else "man" if r > 1.0 - man else "androgynous"


def quality(learnt, w, judged):
    """How good, by the rater's taste w, the KEPT faces the learnt taste likes best of those judged are:
    their mean score above the average face's, as a share of that of the KEPT he likes best."""
    true = taste.terms(judged) @ w
    picked = true[np.argsort(-(taste.terms(judged) @ learnt))[:KEPT]]
    return (picked.mean() - true.mean()) / (np.sort(true)[-KEPT:].mean() - true.mean())


def run(sex, prior, pool, judged, rater, start, a, rng):
    answers = Memory(start)
    session = taste.Session(pool, prior, answers, rng)
    rows = []
    for n in range(a.answers):
        if n >= a.first and (n - a.first) % a.round == 0:
            faces = taste.refine(session.posterior, sex, rng)
            session = taste.Session(faces, prior, answers, rng, "refine %d" % ((n - a.first) // a.round + 1))
        left, right, _ = session.next()
        if a.random and session.pair[2] is None:
            left, right = rng.choice(len(session.faces), 2, replace=False)
            session.pair = (int(left), int(right), None)
        session.answer(rater.pick(session.faces[left], session.faces[right]), 1.0)
        if (n + 1) % CHECK == 0:
            status = session.status()
            rows.append((n + 1, cosine(session.posterior.mean, rater.w), quality(session.posterior.mean, rater.w, judged),
                         status["settled"], status["agreed"], status["repeats"]))
    return rows


def test(model, sex, kinds, start, a):
    """kinds: for each kind of rater, its name and what draws one's hidden taste from a generator."""
    share, spread = taste.shares(model), taste.spread(model)
    prior, pool = taste.prior(share, spread, sex), taste.pool(sex)
    rng = np.random.default_rng(1)
    judged = taste.sample(sex, rng, JUDGED)
    for name, draw in kinds:
        rows = []
        for seed in range(a.raters):
            rng = np.random.default_rng(1000 + seed)
            rows.append(run(sex, prior, pool, judged, Rater(draw(rng), judged, a.strength, a.lapse, rng), start, a, rng))
        rows = np.array(rows, float)
        print("%s, rater %s, %s pairs, %d answers on the pool then rounds of %d, strength %.1f, lapse %.2f, %d raters" % (
            sex.name, name, "random" if a.random else "chosen", min(a.first, a.answers), a.round, a.strength, a.lapse, a.raters))
        print("  answers  cosine (min)    quality  settled  repeats agreed")
        for k in range(rows.shape[1]):
            n, cos, good, settled, agreed, again = rows[:, k].T
            print("  %7d  %.3f (%.3f)  %.3f    %.3f    %d of %d" % (n[0], cos.mean(), cos.min(), good.mean(), settled.mean(),
                                                                agreed.sum(), again.sum()))


def taste_main(model, a):
    share = taste.shares(model)
    if a.his:
        answers = taste.Answers(taste.answers("women"))
        known = answers.posterior(taste.prior(share, taste.spread(model), Sex(model, "women")))
        test(model, Sex(model, "women"), [("his", lambda rng: rng.multivariate_normal(known.mean, known.cov))], answers.lines, a)
        return
    kinds = [("prior", lambda rng: hidden(share, rng)), ("flatter", lambda rng: hidden(np.sqrt(share), rng))]
    with tempfile.TemporaryDirectory() as folder:
        rng = np.random.default_rng(0)
        labels = Labels(os.path.join(folder, "labels.jsonl"))
        labeller = Labeller(hidden(model.share, rng), 0.0, a.slope, a.lapse, rng)
        for i, face in enumerate(label_set(model)):
            labels.label(i, face, labeller.label(face), 1.0)
        for sex in [a.sex] if a.sex else SEXES:
            test(model, Sex(model, sex, labels.path), kinds, (), a)


def label_test(model, labeller, folder):
    """Labels the label set as the labeller would; returns, at each check, the cosine of the learnt direction
    with the hidden one and the error of its middle, then each sex's pool's places along the hidden direction
    and the chances he would call them their sex."""
    labels = Labels(os.path.join(folder, "labels.jsonl"))
    rows = []
    for i, face in enumerate(label_set(model)):
        labels.label(i, face, labeller.label(face), 1.0)
        if i + 1 in LABEL_CHECKS:
            d = Direction(model.share, labels)
            rows.append((cosine(d.unit, labeller.unit), d.middle - labeller.middle))
    pools = {}
    for name, side in SEXES.items():
        logit = labeller.logit(taste.pool(Sex(model, name, labels.path)))
        pools[name] = (side * logit / labeller.slope, sigmoid(side * logit))
    return rows, pools


def labels_main(model, a):
    truth = np.load(a.truth) if a.truth else None
    kinds = [("given", None)] if truth is not None else [("prior", model.share), ("flatter", np.sqrt(model.share))]
    for name, variance in kinds:
        rows, pools = [], {sex: [] for sex in SEXES}
        for seed in range(a.raters):
            rng = np.random.default_rng(2000 + seed)
            unit = truth / np.linalg.norm(truth) if truth is not None else hidden(variance, rng)
            with tempfile.TemporaryDirectory() as folder:
                r, p = label_test(model, Labeller(unit, rng.normal(0.0, 0.2), a.slope, a.lapse, rng), folder)
            rows.append(r)
            for sex in SEXES:
                pools[sex].append(p[sex])
        rows = np.array(rows, float)
        print("labeller %s, slope %.1f, lapse %.2f, %d labellers" % (name, a.slope, a.lapse, a.raters))
        print("  labels  cosine (min)    middle error")
        for k, n in enumerate(LABEL_CHECKS):
            cos, error = rows[:, k].T
            print("  %6d  %.3f (%.3f)  %.3f" % (n, cos.mean(), cos.min(), np.sqrt((error ** 2).mean())))
        for sex, runs in pools.items():
            along = np.concatenate([r[0] for r in runs])
            called = np.concatenate([r[1] for r in runs])
            print("  %-6s pool on its side by %.2f (least %.2f); called %s %.2f, under 0.9 for %.1f%%" % (
                sex, along.mean(), along.min(), sex, called.mean(), 100 * (called < 0.9).mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex", choices=SEXES)
    ap.add_argument("--raters", type=int, default=8)
    ap.add_argument("--answers", type=int, default=300)
    ap.add_argument("--strength", type=float, default=2.0)
    ap.add_argument("--lapse", type=float, default=0.05)
    ap.add_argument("--first", type=int, default=taste.FIRST)
    ap.add_argument("--round", type=int, default=taste.ROUND)
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--his", action="store_true")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--slope", type=float, default=4.0)
    ap.add_argument("--truth")
    a = ap.parse_args()
    model = Model.load(MODEL)
    (labels_main if a.labels else taste_main)(model, a)


main()

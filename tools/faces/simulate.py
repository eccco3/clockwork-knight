"""Tests the face tools' learning with simulated raters, who answer by hidden directions of their own.

  python -I simulate.py [--sex women|men] [--raters 8] [--answers 200] [--strength 2.0] [--lapse 0.05] [--random]
  python -I simulate.py --labels [--raters 8] [--slope 4.0] [--lapse 0.05] [--truth d.npy]

Taste (taste.py): each rater has a hidden preference direction, answers by the Bradley-Terry model with
it, and now and then presses a key at random. Prints how close the learnt direction comes to the hidden
one (the cosine, which is also the correlation of their scores over random faces), the loop's own
estimate of that, and the consistency on re-shown pairs. Each sex's pool, drawn from labels a simulated
labeller gives, is tested in turn, or --sex alone; --random picks pairs at random instead, for comparison. Two kinds of rater: one whose direction is
drawn from the loop's prior, and one that cares more for the small components than the prior expects.

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
from faces.model import Model, SPREAD
from faces.sexes import SEXES, LABEL_COUNT, Direction, Labels, Sex, label_set

MODEL = os.path.join(HERE, "model.npz")
CHECKS = (25, 50, 100, 150, 200, 300)
LABEL_CHECKS = (25, 50, 75, 100, LABEL_COUNT)
BAND, UNCLEAR = 1.0, 0.04


def hidden(variance, rng):
    w = rng.normal(0.0, np.sqrt(variance))
    return w / np.linalg.norm(w)


class Rater:
    def __init__(self, variance, strength, lapse, rng):
        self.w = hidden(variance, rng) * strength / np.sqrt(2 * SPREAD ** 2)
        self.lapse, self.rng = lapse, rng

    def pick(self, left, right):
        if self.rng.random() < self.lapse:
            return "left" if self.rng.random() < 0.5 else "right"
        return "left" if self.rng.random() < sigmoid(self.w @ (left - right)) else "right"


class Labeller:
    def __init__(self, unit, middle, slope, lapse, rng):
        self.unit, self.middle, self.slope, self.lapse, self.rng = unit, middle, slope, lapse, rng

    def logit(self, faces):
        return self.slope * (faces @ self.unit - self.middle)

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


def run(model, faces, rater, count, rng, random_pairs):
    with tempfile.TemporaryDirectory() as folder:
        session = taste.Session(faces, taste.prior(model.share, SPREAD), taste.Answers(os.path.join(folder, "a.jsonl")), rng)
        rows = []
        for n in range(1, count + 1):
            left, right, _ = session.next()
            if random_pairs and session.pair[2] is None:
                left, right = rng.choice(len(faces), 2, replace=False)
                session.pair = (int(left), int(right), None)
            session.answer(rater.pick(faces[left], faces[right]), 1.0)
            if n in CHECKS:
                status = session.status()
                rows.append((n, cosine(session.posterior.mean, rater.w), status["settled"],
                             status["agreed"], status["repeats"]))
        assert len(taste.Answers(session.answers.path)) == count, "an answer was not saved"
        return rows


def test(model, sex, a):
    faces = taste.pool(sex)
    for name, variance in (("prior", model.share), ("flatter", np.sqrt(model.share))):
        rows = []
        for seed in range(a.raters):
            rng = np.random.default_rng(1000 + seed)
            rows.append(run(model, faces, Rater(variance, a.strength, a.lapse, rng), a.answers, rng, a.random))
        rows = np.array(rows, float)
        print("%s, rater %s, %s pairs, strength %.1f, lapse %.2f, %d raters" % (
            sex.name, name, "random" if a.random else "chosen", a.strength, a.lapse, a.raters))
        print("  answers  cosine (min)    settled  repeats agreed")
        for k in range(rows.shape[1]):
            n, cos, settled, agreed, again = rows[:, k].T
            print("  %7d  %.3f (%.3f)  %.3f    %d of %d" % (n[0], cos.mean(), cos.min(), settled.mean(), agreed.sum(), again.sum()))


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
        faces = taste.pool(Sex(model, name, labels.path))
        along = faces @ labeller.unit - labeller.middle
        pools[name] = (side * along, sigmoid(side * labeller.logit(faces)))
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
    ap.add_argument("--answers", type=int, default=200)
    ap.add_argument("--strength", type=float, default=2.0)
    ap.add_argument("--lapse", type=float, default=0.05)
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--labels", action="store_true")
    ap.add_argument("--slope", type=float, default=4.0)
    ap.add_argument("--truth")
    a = ap.parse_args()
    model = Model.load(MODEL)
    if a.labels:
        labels_main(model, a)
        return
    with tempfile.TemporaryDirectory() as folder:
        rng = np.random.default_rng(0)
        labels = Labels(os.path.join(folder, "labels.jsonl"))
        labeller = Labeller(hidden(model.share, rng), 0.0, a.slope, a.lapse, rng)
        for i, face in enumerate(label_set(model)):
            labels.label(i, face, labeller.label(face), 1.0)
        for sex in [a.sex] if a.sex else SEXES:
            test(model, Sex(model, sex, labels.path), a)


main()

"""Tests taste.py's rating loop with simulated raters: each has a hidden preference direction, answers by
the Bradley-Terry model with it, and now and then presses a key at random. Prints how close the learnt
direction comes to the hidden one (the cosine, which is also the correlation of their scores over random
faces), the loop's own estimate of that, and the consistency on re-shown pairs.

  python -I simulate.py [--raters 8] [--answers 200] [--strength 2.0] [--lapse 0.05] [--random]

--random picks pairs at random instead, for comparison. Two kinds of rater: one whose direction is drawn
from the loop's prior, and one that cares more for the small components than the prior expects.
"""
import argparse, os, sys, tempfile
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import taste
from faces.model import Model, SPREAD

MODEL = os.path.join(taste.HERE, "model.npz")
CHECKS = (25, 50, 100, 150, 200, 300)


class Rater:
    def __init__(self, variance, strength, lapse, rng):
        w = rng.normal(0.0, np.sqrt(variance))
        self.w = w * strength / np.sqrt(2 * SPREAD ** 2 * (w @ w))
        self.lapse, self.rng = lapse, rng

    def pick(self, left, right):
        if self.rng.random() < self.lapse:
            return "left" if self.rng.random() < 0.5 else "right"
        return "left" if self.rng.random() < 1.0 / (1.0 + np.exp(-self.w @ (left - right))) else "right"


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
                rows.append((n, taste.cosine(session.posterior.mean, rater.w), status["settled"],
                             status["agreed"], status["repeats"]))
        assert len(taste.Answers(session.answers.path)) == count, "an answer was not saved"
        return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raters", type=int, default=8)
    ap.add_argument("--answers", type=int, default=200)
    ap.add_argument("--strength", type=float, default=2.0)
    ap.add_argument("--lapse", type=float, default=0.05)
    ap.add_argument("--random", action="store_true")
    a = ap.parse_args()
    model = Model.load(MODEL)
    faces = taste.pool(model)
    kinds = (("prior", model.share), ("flatter", np.sqrt(model.share)))
    for name, variance in kinds:
        rows = []
        for seed in range(a.raters):
            rng = np.random.default_rng(1000 + seed)
            rows.append(run(model, faces, Rater(variance, a.strength, a.lapse, rng), a.answers, rng, a.random))
        rows = np.array(rows, float)
        print("rater %s, %s pairs, strength %.1f, lapse %.2f, %d raters" % (
            name, "random" if a.random else "chosen", a.strength, a.lapse, a.raters))
        print("  answers  cosine (min)    settled  repeats agreed")
        for k in range(rows.shape[1]):
            n, cos, settled, agreed, again = rows[:, k].T
            print("  %7d  %.3f (%.3f)  %.3f    %d of %d" % (n[0], cos.mean(), cos.min(), settled.mean(), agreed.sum(), again.sum()))


main()

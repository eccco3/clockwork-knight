"""The rating session dev/taste.tscn shows: it reads the dev's picks on stdin and writes each next pair.

  python -I rate.py --sex women|men [--answers a.jsonl]     a session, one JSON line out per line in
  python -I rate.py --sex women|men --report                how far the learning has come

In: "left" or "right", the face he prefers, or "undo". Out: {"left", "right"} pictures of the pair to show,
and the session's status: "answers", "agreed" of the "repeats" re-shown, and "settled", from 0 to 1.
Every answer is saved before the next pair is sent.
"""
import argparse, json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import taste
from faces.sexes import SEXES


def show(session, pair, folder):
    print(json.dumps(dict(left=taste.picture(pair[0], folder), right=taste.picture(pair[1], folder), **session.status())),
          flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex", choices=SEXES, required=True)
    ap.add_argument("--answers")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    folder = taste.pool_folder(a.sex)
    faces, prior_var = taste.load_pool(folder)
    session = taste.Session(faces, prior_var, taste.Answers(a.answers or taste.answers(a.sex)), np.random.default_rng())
    if a.report:
        print(session.status())
        order = np.argsort(-np.abs(session.posterior.mean))[:8]
        print("strongest components:", ", ".join("%d %+.2f" % (k, session.posterior.mean[k]) for k in order))
        return
    show(session, session.next(), folder)
    shown = time.monotonic()
    for line in sys.stdin:
        pick = line.strip()
        if pick in ("left", "right"):
            session.answer(pick, time.monotonic() - shown)
            pair = session.next()
        elif pick == "undo":
            pair = session.undo()
        else:
            continue
        show(session, pair, folder)
        shown = time.monotonic()


main()

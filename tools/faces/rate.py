"""The rating session dev/taste.tscn shows: it reads the dev's requests on stdin and writes each next pair,
from the sex's latest refinement round if it has one, or else its pool (taste.current), and renders the
next round and the best faces beside it in the background (background.py).

  python -I rate.py --sex women|men [--answers a.jsonl]     a session, one JSON line out per line in
  python -I rate.py --sex women|men --report                how far the learning has come

In: "left" or "right", the face he prefers, "neither" if he likes neither (taste.Answers), "undo", or "best",
to have the best faces rendered from all his answers (build_faces.py --best) unless they are. Out, for each line in, and as a "notice" whenever a render
moves on: {"left", "right"} pictures of the pair to show; the session's status: the "set" shown, his
"answers" in all and "here", on that set, of the "quota" after which the next round is due, "agreed" of the
"repeats" re-shown, "settled", from 0 to 1, and "foreseen" of his "recent" answers (taste.Session.foreseen);
"next", the next round's render: whether "rendering", how many of its "faces" are "rendered", and why it
"failed" if it did; and "best", the best faces: their
"picture" ("" until rendered), the "answers" they were learnt from, whether "rendering" and why it "failed".

Every answer is saved before the next pair is sent. Once a set has its quota of answers the next round
renders (build_faces.py --refine) while he rates on, and the first answer after it is rendered brings the
round's first pair. Closing the sitting ends its renders; the next sitting finishes the round.
"""
import argparse, json, os, queue, sys, threading, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import taste
from faces.background import Build
from faces.files import complete, exists, picture, progress
from faces.sexes import SEXES

POLL = 0.5                                      # seconds between looks at the renders


class Sitting:
    """A session on the set he rates now, and the renders that run beside it."""

    def __init__(self, sex, answers):
        self.sex, self.answers, self.rng = sex, taste.Answers(answers), np.random.default_rng()
        self.round = self.best = None           # their runs of build_faces.py (background.Build), once started
        self.told = None
        taste.advance(sex)
        self.open()

    def open(self):
        """Starts a session on the latest set."""
        self.pictures, faces, prior_var, set_name = taste.current(self.sex)
        self.session = taste.Session(faces, prior_var, self.answers, self.rng, set_name)
        self.pair = self.session.next()

    def request(self, said):
        if said in ("left", "right", "neither"):
            self.session.answer(said, time.monotonic() - self.shown)
            if not (self.round and self.round.running()) and taste.advance(self.sex):
                self.round = None
                self.open()
            else:
                self.pair = self.session.next()
        elif said == "undo":
            self.pair = self.session.undo()
        elif said == "best" and self.answers.lines and not (self.best and self.best.running()) \
                and taste.best_answers(self.sex) != len(self.answers):
            self.best = self.build(["--best", taste.best_picture(self.sex)], taste.best_picture(self.sex))
        self.renders()
        self.show()

    def renders(self):
        """Renders the next round once this set has its quota of answers, or to finish one begun before."""
        where = taste.next_folder(self.sex)
        if self.round is None and not complete(where) and (exists(where) or self.session.here() >= self.session.quota()):
            self.round = self.build(["--refine"], where)

    def build(self, arguments, where):
        return Build(["--sex", self.sex, "--answers", self.answers.path] + arguments, os.path.splitext(where)[0] + ".log")

    def background(self):
        rendered, faces = progress(taste.next_folder(self.sex))
        learnt = taste.best_answers(self.sex)
        return dict(
            next=dict(rendering=bool(self.round and self.round.running()), rendered=rendered, faces=faces,
                      failed=self.round.failure() if self.round else ""),
            best=dict(picture=taste.best_picture(self.sex) if learnt is not None else "", answers=learnt,
                      rendering=bool(self.best and self.best.running()), failed=self.best.failure() if self.best else ""))

    def show(self, notice=False):
        self.told = self.background()
        print(json.dumps(dict(left=picture(self.pair[0], self.pictures), right=picture(self.pair[1], self.pictures),
                              notice=notice, **self.session.status(), **self.told)), flush=True)
        if not notice:
            self.shown = time.monotonic()

    def look(self):
        """Tells him when a render has moved on."""
        self.renders()
        if self.background() != self.told:
            self.show(notice=True)


def read(requests):
    for line in sys.stdin:
        requests.put(line.strip())
    requests.put(None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex", choices=SEXES, required=True)
    ap.add_argument("--answers")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    answers = os.path.abspath(a.answers or taste.answers(a.sex))
    if a.report:
        _, faces, prior_var, set_name = taste.current(a.sex)
        session = taste.Session(faces, prior_var, taste.Answers(answers), np.random.default_rng(), set_name)
        print(session.status())
        order, size = np.argsort(-np.abs(session.posterior.mean))[:8], len(faces[0])
        print("strongest terms:", ", ".join("%s %+.2f" % (k if k < size else "%d²" % (k - size), session.posterior.mean[k])
                                             for k in order))
        return
    sitting = Sitting(a.sex, answers)
    requests = queue.Queue()
    threading.Thread(target=read, args=(requests,), daemon=True).start()
    sitting.renders()
    sitting.show()
    while True:
        try:
            said = requests.get(timeout=POLL)
        except queue.Empty:
            sitting.look()
            continue
        if said is None:
            return
        sitting.request(said)


main()

"""The picking session dev/picks_women.tscn shows (rounds.py): it reads the dev's requests on stdin and
writes the sheet to show, drawing each next sheet and rendering it in the background (background.py).

  python -I pick.py --sex women [--picks a.jsonl] [--answers a.json]     a session, one JSON line out per line in
  python -I pick.py --sex women [--picks a.jsonl] --report       how his picks so far narrow the next sheet

In: "submit" and the JSON list of the faces he picked on the sheet shown, [] if none, or "undo", to take the
last sheet submitted back and show it again. Out, for each line in, and as a "notice" whenever a render moves
on: the "sheet" shown, its "pictures", a face each, the front and the profile side by side ([] until all are
rendered), and the faces "picked" on it before ([] unless taken back); how many
"sheets" he has submitted and "picks" he made on them; the sheet's "narrowest" directions as [name, share of
the full spread], the "candidates" its faces carry and how many candidate features are "unanswered", held at
0; and the render of the sheet shown, "here", and of the "next": how many of its "faces" are "rendered", and
why it "failed" if it did.

The sheet shown and the next are drawn and rendered one at a time, the next from his picks on the sheets
before the one shown, so that it renders while he picks. A sheet's picks are saved before the next is shown;
taking a sheet back throws away the sheet drawn from it. The pictures of all but the last KEEP sheets
submitted are deleted, so those are as far back as he can go.
"""
import argparse, json, os, queue, shutil, sys, threading
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import candidates, rounds
from faces.background import Build
from faces.files import complete, folder, picture, progress
from faces.sexes import SEXES

POLL = 0.5                                      # seconds between looks at the render
KEEP = 3


class Sitting:
    """His picks, the sheets drawn from them and the render that runs beside him."""

    def __init__(self, sex, picks, answers):
        self.rounds, self.picks = rounds.Rounds(sex, answers), rounds.Picks(picks)
        self.where, self.rng = folder(os.path.splitext(os.path.basename(picks))[0]), np.random.default_rng()
        self.build = self.building = None       # the render running or last run, and its sheet's number
        self.restored, self.told = [], None
        os.makedirs(self.where, exist_ok=True)

    def record(self, j):
        """The file that holds how the jth sheet was drawn."""
        return os.path.join(self.where, "%03d.json" % j)

    def folder(self, j):
        """Where the jth sheet's pictures are rendered."""
        return os.path.join(self.where, "%03d" % j)

    def shown(self):
        return len(self.picks) + 1

    def renders(self):
        """Draws and renders the sheet shown and then the next, one at a time; a render that failed waits for
        the next sitting."""
        if self.build and (self.build.running() or self.build.failure()):
            return
        for j in (self.shown(), self.shown() + 1):
            if complete(self.folder(j)):
                continue
            if not os.path.exists(self.record(j)):
                rounds.keep(self.record(j), dict(self.rounds.draw(self.picks.lines, self.rng), sheet=j))
            self.build, self.building = Build(["--sheet", self.record(j)], self.folder(j) + ".log", rounds.SCRIPT), j
            return

    def request(self, said):
        if said.startswith("submit"):
            self.submit(json.loads(said[len("submit"):] or "[]"))
        elif said == "undo":
            self.undo()
        self.renders()
        self.show()

    def submit(self, picked):
        j = self.shown()
        if not complete(self.folder(j)):
            return
        self.picks.submit(rounds.load(self.record(j)), [i for i in map(int, picked) if 0 <= i < rounds.SHEET])
        self.restored = []
        for old in range(1, j - KEEP + 1):
            self.discard(old)

    def undo(self):
        """Takes the last sheet submitted back, if its pictures are kept, and throws away the sheet drawn from it."""
        j = len(self.picks)
        if not (j and complete(self.folder(j))):
            return
        self.restored = self.picks.undo()["picked"]
        later = j + 2
        while os.path.exists(self.record(later)):
            self.discard(later)
            later += 1

    def discard(self, j):
        if self.building == j:
            self.build.stop()
            self.build = self.building = None
        shutil.rmtree(self.folder(j), ignore_errors=True)
        for path in (self.record(j), self.folder(j) + ".log"):
            if os.path.exists(path):
                os.remove(path)

    def render(self, j):
        rendered, faces = progress(self.folder(j))
        failed = self.build.failure() if self.build and self.building == j else ""
        return dict(rendered=rendered, faces=faces, failed=failed)

    def state(self):
        j = self.shown()
        sheet = rounds.load(self.record(j)) if os.path.exists(self.record(j)) else dict(r=[], candidates={})
        names = candidates.names()
        return dict(sheet=j, pictures=[picture(i, self.folder(j)) for i in range(rounds.SHEET)]
                    if complete(self.folder(j)) else [], picked=self.restored, sheets=len(self.picks),
                    picks=self.picks.picks(), narrowest=self.rounds.narrowest(sheet),
                    candidates=[names[key] for key in sheet["candidates"]], unanswered=self.rounds.unanswered(),
                    here=self.render(j), next=self.render(j + 1))

    def show(self, notice=False):
        self.told = self.state()
        print(json.dumps(dict(self.told, notice=notice)), flush=True)

    def look(self):
        """Tells him when the render has moved on."""
        self.renders()
        if self.state() != self.told:
            self.show(notice=True)


def read(requests):
    for line in sys.stdin:
        requests.put(line.strip())
    requests.put(None)


def report(sitting):
    """How his picks so far, and his favourites among the pool, narrow the next sheet."""
    lines = sitting.picks.lines
    sheet = sitting.rounds.draw(lines, np.random.default_rng(0))
    judged = sheet["shrinkage"]
    print("%d sheets, %d picks; log variance ratios' scatter over %d directions observed %.3f, by chance %.3f, "
          "real %.3f; narrower by %.3f on average" % (len(lines), sitting.picks.picks(), judged["judged"],
                                                      judged["observed"], judged["chance"], judged["real"],
                                                      judged["narrowing"]))
    named = sitting.rounds.narrowest(sheet, 8)
    print("narrowest spreads:", ", ".join("%s %.3f (variance %.3f)" % (name, s, s * s) for name, s in named))
    print("candidates drawn:", ", ".join("%s %s" % (key, d["range"]) for key, d in sheet["candidates"].items()) or "none")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex", choices=SEXES, required=True)
    ap.add_argument("--picks")
    ap.add_argument("--answers")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    sitting = Sitting(a.sex, os.path.abspath(a.picks or rounds.picks_path(a.sex)), a.answers and os.path.abspath(a.answers))
    if a.report:
        return report(sitting)
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

"""Picking rounds around a sex's base face (women_base.json): sheets of SHEET faces, from which the dev picks
those he likes (dev/picks_women.tscn, through pick.py), each next sheet drawn about the average of his picks.

  blender --background --python tools/faces/rounds.py -- --sheet tools/faces/pool/picks_women/003.json

renders a drawn sheet into the folder beside it, a picture per face, the front and the profile side by side
in the candidate features' frame (candidates.FACE), carrying on where a render stopped.

A sheet's face is its centre plus a deviation drawn as the sex's pool draws its faces (taste.draw), about
their average, at SCALES of the pool's spread in the scan numbers, the 22 features and the brows; and each
candidate feature he keeps (candidates.kept) at a strength drawn between his lowest and highest, most often
at the centre (a triangular distribution). Faces are symmetric. The first sheet's centre is the base face,
its candidates at his favourites; each after that is the average of every face he has picked, a candidate's
within his strengths, or at his favourite until a pick carries it.

Each direction's spread, and a candidate's reach from the centre, is that times sqrt(r), r an empirical-Bayes
estimate of how much narrower in variance his picks are than the faces they were picked from (narrowing),
from FLOOR to 1: never below half the spread. No correlations between directions are learnt.
"""
import json, os, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import brows, candidates, files, makehuman, taste
from faces.files import HERE, Log, whole
from faces.model import Model
from faces.sexes import Sex

SHEET = 25
SCALES = (1.0, 0.5, 1.0)                        # of the pool's spread: in the scan numbers, the 22 features, the brows
FLOOR = 0.25
FEWEST = 8                                      # picks a direction needs to be judged on its own
NULLS, CHUNK = 1000, 100                        # random pickings chance is measured over, so many at a time
VIEWS = (0.0, 90.0)
SCRIPT = os.path.abspath(__file__)


def base_path(sex):
    return os.path.join(HERE, "%s_base.json" % sex)


def answers_path(sex):
    """The dev's answers on the candidate features (dev/features.gd)."""
    return os.path.join(HERE, "features_%s.json" % sex)


def picks_path(sex):
    return os.path.join(HERE, "picks_%s.jsonl" % sex)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def keep(path, sheet):
    with whole(path) as part, open(part, "w", encoding="utf-8", newline="\n") as f:
        json.dump(sheet, f, separators=(",", ":"))


def labels(model):
    """What the dev calls each of a face's numbers."""
    return ["scan %d" % k for k in range(len(model.share))] + list(makehuman.SHAPES) + list(brows.NAMES)


def scales(model):
    """SCALES for each of a face's numbers."""
    counts = (len(model.share), len(model.names), len(brows.NAMES))
    return np.concatenate([np.full(n, s) for n, s in zip(counts, SCALES)])


def triangle(lowest, mode, highest):
    """The mean and standard deviation of the triangular distribution."""
    return (lowest + mode + highest) / 3.0, float(np.sqrt(
        (lowest ** 2 + mode ** 2 + highest ** 2 - lowest * mode - lowest * highest - mode * highest) / 18.0))


def deviations(sheet, keys):
    """Each of a sheet's faces' deviations from the mean of its draw, in units of its spread, in each of a
    face's numbers and then each candidate of `keys`: nan where the sheet drew none."""
    numbers = np.array([face["numbers"] for face in sheet["faces"]], float)
    z = (numbers - np.asarray(sheet["centre"])) / np.asarray(sheet["spread"])
    extra = np.full((len(numbers), len(keys)), np.nan)
    for k, key in enumerate(keys):
        if key in sheet["candidates"]:
            (lowest, highest), mode = sheet["candidates"][key]["range"], sheet["candidates"][key]["centre"]
            mean, spread = triangle(lowest, mode, highest)
            if spread > 0:
                extra[:, k] = [(face["strengths"][key] - mean) / spread for face in sheet["faces"]]
    return np.hstack([z, extra])


def variance(z, axis):
    """The variance along `axis` of z's values that are not nan, and how many there are."""
    has = ~np.isnan(z)
    count = has.sum(axis)
    mean = np.where(has, z, 0.0).sum(axis, keepdims=True) / np.maximum(has.sum(axis, keepdims=True), 1)
    return (np.where(has, z - mean, 0.0) ** 2).sum(axis) / np.maximum(count, 1), count


def narrowing(sheets, keys, rng, nulls=NULLS):
    """r for each of a face's numbers and then each candidate of `keys`, from his picks on `sheets`, and how
    it was judged.

    In each direction, the log of the variance of his picks over that of every face of the sheets (in units of
    each sheet's spread) says how much narrower his picks are, but partly by chance: random pickings of as
    many faces from the same sheets give, in each direction, the log ratio chance alone yields, its mean (the
    bias) and its spread. The scatter of the debiased log ratios over the directions beyond chance's is what
    really differs between directions (tau^2); each is pulled toward their mean by its own chance spread,
    by tau^2 / (tau^2 + its chance variance), the empirical-Bayes estimate. A direction with fewer than FEWEST
    picks keeps their mean. Returns r and the judgement: the log ratios' scatter "observed" over the
    directions judged and by "chance", the "real" scatter, tau, and the mean "narrowing", exp of their mean."""
    z = [deviations(sheet, keys) for sheet in sheets]
    picked = [np.asarray(sheet["picked"], int) for sheet in sheets]
    drawn = variance(np.vstack(z), 0)[0]
    spread, count = variance(np.vstack([d[p] for d, p in zip(z, picked)]), 0)
    judged = (count >= FEWEST) & (drawn > 0)
    logs = np.log(spread[judged] / drawn[judged])
    by_chance = []
    for start in range(0, nulls, CHUNK):
        n = min(CHUNK, nulls - start)
        random = np.concatenate([d[rng.random((n, len(d))).argsort(1)[:, :len(p)]] for d, p in zip(z, picked)], 1)
        by_chance.append(np.log(np.maximum(variance(random[:, :, judged], 1)[0], 1e-12) / drawn[judged]))
    by_chance = np.concatenate(by_chance)
    bias, noise = by_chance.mean(0), by_chance.std(0)
    real = logs - bias
    mean = real.mean()
    tau2 = max(0.0, ((real - mean) ** 2).mean() - (noise ** 2).mean())
    shrunk = np.full(len(drawn), mean)
    shrunk[judged] = mean + tau2 / (tau2 + noise ** 2) * (real - mean)
    return np.clip(np.exp(shrunk), FLOOR, 1.0), dict(
        observed=round(float(logs.std()), 4), chance=round(float(by_chance.std(1).mean()), 4),
        real=round(float(np.sqrt(tau2)), 4), narrowing=round(float(np.exp(mean)), 4), judged=int(judged.sum()))


class Rounds:
    """A sex's picking rounds: the base face, the dev's answers on the candidate features, and his favourites
    among the sex's pool (the base face's "picks"), which count as picks from one sheet of its faces, for the
    spreads only."""

    def __init__(self, sex, answers=None):
        self.sex = Sex(Model.load(os.path.join(HERE, "model.npz")), sex)
        self.base, self.answers = load(base_path(sex)), answers or answers_path(sex)
        where = files.folder(sex)
        if not files.exists(where) or files.rendered(where)[3] != self.base["pool"]:
            sys.exit("the %s's %s is not rendered in %s: pick in the main checkout" % (sex, self.base["pool"], where))
        faces = files.rendered(where)[0]
        self.prior = dict(centre=faces.mean(0), spread=faces.std(0), candidates={}, picked=self.base["picks"],
                          faces=[dict(numbers=face, strengths={}) for face in faces])
        self.tried = taste.tried(self.sex)

    def kept(self):
        return candidates.kept(self.answers)

    def unanswered(self):
        """How many candidate features he has not answered yet, held at 0 until he does."""
        return len(set(candidates.names()) - set(candidates.answered(self.answers)))

    def keys(self, lines):
        """The candidates kept now or drawn on a sheet he picked from."""
        return sorted(set(self.kept()) | {key for line in lines for key in line["candidates"]})

    def centre(self, lines, kept):
        """The next sheet's centre: the average of every face he picked on the sheets `lines`, or the base
        face before he has picked any; and each kept candidate's average strength on those faces, within his
        strengths, or else his favourite."""
        picked = [line["faces"][i] for line in lines for i in line["picked"]]
        numbers = np.mean([face["numbers"] for face in picked], 0) if picked else np.asarray(self.base["numbers"])
        at = {}
        for key, (lowest, favourite, highest) in kept.items():
            had = [face["strengths"][key] for face in picked if key in face["strengths"]]
            at[key] = float(np.clip(np.mean(had), lowest, highest)) if had else favourite
        return numbers, at

    def draw(self, lines, rng):
        """The next sheet, from his picks on the sheets `lines`: its faces and how they were drawn, as Picks
        keeps them."""
        kept, keys = self.kept(), self.keys(lines)
        r, judged = narrowing([self.prior] + lines, keys, rng)
        numbers = len(self.tried[0])
        middle, at = self.centre(lines, kept)
        width = np.sqrt(r[:numbers]) * scales(self.sex.model)
        faces = middle + (np.stack([taste.draw(self.sex, rng) for _ in range(SHEET)]) - self.tried.mean(0)) * width
        drawn = {}
        for key, (lowest, _, highest) in kept.items():
            c, k = at[key], numbers + keys.index(key)
            q = float(np.sqrt(r[k]))
            drawn[key] = dict(centre=c, range=[c - q * (c - lowest), c + q * (highest - c)], r=float(r[k]))

        def strength(d):
            low, high = d["range"]
            return float(rng.triangular(low, d["centre"], high)) if high > low else d["centre"]

        rounded = lambda x: np.round(x, 5).tolist()
        return dict(sex=self.sex.name, drawn_from=len(lines), centre=rounded(middle),
                    spread=rounded(self.tried.std(0) * width), r=rounded(r[:numbers]),
                    candidates={key: {k: rounded(v) for k, v in d.items()} for key, d in drawn.items()},
                    shrinkage=judged, faces=[dict(numbers=rounded(face), strengths={
                        key: round(strength(d), 5) for key, d in drawn.items()}) for face in faces])

    def narrowest(self, sheet, count=4):
        """The sheet's `count` most narrowed directions, as [name, share of the full spread]."""
        named = list(zip(labels(self.sex.model), sheet["r"])) \
            + [(candidates.names()[key], d["r"]) for key, d in sheet["candidates"].items()]
        return [[name, round(float(np.sqrt(r)), 2)] for name, r in sorted(named, key=lambda nr: nr[1])][:count]


class Picks(Log):
    """The picks file: each line one sheet he picked from, as Rounds.draw drew it: its "sex", "drawn_from" how
    many sheets before it, its "centre", "spread" and "r" in each of a face's numbers, the "candidates" drawn
    ({key: their "centre", the "range" drawn within and "r"}), how r was judged ("shrinkage", narrowing) and
    its "faces", each its "numbers" and candidates' "strengths"; then its "sheet" number, the indices of the
    faces he "picked" and "at", the time."""

    def picks(self):
        return sum(len(line["picked"]) for line in self.lines)

    def submit(self, sheet, picked):
        self.add(dict(sheet, picked=sorted(set(picked)), at=time.strftime("%Y-%m-%dT%H:%M:%S")))


def render(path):
    """Renders the sheet drawn in `path` into the folder beside it: each face carries its candidates as more
    features of the model, in the paint the dev liked on the base face (candidates.lashed)."""
    from faces import build_faces as bf
    sheet, model = load(path), bf.current()
    keys, numbers = sorted(sheet["candidates"]), len(model.directions)
    if keys:
        moves = candidates.candidates(model, bf.EYE, {key.split("/")[0] for key in keys})
        model.directions = np.concatenate([model.directions, np.stack([moves[key][3] for key in keys]).astype(
            model.directions.dtype)])
    faces = np.array([face["numbers"][:numbers] + [face["strengths"][key] for key in keys] + face["numbers"][numbers:]
                      for face in sheet["faces"]])
    candidates.lashed(bf, model)
    bf.render_in(model, os.path.splitext(path)[0], faces, np.zeros(0), np.asarray(sheet["spread"]), 1.0,
                 "sheet %d" % sheet["sheet"], bf.style(sheet["sex"]), VIEWS, candidates.FACE)


if __name__ == "__main__":
    from sculpt.bl import opt
    render(opt("--sheet"))

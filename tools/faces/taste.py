"""The dev's taste in faces, learnt from his choices between pairs of them (numpy only).

A Bradley-Terry model over the face model's coefficients: he prefers face a to face b with probability
sigmoid(w . (a - b)). A coefficient moves the head by its component's standard deviation, so a prior on w
that is isotropic in shape gives w_k a variance in proportion to the share of the variance component k
explains, scaled so that two random faces differ by about PRIOR_LOGIT. The posterior is the Laplace
approximation at its mode. Each next pair is the one, among random pairs of the pool's faces, whose answer
is expected to tell the most about w (BALD); about REPEAT of them instead re-show an earlier pair, sides
swapped, to measure his consistency.

The answers live in ANSWERS, one JSON line each, written the moment he gives them.
"""
import json, math, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = os.path.join(HERE, "taste.jsonl")
POOL = os.path.join(HERE, "pool")              # build_faces.py --pool renders the faces shown here
POOL_SEED, POOL_SIZE = 7, 240
PRIOR_LOGIT = 2.0
REPEAT = 0.05
FIRST_REPEAT = 10                              # no pair is re-shown before this many answers
CANDIDATES = 4000
PROBIT = 1.7                                   # sigmoid(x) is close to Phi(x / PROBIT)
BALD_C = np.sqrt(np.pi * np.log(2) / 2)
ERF = np.vectorize(math.erf, otypes=[float])


def pool(model, seed=POOL_SEED, size=POOL_SIZE):
    """Coefficients of the faces the dev is shown."""
    rng = np.random.default_rng(seed)
    return np.stack([model.sample(rng) for _ in range(size)])


def load_pool(folder=POOL):
    """The rendered pool's faces and the prior on w for them."""
    with np.load(os.path.join(folder, "pool.npz")) as f:
        return f["faces"], prior(f["share"], float(f["spread"]))


def picture(i, folder=POOL):
    return os.path.join(folder, "%03d.png" % i)


def prior(share, spread):
    """Prior variances of w, for faces drawn at `spread`."""
    return share / share.sum() * PRIOR_LOGIT ** 2 / (2 * spread ** 2)


class Posterior:
    """Normal approximation to the posterior of w given that each winner beat its loser: mean, cov."""

    def __init__(self, prior_var, winners, losers, steps=30):
        d = np.asarray(winners, float).reshape(-1, len(prior_var)) - np.asarray(losers, float).reshape(-1, len(prior_var))
        precision0 = np.diag(1.0 / prior_var)
        w = np.zeros(len(prior_var))
        for _ in range(steps):
            p = 1.0 / (1.0 + np.exp(-d @ w))
            gradient = d.T @ (1.0 - p) - precision0 @ w
            hessian = precision0 + (d * (p * (1.0 - p))[:, None]).T @ d
            step = np.linalg.solve(hessian, gradient)
            w += step
            if np.abs(step).max() < 1e-9:
                break
        p = 1.0 / (1.0 + np.exp(-d @ w))
        self.mean = w
        self.cov = np.linalg.inv(precision0 + (d * (p * (1.0 - p))[:, None]).T @ d)

    def logit(self, d):
        """Mean and variance of w . d for differences d (..., K)."""
        return d @ self.mean, np.einsum("...i,ij,...j->...", d, self.cov, d)

    def information(self, d):
        """Expected information, in bits, an answer on each pair with difference d gives about w."""
        mean, var = self.logit(d)
        mean, var = mean / PROBIT, var / PROBIT ** 2
        p = 0.5 * (1.0 + ERF(mean / np.sqrt(2.0 * (1.0 + var))))
        entropy = -(p * np.log2(np.clip(p, 1e-12, 1)) + (1 - p) * np.log2(np.clip(1 - p, 1e-12, 1)))
        return entropy - BALD_C / np.sqrt(var + BALD_C ** 2) * np.exp(-mean ** 2 / (2 * (var + BALD_C ** 2)))

    def settled(self, rng, draws=400):
        """Expected cosine between w and the mean: 0 knows nothing of the direction, 1 knows it exactly."""
        return float(np.mean([cosine(w, self.mean) for w in rng.multivariate_normal(self.mean, self.cov, draws)]))



def cosine(a, b):
    return float(a @ b / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-300))


def best(posterior, model, rng, count, draws=4000):
    """The `count` faces, of `draws` random ones, furthest along the learnt direction, best first: faces the
    model could draw, with their other features left to chance. Returns their coefficients and the logits of
    his preferring each to the mean face."""
    faces = np.stack([model.sample(rng) for _ in range(draws)])
    score = faces @ posterior.mean
    keep = np.argsort(-score)[:count]
    return faces[keep], score[keep]


class Answers:
    """The answers file: each line is one answer, {"left", "right", "winner"} pool indices, the coefficients
    of the winning face "won" and the losing one "lost", "repeat_of" the line it re-asks or null, "seconds"
    he took and "at", the time."""

    def __init__(self, path=ANSWERS):
        self.path = path
        self.lines = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.lines = [json.loads(line) for line in f if line.strip()]

    def __len__(self):
        return len(self.lines)

    def add(self, line):
        self.lines.append(line)
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def undo(self):
        if self.lines:
            self.lines.pop()
            with open(self.path, "w", encoding="utf-8", newline="\n") as f:
                f.writelines(json.dumps(line, separators=(",", ":")) + "\n" for line in self.lines)

    def won(self):
        return np.array([line["won"] for line in self.lines], float)

    def lost(self):
        return np.array([line["lost"] for line in self.lines], float)

    def consistency(self):
        """How many re-shown pairs he answered as he did the first time, and how many were re-shown."""
        again = [line for line in self.lines if line["repeat_of"] is not None]
        return sum(line["winner"] == self.lines[line["repeat_of"]]["winner"] for line in again), len(again)

    def posterior(self, prior_var):
        return Posterior(prior_var, self.won(), self.lost())


class Session:
    """A sitting: shows pairs from the pool's faces (coefficients (P, K)) and records the answers."""

    def __init__(self, faces, prior_var, answers, rng):
        self.faces, self.prior_var, self.answers, self.rng = faces, prior_var, answers, rng
        self.posterior = answers.posterior(prior_var)
        self.pair = None

    def asked(self):
        return {frozenset((line["left"], line["right"])) for line in self.answers.lines}

    def repeatable(self):
        """Earlier first-time answers on this pool's faces that have not been re-shown."""
        again = {line["repeat_of"] for line in self.answers.lines}
        return [k for k, line in enumerate(self.answers.lines)
                if line["repeat_of"] is None and k not in again and line["left"] < len(self.faces)
                and line["right"] < len(self.faces)
                and np.allclose(self.faces[line["winner"]], line["won"], atol=1e-3)]

    def next(self):
        """The next pair: (left, right, repeat_of)."""
        repeatable = self.repeatable() if len(self.answers) >= FIRST_REPEAT else []
        if repeatable and self.rng.random() < REPEAT:
            k = int(self.rng.choice(repeatable))
            line = self.answers.lines[k]
            self.pair = (line["right"], line["left"], k)
        else:
            i, j = self.rng.integers(0, len(self.faces), (2, CANDIDATES))
            asked = self.asked()
            fresh = np.array([a != b and frozenset((a, b)) not in asked for a, b in zip(i, j)])
            i, j = i[fresh], j[fresh]
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
        if len(self.answers):
            line = self.answers.lines[-1]
            self.answers.undo()
            self.posterior = self.answers.posterior(self.prior_var)
            self.pair = (line["left"], line["right"], line["repeat_of"])
        return self.pair

    def status(self):
        agreed, again = self.answers.consistency()
        return dict(answers=len(self.answers), agreed=agreed, repeats=again,
                    settled=round(self.posterior.settled(self.rng), 3))

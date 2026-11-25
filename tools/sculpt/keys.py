"""What a figure's clips are keyed with: curves through (time, value) pairs.

A curve eases from key to key without overshooting, so a held value stays held. Looping curves take a phase
(0..1 round the loop); `held` curves take seconds and keep their first and last values beyond them.
"""
import numpy as np

FPS = 30


class Curve:
    def __init__(self, *keys, loop=True):
        t, v = np.array(sorted(keys), dtype=np.float64).T
        if loop:
            t, v = np.concatenate([t - 1.0, t, t + 1.0]), np.tile(v, 3)
        else:
            t, v = np.concatenate([t[:1] - 1.0, t, t[-1:] + 1.0]), np.concatenate([v[:1], v, v[-1:]])
        h, rise = np.diff(t), np.diff(v) / np.diff(t)
        slope = np.zeros(len(t))
        eases = rise[:-1] * rise[1:] > 0
        with np.errstate(divide="ignore", invalid="ignore"):
            mean = 3.0 * (h[:-1] + h[1:]) / ((2.0 * h[1:] + h[:-1]) / rise[:-1] + (h[1:] + 2.0 * h[:-1]) / rise[1:])
        slope[1:-1] = np.where(eases, mean, 0.0)
        self.loop, self.t, self.v, self.slope = loop, t, v, slope

    def __call__(self, phase):
        x = phase % 1.0 if self.loop else float(np.clip(phase, self.t[1], self.t[-2]))
        i = int(np.clip(np.searchsorted(self.t, x, side="right") - 1, 0, len(self.t) - 2))
        h = self.t[i + 1] - self.t[i]
        s = (x - self.t[i]) / h
        return (2 * s ** 3 - 3 * s ** 2 + 1) * self.v[i] + (s ** 3 - 2 * s ** 2 + s) * h * self.slope[i] \
            + (-2 * s ** 3 + 3 * s ** 2) * self.v[i + 1] + (s ** 3 - s ** 2) * h * self.slope[i + 1]


def times(n, *keys):
    """Keys for one nth of the loop, repeated through the rest of it."""
    return Curve(*((t + k / n, v) for k in range(n) for t, v in keys))


def stepped(move, *keys):
    """A looping curve that rests on each key's value, and passes to the next in the `move` of the loop before it."""
    keys = sorted(keys)
    rests = [(after + (after <= t) - move, v) for (t, v), (after, _) in zip(keys, keys[1:] + keys[:1])]
    return Curve(*keys, *rests)


def held(*keys):
    """Keys in seconds after the start of a move played once, which it begins at rest: (0, 0) is understood."""
    return Curve((0.0, 0.0), *keys, loop=False)


def at(curves, t):
    return {name: curve(t) for name, curve in curves.items()}


def sided(left, right):
    out = {name + "_l": value for name, value in left.items()}
    out.update({name + "_r": value for name, value in right.items()})
    return out


def both(controls):
    return sided(controls, controls)

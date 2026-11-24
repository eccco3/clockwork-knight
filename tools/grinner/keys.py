"""What the grinner's clips are keyed with: curves through (time, value) pairs, and the bearing every clip shares.

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


def twice(*keys):
    """Keys for half the loop, repeated in the other half."""
    return Curve(*keys, *((t + 0.5, v) for t, v in keys))


def swaying(*keys):
    """Keys for half the loop, mirrored in the other half."""
    return Curve(*keys, *((t + 0.5, -v) for t, v in keys))


def held(*keys):
    """Keys in seconds after the start of a move played once, which it begins at rest: (0, 0) is understood."""
    return Curve((0.0, 0.0), *keys, loop=False)


def at(curves, t):
    return {name: curve(t) for name, curve in curves.items()}


def glide(t, start, full, slow, stop):
    """0..1: gathers speed evenly from `start` to `full`, keeps it until `slow`, and brakes evenly to `stop`."""
    top = 1.0 / (0.5 * (full - start) + (slow - full) + 0.5 * (stop - slow))
    t = float(np.clip(t, start, stop))
    if t < full:
        return 0.5 * top * (t - start) ** 2 / (full - start)
    if t < slow:
        return top * (0.5 * (full - start) + t - full)
    return 1.0 - 0.5 * top * (stop - t) ** 2 / (stop - slow)


def thrown(t, start, end):
    """The height of a thing thrown at `start` that lands at `end`, as a share of its peak."""
    s = float(np.clip((t - start) / (end - start), 0.0, 1.0))
    return 4.0 * s * (1.0 - s)


def trod(t, travel, stands, steps):
    """A foot's foot_y while the root travels (travel: seconds -> metres), so that it never slides. The foot
    stands at each of `stands`, metres ahead of where the move began; each of `steps`, (lift, land, carried),
    takes it to the next, and `carried` (0..1 -> 0..1) is how far along it is, measured from the root."""
    for k, (lift, land, carried) in enumerate(steps):
        if t <= lift:
            return travel(t) - stands[k]
        if t < land:
            a, b = travel(lift) - stands[k], travel(land) - stands[k + 1]
            return a + (b - a) * carried((t - lift) / (land - lift))
    return travel(t) - stands[-1]


def sided(left, right):
    out = {name + "_l": value for name, value in left.items()}
    out.update({name + "_r": value for name, value in right.items()})
    return out


def both(controls):
    return sided(controls, controls)


_HANGING = dict(foot_x=0.012, spread=4.0, arm_hang=0.75, curl_pinky=24.0, curl_ring=19.0, curl_middle=16.0, curl_index=13.0,
                thumb_curl=8.0)
BEARING = dict(sided(dict(_HANGING, foot_yaw=4.0, arm_out=-7.0, elbow=6.0, wrist_curl=8.0),
                     dict(_HANGING, foot_yaw=7.0, arm_out=-9.0, elbow=13.0, wrist_curl=15.0, shoulder_up=3.0, curl_index=22.0)),
               hips_z=-0.002,neck_roll=2.0, head_roll=4.0)


def borne(controls):
    """The clip's controls on top of how the grinner always carries itself: crooked, one shoulder up."""
    return {name: controls.get(name, 0.0) + BEARING.get(name, 0.0) for name in {*controls, *BEARING}}

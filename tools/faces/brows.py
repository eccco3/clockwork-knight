"""The eyebrows painted on a face, shaped by the last of its numbers.

A brow is painted where it lies on the model's mean face: a band about a curve through its inner end, its
peak and its tail, thinning toward the tail. After a face's coefficients (model.py) come its brow numbers,
one for each of NAMES, in units of about what people commonly differ by; all zero, or left out, is the brow
every face wore before it had them.
"""
import numpy as np
from sculpt.num import smoothstep

NAMES = ("brows high", "brows arched", "brows slanted up", "brows thick", "brows long", "brows apart")
CURVE = ((0.013, 0.021, 0.0045), (0.038, 0.027, 0.0038), (0.058, 0.022, 0.0014))   # (x, z, half height) of the three
# What one unit does: lifts the brow; lifts its peak and drops its ends by half as much; lifts its tail and
# drops its inner end; thickens it by this share; moves the tail's end out; moves the inner end out.
HIGH, ARCHED, SLANTED, THICK, LONG, APART = 0.0013, 0.0012, 0.0013, 0.22, 0.003, 0.0016
FADE = 0.003                                   # the ends fade out over this length
DENSITY = 0.9


def brow(x, z, numbers=()):
    """How much of each point of the mean face is brow, from 0 to DENSITY: x from the midline, z up."""
    high, arched, slanted, thick, long, apart = np.pad(np.asarray(numbers, float), (0, len(NAMES) - len(numbers)))
    (x0, z0, h0), (x1, z1, h1), (x2, z2, h2) = CURVE
    xs = np.array([x0 + APART * apart, x1, x2 + LONG * long])
    zs = HIGH * high + np.array([z0 - 0.5 * ARCHED * arched - SLANTED * slanted, z1 + ARCHED * arched,
                                 z2 - 0.5 * ARCHED * arched + SLANTED * slanted])
    middle, half = np.polyval(np.polyfit(xs, zs, 2), x), np.interp(x, xs, np.array([h0, h1, h2]) * np.exp(THICK * thick))
    band = smoothstep(0.0, 1.0, (1.0 - np.abs(z - middle) / half) * 2.0)
    return DENSITY * band * smoothstep(xs[0], xs[0] + FADE, x) * smoothstep(xs[2], xs[2] - FADE, x)

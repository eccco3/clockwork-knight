"""The hair the faces wear, reckoned in numbers alone, without Blender, so that the face maker's session
(maker.py) hangs the same long hair from a head as the sheets do (build_faces.py, which lays the rest).

Long hair falls round the back from FALL_FROM degrees from the front, behind the ears, down to FALL_END
(sheet): from where the head is widest above FALL_WIDEST, sunk FALL_DIVE into the head above that, and
spreading out below FALL_FLARE. It is reckoned FALL_STEP apart (metres down, degrees round), made of rings
of FALL_RING points, ridged FALL_LOCKS times round a turn and waved FALL_WAVE apart. Angles round the head
are taken about an upright axis at y = AXIS_Y. STRAND_ROUND turns a strand's angle round into metres across
the strands, and a head's right side is SIDES on from its left.
"""
import numpy as np
from sculpt.num import smoothstep

AXIS_Y = -0.01
STRAND_ROUND, SIDES = 0.08, 1.0
FALL_FROM, FALL_END, FALL_WIDEST, FALL_INSET, FALL_DIVE, FALL_FLARE = 118.0, -0.26, -0.02, 0.0015, 0.008, -0.06
FALL_STEP, FALL_RING, FALL_LOCKS, FALL_WAVE = (0.002, 2.0), 128, 70, 0.045


def ramp(x):
    return smoothstep(0.0, 1.0, x)


def reach(v, top):
    """How far the head v (levelled) reaches out from the upright axis at y = AXIS_Y round the back, at each
    angle from FALL_FROM behind one ear to behind the other and each height from `top` down to FALL_END,
    FALL_STEP apart: the furthest any point does there, give or take a step round. Returns the angles, the
    heights and the reach (angles, heights)."""
    step, turn = FALL_STEP
    angles, heights = np.arange(FALL_FROM, 360.0 - FALL_FROM + 1e-9, turn), np.arange(top, FALL_END, -step)
    x, y, z = v[:, 0], v[:, 1] - AXIS_Y, v[:, 2]
    k = np.rint((np.degrees(np.arctan2(x, y)) % 360.0 - FALL_FROM) / turn).astype(int)
    j = np.minimum(((top - z) / step).astype(int), len(heights) - 1)
    out = np.zeros((len(angles), len(heights)))
    keep = (k >= 0) & (k < len(angles))
    np.maximum.at(out, (k[keep], j[keep]), np.hypot(x, y)[keep])
    wide = out.copy()
    wide[1:], wide[:-1] = np.maximum(wide[1:], out[:-1]), np.maximum(wide[:-1], out[1:])
    return angles, heights, wide


def sheet(v, thick, flare, locks, wave):
    """The long hair that hangs clear of the head v (levelled): a sheet round the back from behind one ear to
    behind the other, at each height FALL_INSET inside the furthest the head reaches there or above, so that
    it falls straight from where the head is widest, sunk into the head above that and rounded over the
    upper back; spreading out by `flare` toward the bottom of the picture and past it, `thick` down the
    middle of the back and rounded at its edges, ridged along its length `locks` deep and waved `wave` deep.
    Returns its points, its quads, rings of FALL_RING points from the top down, and where each point lies
    across the strands (metres)."""
    angles, z, out = reach(v, v[:, 2].max())
    widest = z[np.argmax(np.where(z > FALL_WIDEST, out, 0.0), axis=1)]
    out = np.maximum.accumulate(out, axis=1)
    for _ in range(30):
        out[:, 1:-1] = np.maximum(out[:, 1:-1], 0.25 * (out[:, :-2] + 2.0 * out[:, 1:-1] + out[:, 2:]))
    out = out - FALL_INSET - FALL_DIVE * ramp((z - widest[:, None]) / 0.02) + flare * ramp((FALL_FLARE - z) / 0.12)
    rows = z <= widest.max() + 0.02
    out, z = out[:, rows], z[rows, None]
    phi = np.linspace(0.0, 2.0 * np.pi, FALL_RING, endpoint=False)          # out round the back, and in again
    at = 0.5 * (1.0 - np.cos(phi)) * (len(angles) - 1)
    k = np.minimum(at.astype(int), len(angles) - 2)
    radius = out[k].T * (k + 1 - at) + out[k + 1].T * (at - k)
    a, side = np.radians(FALL_FROM + at * FALL_STEP[1]), np.sin(phi)
    r = (radius + 0.5 * thick * (np.sign(side) * np.abs(side) ** 0.4 - 1.0)
         + locks * np.sin(FALL_LOCKS * a) * np.maximum(side, 0.0)
         + wave * ramp((widest.max() - z) / 0.04) * np.sin(2.0 * np.pi * z / FALL_WAVE + 2.5 * np.sin(5.0 * a)))
    pts = np.stack([r * np.sin(a), AXIS_Y + r * np.cos(a), np.broadcast_to(z, r.shape)], -1).reshape(-1, 3)
    n, row = len(phi), len(phi) * np.arange(len(z) - 1)[:, None]
    ring = np.arange(n)
    quads = np.stack([row + ring, row + (ring + 1) % n, row + n + (ring + 1) % n, row + n + ring], -1).reshape(-1, 4)
    return pts, quads, np.broadcast_to(STRAND_ROUND * a + 2.0 * SIDES, r.shape).ravel()

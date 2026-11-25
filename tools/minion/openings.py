"""Openings cut through a sculpted piece to show the works behind it: windows, portholes and missing panels.

A window is an outline drawn flat on a frame that stands on the piece's surface, its z pointing out. The piece is
wrapped with an edge loop on every outline, the quads inside are left out, and the loop comes back as the
window's rim. Behind the rim is a well: its wall runs straight in to a floor the works stand on.
"""
import numpy as np
from sculpt import sdf as S, mesher, lattice, pieces as P

ON = 2e-4                                      # how far outside an outline its rim's points lie, and count as on it


# ---------------------------------------------------------------- outlines: (N,2) points -> metres, negative inside

def circle(r):
    return lambda xy: np.hypot(xy[:, 0], xy[:, 1]) - r


def tablet(hx, hy, r):
    """A rectangle with its corners rounded."""
    def f(xy):
        q = np.abs(xy) - (np.array([hx, hy]) - r)
        return np.hypot(np.maximum(q[:, 0], 0), np.maximum(q[:, 1], 0)) + np.minimum(q.max(-1), 0.0) - r
    return f


def arch(hx, hy):
    """A doorway: square below, a half-round above."""
    spring = hy - hx                           # where the half-round springs from
    below = moved(tablet(hx, 0.5 * (hy + spring), 0.2 * hx), 0.0, 0.5 * (spring - hy))
    return lambda xy: np.minimum(below(xy), np.hypot(xy[:, 0], xy[:, 1] - spring) - hx)


def oval(hx, hy):
    return lambda xy: (np.hypot(xy[:, 0] / hx, xy[:, 1] / hy) - 1.0) * min(hx, hy)


def shield(hx, hy, point):
    """A heater shield: a flat top `hy` above its middle, rounded at the corners, straight sides `hx` out, and
    below its middle two arcs that meet at a point `point` under it."""
    c = (point ** 2 - hx ** 2) / (2 * hx)      # how far beyond the middle each arc's centre lies
    top = tablet(hx, hy, 0.3 * hx)
    return lambda xy: np.where(xy[:, 1] > 0, top(xy), np.hypot(np.abs(xy[:, 0]) + c, xy[:, 1]) - (hx + c))


def torn(r, seed, rough=0.35):
    """A ragged hole about r across, as a blow leaves."""
    rng = np.random.default_rng(seed)
    waves = [(k, rng.uniform(0, 2 * np.pi), rng.uniform(0.3, 1.0) / k) for k in (2, 3, 5, 7)]

    def f(xy):
        a = np.arctan2(xy[:, 1], xy[:, 0])
        return np.hypot(xy[:, 0], xy[:, 1]) - r * (1 + rough * sum(w * np.sin(k * a + ph) for k, ph, w in waves) / 1.6)
    return f


def moved(outline, x, y):
    return lambda xy: outline(xy - (x, y))


def lean(outline, xy, eps=1e-5):
    """The way an outline grows at each point, as unit vectors in its plane."""
    g = np.stack([outline(xy + (eps, 0)) - outline(xy - (eps, 0)), outline(xy + (0, eps)) - outline(xy - (0, eps))], axis=-1)
    return g / np.maximum(np.hypot(g[:, 0], g[:, 1]), 1e-12)[:, None]


# ---------------------------------------------------------------- windows

class Window:
    """An outline on `frame`, which stands on a piece's surface with its z pointing out. It cuts only the
    surface within `reach` behind the frame, so the far side of the piece stays whole."""

    def __init__(self, frame, outline, reach=0.06):
        self.frame, self.outline, self.reach = frame, outline, reach

    def g(self, p):
        l = self.frame.l(p)
        return np.where(l[:, 2] > -self.reach, self.outline(l[:, :2]), 1.0)

    def wall(self, rim, depth):
        """The rim's points carried straight in to `depth` behind the frame, and the way the wall between faces."""
        l = self.frame.l(rim)
        foot = self.frame.w(np.column_stack([l[:, :2], np.full(len(l), -depth)]))
        return foot, self.frame.dir(np.column_stack([-lean(self.outline, l[:, :2]), np.zeros(len(l))]))


def _slide(field, g, p, steps=6):
    """The points moved over the surface of `field` onto the curve where g is ON."""
    for _ in range(steps):
        grad = lattice.grad(g, p, 5e-5)
        p = lattice.project(field, p - grad * ((g(p) - ON * 0.6) / np.maximum((grad * grad).sum(-1), 1e-9))[:, None], 2)
    return p


def _loops(quads):
    """The open edges of a mesh of quads, chained into loops of point indices. Each runs with its opening on the
    right. Where two openings meet at a point, a loop passes through it once for each."""
    edges = np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)])
    key = np.sort(edges, axis=1)
    _, inverse, count = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    follow = {}
    for a, b in edges[count[inverse.ravel()] == 1]:
        follow.setdefault(int(a), []).append(int(b))
    loops = []
    while follow:
        start = at = next(iter(follow))
        loop = []
        while not loop or at != start:
            loop.append(at)
            onward = follow[at]
            at = onward.pop()
            if not onward:
                del follow[loop[-1]]
        loops.append(np.array(loop))
    return loops


def opened(field, axis, extent, dims, windows, density=None, hidden=None, relax=12):
    """Wrap the sculpt `field` as mesher.wrap does, leaving out the quads inside every window and those wholly
    `hidden` (points -> bool). The lattice gathers along the rims. Returns verts, quads, normals, and each
    window's rim as indices into the verts, running anticlockwise seen from outside."""
    g = lambda p: np.min([w.g(p) for w in windows], axis=0)
    gather = lambda p: (1.0 if density is None else density(p)) + 5 * np.exp(-(g(p) / 0.012) ** 2)
    v, q, n = mesher.wrap(field, *axis, extent, dims, relax=relax, density=gather, snap=[(w.g, None, 5e-4) for w in windows])
    gone = g(v) < ON
    if hidden is not None:
        gone |= hidden(v)
    v, q, n = lattice.cull(v, q, gone, (n,))
    q = np.array(P.outward(v, q, n))
    inside = g(v) < 0
    v[inside] = _slide(field, g, v[inside])
    n[inside] = S.gradient(field, v[inside])
    loops = _loops(q)
    rims = []
    for w in windows:
        near = [loop for loop in loops if np.abs(w.g(v[loop])).max() < 10 * ON]
        assert len(near) == 1, "a window should leave one rim, not %d" % len(near)
        rims.append(near[0][::-1])
    return v, q, n, rims


def trace(window, field, spacing, grow=None):
    """Points about `spacing` apart round the window's outline, on the surface of `field` behind or before the
    frame, and the surface's normals there: the outline's true curve, which its rim only follows from corner to
    corner. `grow`, given the angle round the frame's z, scales the outline out from the frame's origin. The
    outline must be seen whole from that origin."""
    def crossing(inside, lo, hi):          # where each ray leaves what `inside` holds, by halving
        for _ in range(32):
            mid = 0.5 * (lo + hi)
            held = inside(mid)
            lo, hi = np.where(held, mid, lo), np.where(held, hi, mid)
        return lo

    angles = lambda count: 2 * np.pi * np.arange(count) / count
    ways = lambda a: np.stack([np.cos(a), np.sin(a)], axis=-1)
    radius = lambda way: crossing(lambda r: window.outline(way * r[:, None]) < 0, np.zeros(len(way)), np.full(len(way), 0.3))
    rough = ways(angles(64)) * radius(ways(angles(64)))[:, None]
    a = angles(max(12, int(np.linalg.norm(rough - np.roll(rough, 1, axis=0), axis=1).sum() / spacing)))
    way = ways(a)
    r = radius(way) * (1.0 if grow is None else grow(a))
    flat = window.frame.w(np.column_stack([way * r[:, None], np.zeros(len(way))]))
    up = window.frame.dir((0, 0, 1))
    p = flat + up * crossing(lambda t: field(flat + up * t[:, None]) < 0, np.full(len(way), -0.08), np.full(len(way), 0.08))[:, None]
    return p, S.gradient(field, p)


def well(window, rim, depth):
    """A well behind a window: its wall, from the rim's points straight in to `depth` behind the window's frame,
    and its floor there. Each is verts, faces and normals."""
    foot, face = window.wall(rim, depth)
    k = np.arange(len(rim))
    k1 = (k + 1) % len(rim)
    wv, wn = np.concatenate([rim, foot]), np.concatenate([face, face])
    out = np.tile(window.frame.dir((0, 0, 1)), (len(foot), 1))
    return (wv, P.outward(wv, np.stack([k, k1, len(rim) + k1, len(rim) + k], axis=1), wn), wn), (foot, [tuple(k)], out)

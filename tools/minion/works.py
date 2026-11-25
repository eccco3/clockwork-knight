"""Clockwork made by formula: toothed wheels, springs, levers and wire, in a local frame as sculpt.gen makes its
parts. Every corner carries its own normal, so a wheel's flats stay flat and a wire's few sides shade round, and a
face that only ever shows one side is made once.
"""
import numpy as np
from sculpt import pieces as P

# A tooth's outline within its share of the rim: where each point falls, and whether it is on the tip or the root.
TEETH = {"cog": ((0.0, 0), (0.27, 1), (0.73, 1)), "clock": ((0.0, 0), (0.5, 1)), "plain": ((0.0, 0),)}
DEPTH = {"cog": 0.42, "clock": 0.75, "plain": 0.0}     # a tooth's height, of the pitch between teeth


class Solid:
    """A mesh gathered face by face."""

    def __init__(self):
        self.v, self.n, self.f = [], [], []

    def _points(self, pts, normals):
        at = len(self.v)
        self.v += [np.asarray(p, dtype=np.float64) for p in pts]
        self.n += [np.asarray(n, dtype=np.float64) for n in normals]
        return np.arange(at, at + len(pts))

    def flat(self, pts, toward):
        """A flat polygon facing `toward`."""
        self.f.append(tuple(self._points(pts, [toward] * len(pts))))

    def band(self, a, b, na, nb=None, closed=False):
        """Quads between two rows of points, shaded by each point's normal."""
        ia, ib = self._points(a, na), self._points(b, na if nb is None else nb)
        for k in range(len(a) - (not closed)):
            k1 = (k + 1) % len(a)
            self.f.append((ia[k], ia[k1], ib[k1], ib[k]))

    def made(self):
        v, n = np.array(self.v), np.array(self.n)
        return v, P.outward(v, self.f, n), n


def solid(name, mat, made, frame, mirror=False):
    """A piece made with its normals, placed in `frame`, which its grain runs along."""
    v, q, n = made
    return dict(name=name, mat=mat, v=frame.w(v), q=q, n=frame.dir(n), grain=frame, mirror=mirror)


def ring(r, a):
    return np.stack([r * np.cos(a), r * np.sin(a)], axis=-1)


def lift(xy, z):
    return np.column_stack([xy, np.full(len(xy), z)])


def _zip(a, b):
    """Triangles filling the band between two rings whose points stand at the angles a and b, each ascending
    through one turn. Corners are (ring, index)."""
    turn = 2 * np.pi
    start = int(np.argmin(np.abs((np.asarray(b) - a[0] + np.pi) % turn - np.pi)))
    ua = [(x - a[0]) % turn for x in a] + [turn]
    first = (b[start] - a[0] + np.pi) % turn - np.pi
    ub = [first + (b[(start + k) % len(b)] - b[start]) % turn for k in range(len(b))] + [first + turn]
    i = j = 0
    out = []
    while i < len(a) or j < len(b):
        here = (0, i % len(a)), (1, (start + j) % len(b))
        if j == len(b) or (i < len(a) and ua[i + 1] <= ub[j + 1]):
            i += 1
            out.append((here[0], (0, i % len(a)), here[1]))
        else:
            j += 1
            out.append((here[0], (1, (start + j) % len(b)), here[1]))
    return out


def teeth_for(radius, pitch, least=5):
    """How many teeth a wheel of about `radius` carries at `pitch` between them, and the radius that makes."""
    count = max(least, int(round(2 * np.pi * radius / pitch)))
    return count, count * pitch / (2 * np.pi)


def wheel(teeth, tip, thick, kind="cog", spokes=0, lean=0.0, back=False, bore=0.0):
    """A toothed wheel about z, from z = 0 to its front face at z = thick. A cog's teeth are blunt; a clock
    wheel's are pointed, and lean `lean` of a tooth forward as an escape wheel's do; a plain wheel has none.
    With `spokes` its web is crossed out between rim and hub; with a `bore` it is a ring of that radius within,
    for whatever fills it. `back` gives it a far face too."""
    pitch = 2 * np.pi * tip / teeth
    root = tip - DEPTH[kind] * pitch
    form = TEETH[kind]
    ang = np.array([2 * np.pi * (k + a + lean * up) / teeth for k in range(teeth) for a, up in form])
    high = np.array([up for k in range(teeth) for a, up in form], dtype=bool)
    edge = ring(np.where(high, tip, root), ang)
    faces = []
    if len(form) > 1:                                            # each tooth, from its root to the next one's
        faces += [edge[np.arange(k * len(form), (k + 1) * len(form) + 1) % len(edge)] for k in range(teeth)]
    web_at, web = ang[~high], edge[~high]
    if spokes:
        r1, r2 = root - max(0.13 * tip, 0.0014), max(0.25 * tip, 0.0030)
        a1, a2, turn = 0.075 * tip / r1, 0.105 * tip / r2, 2 * np.pi / spokes
        gap = (turn - 2 * a1) / 3
        centres = turn * (np.arange(spokes) + 0.25)
        rim_at = np.concatenate([(t - a1, t + a1, t + a1 + gap, t + a1 + 2 * gap) for t in centres])
        rim, hub = ring(r1, rim_at), ring(r2, np.concatenate([(t - a2, t + a2) for t in centres]))
        rings = web, rim
        faces += [np.array([rings[r][i] for r, i in tri]) for tri in _zip(web_at, rim_at)]
        faces += [np.array([hub[2 * k], rim[4 * k], rim[4 * k + 1], hub[2 * k + 1]]) for k in range(spokes)]
        faces.append(hub)
    elif bore:
        hole = ring(bore, web_at)
        faces += [np.array([web[k - 1], web[k], hole[k], hole[k - 1]]) for k in range(len(web))]
    else:
        faces.append(web)
    s = Solid()
    for f in faces:
        s.flat(lift(f, thick), (0, 0, 1))
        if back:
            s.flat(lift(f, 0.0), (0, 0, -1))
    for a, b in zip(edge, np.roll(edge, -1, axis=0)):
        s.flat([(*a, thick), (*b, thick), (*b, 0.0), (*a, 0.0)], (b[1] - a[1], a[0] - b[0], 0.0))
    return s.made()


def pitch_radius(teeth, tip, kind="cog"):
    """The radius of the circle a wheel's teeth mesh on."""
    return tip * (1 - DEPTH[kind] * np.pi / teeth)


def stud(r, h, sides=6):
    """A screw head or pivot cap rising along z: a low cone, cut off flat."""
    a = 2 * np.pi * np.arange(sides) / sides
    out = np.column_stack([ring(0.8, a), np.full(sides, 0.6)])
    s = Solid()
    s.band(lift(ring(r, a), 0.0), lift(ring(0.62 * r, a), h), out, closed=True)
    s.flat(lift(ring(0.62 * r, a), h), (0, 0, 1))
    return s.made()


def spiral(r0, r1, turns, width, z, per_turn=10, back=False):
    """A spring coiled flat about z: a strip `width` wide winding out from r0 to r1, facing +z."""
    t = np.linspace(0.0, 1.0, int(round(turns * per_turn)) + 1)
    a, r = 2 * np.pi * turns * t, r0 + (r1 - r0) * t
    s = Solid()
    for face in ((0, 0, 1), (0, 0, -1))[:1 + back]:
        s.band(lift(ring(r, a), z), lift(ring(r + width, a), z), [face] * len(t))
    return s.made()


def slab(outline, z0, z1, back=False):
    """A flat plate cut to `outline`, (x, y) points running anticlockwise, from z0 up to its face at z1."""
    outline = np.asarray(outline, dtype=np.float64)
    s = Solid()
    s.flat(lift(outline, z1), (0, 0, 1))
    if back:
        s.flat(lift(outline, z0), (0, 0, -1))
    for a, b in zip(outline, np.roll(outline, -1, axis=0)):
        s.flat([(*a, z1), (*b, z1), (*b, z0), (*a, z0)], (b[1] - a[1], a[0] - b[0], 0.0))
    return s.made()


def bar(a, b, ra, rb=None, sides=3):
    """The outline of a bar between two points in the plane, its ends rounded to the radii ra and rb."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    along = np.arctan2(*(b - a)[::-1])
    sweep = np.linspace(-np.pi / 2, np.pi / 2, sides + 1)
    return np.concatenate([b + ring(ra if rb is None else rb, along + sweep), a + ring(ra, along + np.pi + sweep)])


def evenly(points, spacing):
    """A closed loop of points walked again in steps of about `spacing`."""
    pts = np.asarray(points, dtype=np.float64)
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.roll(pts, -1, axis=0) - pts, axis=1))])
    at = np.linspace(0.0, along[-1], max(8, int(round(along[-1] / spacing))), endpoint=False)
    ring = np.concatenate([pts, pts[:1]])
    return np.column_stack([np.interp(at, along, ring[:, k]) for k in range(3)])


def wire(points, radius, sides=4, closed=False):
    """A round wire along a polyline; closed, it is a ring."""
    pts = np.asarray(points, dtype=np.float64)
    count = len(pts)
    step = lambda k: pts[k % count if closed else min(max(k, 0), count - 1)]
    tang = np.array([step(k + 1) - step(k - 1) for k in range(count)])
    tang /= np.linalg.norm(tang, axis=1)[:, None]
    side = np.cross(tang[0], (0.0, 0.0, 1.0) if abs(tang[0][2]) < 0.9 else (1.0, 0.0, 0.0))
    sides_at = []
    for t in tang:                                               # carried along without twisting
        side = side - t * (side @ t)
        side /= np.linalg.norm(side)
        sides_at.append(side)
    twist = 0.0
    if closed:                                                   # what twist is left at the join is spread round the ring
        back = sides_at[-1] - tang[0] * (sides_at[-1] @ tang[0])
        twist = np.arctan2(np.cross(back, sides_at[0]) @ tang[0], back @ sides_at[0])
    around = 2 * np.pi * np.arange(sides) / sides
    rows = []
    for k, (p, t, u) in enumerate(zip(pts, tang, sides_at)):
        a = around + twist * k / count
        out = np.outer(np.cos(a), u) + np.outer(np.sin(a), np.cross(t, u))
        rows.append((p + radius * out, out))
    s = Solid()
    for (a, na), (b, nb) in zip(rows, rows[1:] + rows[:1] if closed else rows[1:]):
        s.band(a, b, na, nb, closed=True)
    if not closed:
        s.flat(rows[0][0], -tang[0])
        s.flat(rows[-1][0], tang[-1])
    return s.made()


def coil(length, radius, turns, gauge, per_turn=7, sides=3):
    """A coil spring along z from 0 to `length`, its wire `gauge` thick."""
    t = np.linspace(0.0, 1.0, int(round(turns * per_turn)) + 1)
    a = 2 * np.pi * turns * t
    return wire(np.column_stack([ring(radius, a), length * t]), gauge / 2, sides)

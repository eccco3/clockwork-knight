"""Clock works laid out on a floor: a train of wheels, each driving the next one's pinion, from the mainspring's
barrel or a great wheel to the escapement that checks it (the anchor, and the balance that times it) or to a fly
whose vanes the air brakes. Bridges hold arbors down, a crank drives a rod off toward his limbs, and where the works
are seen from all round a ribbed frame carries the arbors in place of a plate.

Wheels on one arbor after another stand on alternate levels, so each overlaps the one it drives. A seeded generator
draws the layout, so a seed always lays the same works. On the floor of a well, wheels may run under the wall:
what shows is a glimpse of more works beyond.

Everything comes back in groups, each with a rank: the lower, the more the works need it, so a figure short of
triangles sheds the highest first.
"""
import itertools
import numpy as np
from sculpt.gen import Frame
from . import works as W

PINION = 5                                     # a pinion's teeth
# The anchor's outline about its escape wheel, in the wheel's radius: the angles of its points from the way to
# its pivot, and how far out its back and its belly stand at each.
ANCHOR = np.radians((-58, -30, 0, 30, 58)), (1.22, 1.30, 1.50, 1.30, 1.22), (0.90, 1.08, 1.14, 1.08, 0.90)
ABOVE = 3.6                                    # where rods and bridges run over the wheels, in wheel thicknesses


class Bench:
    """The floor works are laid on: `frame` with its z rising from the floor, the floor's `outline` in the
    frame's plane and `reach`, about half its width, which sizes everything. In a well the works show their faces
    only; on a `bare` floor, seen from all round, they have backs too."""

    def __init__(self, name, rng, frame, outline, reach, bare=False):
        self.name, self.rng, self.frame, self.outline, self.reach, self.bare = name, rng, frame, outline, reach, bare
        self.pitch, self.thick = 0.24 * reach, max(0.0014, 0.046 * reach)
        self.pinion = PINION * self.pitch / (2 * np.pi)       # a pinion's radius
        self.placed, self.arbors, self.groups, self.number = [], [], [], itertools.count()

    def level(self, l):
        return (0.5 + 1.6 * l) * self.thick

    def named(self):
        return "%s_%d" % (self.name, next(self.number))

    def put(self, mat, made, c=(0.0, 0.0), z=0.0, turn=0.0):
        f = self.frame
        return W.solid(self.named(), mat, made, Frame(f.w((c[0], c[1], z)), f.dir((0, 0, 1)), f.dir((np.cos(turn), np.sin(turn), 0))))

    def stand(self, mat, made, c, z, turn):
        """A piece standing up off the floor: its own z runs along the floor the way `turn` points, its x up."""
        f = self.frame
        return W.solid(self.named(), mat, made, Frame(f.w((c[0], c[1], z)), f.dir((np.cos(turn), np.sin(turn), 0)), f.dir((0, 0, 1))))

    def wheel(self, mat, c, z, turn, thick=1.0, **shape):
        return self.put(mat, W.wheel(thick=thick * self.thick, back=self.bare, **shape), c, z, turn)

    def slab(self, mat, outline, z0, z1):
        return self.put(mat, W.slab(outline, z0, z1, self.bare))

    def within(self, c):
        return -self.outline(np.asarray(c)[None])[0]

    def free(self, c, r, l, inside, but=None):
        """Whether a wheel fits at c on level l, at least `inside` of its radius within the outline, clear of
        the others there `but` the one it meshes with."""
        return self.within(c) >= inside * r and all(
            np.hypot(*(c - at)) > r + other + 0.02 * self.reach for at, other, on in self.placed if on == l and at is not but)

    def beside(self, last, l, tip, inside):
        """A spot for a wheel of radius `tip` on level 1 - l whose pinion, on level l, meshes with the wheel
        `last`, (centre, teeth, tip); or None."""
        apart = W.pitch_radius(*last[1:]) + W.pitch_radius(PINION, self.pinion)
        spots = [last[0] + apart * W.ring(1.0, a) for a in self.rng.uniform(0, 2 * np.pi, 48)]
        return next((c for c in spots if self.free(c, tip, 1 - l, inside) and self.free(c, self.pinion, l, 0.0, last[0])), None)

    def arbor(self, rank, c, l, mat, driven=None, **shape):
        """A wheel at c on level l with its pivot's cap and, if it is `driven` from a level, its pinion there."""
        turn = self.rng.uniform(0, 2 * np.pi)
        pieces = [self.wheel(mat, c, self.level(l), turn, **shape)]
        self.placed.append((c, shape["tip"], l))
        self.arbors.append((c, shape["tip"], l))
        top = l
        if driven is not None:
            pieces.append(self.wheel("steel", c, self.level(driven), turn, 1.25, teeth=PINION, tip=self.pinion))
            self.placed.append((c, self.pinion, driven))
            top = max(l, driven)
        cap = W.stud(max(0.17 * shape["tip"], 0.9 * self.thick), 0.8 * self.thick)
        self.groups.append((rank, pieces + [self.put("steel", cap, c, self.level(top) + self.thick)]))


def train(b, last, l, count, rank, shape):
    """`count` arbors after the wheel `last`, (centre, teeth, tip) on level l, each wheel's pinion driven by the
    one before; shape(k, shrink) draws the k-th wheel's form, and smaller on another try. Returns the last wheel
    placed and its level."""
    for k in range(count):
        for shrink in (1.0, 0.85, 0.7):
            form = shape(k, shrink)
            c = b.beside(last, l, form["tip"], 0.45)
            if c is not None:
                b.arbor(rank + k, c, 1 - l, "brass", l, **form)
                last, l = (c, form["teeth"], form["tip"]), 1 - l
                break
    return last, l


def movement(name, rng, frame, outline, reach, wheels=3, peeking=2, bare=False, over=None, ways=None):
    """A going train on a Bench of these arguments, ended by its escapement. wheels: how many it has between the
    great wheel and the escape wheel. peeking: how many more show at the wall. over: what runs over the wheels,
    "bridge" or "crank", if anything; ways: the directions a crank's rod may leave in. Returns the Bench."""
    b = Bench(name, rng, frame, outline, reach, bare)
    teeth, tip = W.teeth_for(rng.uniform(0.44, 0.54) * reach, b.pitch, 9)
    c = next((c for c in rng.uniform(-0.6, 0.6, (60, 2)) * reach if b.free(c, tip, 0, 1.0)), np.zeros(2))
    b.arbor(1, c, 0, "brass", teeth=teeth, tip=tip, spokes=int(rng.integers(4, 7)))
    great = c, teeth, tip

    def form(k, shrink):
        teeth, tip = W.teeth_for(rng.uniform(0.31, 0.40) * reach * shrink, b.pitch, 7)
        return dict(teeth=teeth, tip=tip, spokes=int(rng.integers(3, 6)))
    last, l = train(b, great, 0, wheels, 3, form)
    escape = dict(teeth=int(rng.integers(12, 16)), kind="clock", lean=0.3, spokes=4)
    for shrink in (1.0, 0.85, 0.7):
        tip = rng.uniform(0.25, 0.30) * reach * shrink
        c = b.beside(last, l, tip, 0.45)
        if c is not None:
            b.arbor(2, c, 1 - l, "steel", l, tip=tip, **escape)
            break
    if c is None:                              # nowhere to mesh: it stands wherever there is room
        tip = 0.25 * reach
        c = next((c for c in rng.uniform(-0.8, 0.8, (80, 2)) * reach if b.free(c, tip, 1 - l, 0.6)), None)
        if c is not None:
            b.arbor(2, c, 1 - l, "steel", tip=tip, **escape)
    if c is not None:
        escapement(b, c, tip, 1 - l)
    peek(b, peeking)
    cover(b, over, great, ways)
    return b


def cover(b, over, wheel, ways=None):
    """Runs a bridge over the arbors well inside the floor, or a crank's rod off the wheel, as `over` says."""
    if over == "bridge":
        bridge(b, [a for a in b.arbors[1:] if b.within(a[0]) > 0.2 * b.reach])
    elif over == "crank":
        crank(b, wheel, ways)


def peek(b, count, rank=6):
    """Wheels running in under the wall from beyond it, of which a little shows."""
    for k in range(count):
        kind = ("cog", "clock")[int(b.rng.integers(2))]
        teeth, tip = W.teeth_for(b.rng.uniform(0.28, 0.44) * b.reach, b.pitch * (0.55 if kind == "clock" else 1.0), 7)
        c = next((c for c in b.rng.uniform(-1.4, 1.4, (80, 2)) * b.reach if b.free(c, tip, 0, -0.35) and b.within(c) < 0.3 * tip), None)
        if c is not None:
            b.arbor(rank + k, c, 0, "brass", teeth=teeth, tip=tip, kind=kind, spokes=int(b.rng.integers(4, 6)))


def escapement(b, c, tip, l):
    """The anchor over the escape wheel at c on level l, and the balance beside it under its cock, with its
    hairspring. The balance swings on top of everything, where it best clears the other arbors, and its cock
    stands its foot as far inside the floor as it can."""
    radius, thick = 0.34 * b.reach, b.thick
    spots = [(a, c + (1.30 * tip + 0.62 * radius) * W.ring(1.0, a)) for a in b.rng.uniform(0, 2 * np.pi, 32)]
    clear = lambda s: min([np.hypot(*(s[1] - at)) for at, _, _ in b.placed if at is not c] + [b.reach])
    a, at = max(spots, key=lambda s: clear(s) + 4 * min(0.0, b.within(s[1]) - radius))
    angles, back, belly = ANCHOR
    crescent = np.concatenate([tip * W.ring(np.array(back), a + angles), tip * W.ring(np.array(belly), a - angles)])
    z = b.level(l) + 1.1 * thick
    b.groups.append((2, [b.slab("steel", c + crescent, z, z + thick),
                         b.put("steel", W.stud(0.13 * tip, 0.7 * thick), c + 1.32 * tip * W.ring(1.0, a), z + thick)]))

    z = max(b.level(3), z + 1.4 * thick)
    spring = W.spiral(0.30 * radius, 0.74 * radius, 2.6, max(0.0005, 0.045 * radius), 0.0, back=b.bare)
    balance = [b.wheel("brass", at, z, a, 1.2, teeth=16, tip=radius, kind="plain", spokes=int(b.rng.integers(2, 4))),
               b.put("steel", spring, at, z + 1.35 * thick, a)]
    swing = b.rng.uniform(-0.9, 0.9)           # the cock reaches on away from the escape wheel, or back over the works
    foot = max((at + 1.5 * radius * W.ring(1.0, a + t) for t in (swing, -swing, np.pi + swing, np.pi - swing)), key=b.within)
    z += 1.8 * thick
    b.groups.append((1, balance + [b.slab("brass", W.bar(at, foot, 0.21 * radius, 0.27 * radius), z, z + thick),
                                   b.slab("brass", foot + W.ring(0.20 * radius, 2 * np.pi * np.arange(6) / 6), 0.0, z),
                                   b.put("lacquer", W.stud(0.11 * radius, 0.6 * thick), at, z + thick),
                                   b.put("steel", W.stud(0.15 * radius, 0.6 * thick), foot, z + thick)]))


def barrel(b, c, size, post, rank=1):
    """The mainspring's barrel at c, `size` across its teeth: its toothed drum, the spring showing through its
    crossed-out lid, the ratchet and click that hold its winding, and its arbor carried up to `post` above the
    floor for a key. Returns the drum as (centre, teeth, tip), for the wheels it drives."""
    thick, turn = b.thick, b.rng.uniform(0, 2 * np.pi)
    teeth, tip = W.teeth_for(size, b.pitch, 9)
    drum = 0.9 * (tip - W.DEPTH["cog"] * b.pitch)
    z = b.level(0)
    b.placed.append((c, tip, 0))
    b.arbors.append((c, tip, 0))
    b.groups.append((rank, [b.wheel("brass", c, z, turn, teeth=teeth, tip=tip),
                            b.wheel("brass", c, z + thick, turn, 2.2, teeth=16, tip=drum, kind="plain", spokes=3),
                            b.put("steel", W.spiral(0.30 * drum, 0.80 * drum, 3.5, 0.07 * drum, 0.0, 9), c, z + 2.9 * thick, turn)]))
    lid, hold = z + 3.2 * thick, 0.43 * size
    pivot = c + 1.42 * hold * W.ring(1.0, turn + 0.6)
    b.groups.append((rank + 1, [b.wheel("steel", c, lid, turn, teeth=10, tip=hold, kind="clock", lean=0.35),
                                b.slab("steel", W.bar(pivot, c + 0.98 * hold * W.ring(1.0, turn + 1.5), 0.20 * hold, 0.07 * hold),
                                       lid, lid + 0.8 * thick),
                                b.put("brass", W.stud(0.14 * hold, 0.6 * thick), pivot, lid + 0.8 * thick)]))
    top = lid + thick
    b.groups.append((rank, [b.put("brass", W.wire([(0, 0, top), (0, 0, max(post, top + thick))], 0.22 * hold, 6), c)]))
    return c, teeth, tip


def mainspring(name, rng, frame, outline, reach, post=0.0, peeking=2, bare=False):
    """The mainspring's barrel alone in the middle of a Bench of these arguments, and the wheels it drives,
    which in a well mostly run under the wall. Returns the Bench."""
    b = Bench(name, rng, frame, outline, reach, bare)
    c, teeth, tip = barrel(b, np.zeros(2), 0.60 * reach, post)
    for k in range(peeking):
        wheel, radius = W.teeth_for(rng.uniform(0.30, 0.44) * reach, b.pitch, 7)
        apart = W.pitch_radius(teeth, tip) + W.pitch_radius(wheel, radius)
        at = next((at for at in apart * W.ring(1.0, rng.uniform(0, 2 * np.pi, 24)) if b.free(at, radius, 0, -0.7, c)), None)
        if at is not None:
            b.arbor(4 + k, at, 0, "brass", teeth=wheel, tip=radius, spokes=int(rng.integers(3, 6)))
    return b


def motor(name, rng, frame, outline, reach, post=0.0, bare=False, over=None):
    """An automaton's motor on a Bench of these arguments: the mainspring's barrel at the middle, wound from
    `post` above it, driving two wheels and a fly whose vanes hold it to a steady pace, with `over` running over
    them as in a movement. Returns the Bench."""
    b = Bench(name, rng, frame, outline, reach, bare)
    drum = barrel(b, np.zeros(2), rng.uniform(0.55, 0.65) * reach, post)

    def form(k, shrink):
        teeth, tip = W.teeth_for(rng.uniform(0.38, 0.48) * reach * shrink, b.pitch, 7)
        return dict(teeth=teeth, tip=tip, spokes=int(rng.integers(3, 6)))
    last, l = train(b, drum, 0, 2, 3, form)
    fly(b, last, l)
    peek(b, 2)
    if len(b.arbors) > 1:
        cover(b, over, (b.arbors[1][0], 0, b.arbors[1][1]))
    return b


def fly(b, last, l, rank=2):
    """An air brake driven by the wheel `last`, (centre, teeth, tip) on level 1 - l: a pinion on an upright
    arbor, and a vane standing up off it on either side that the air holds back."""
    span, thick = 0.36 * b.reach, b.thick
    c = b.beside(last, l, 0.3 * span, 0.0)
    if c is None:
        return
    b.placed.append((c, b.pinion, l))
    turn = b.rng.uniform(0, 2 * np.pi)
    low = b.level(2) + 0.5 * thick
    high = low + 0.5 * span
    vane = [(low, -span), (high, -span), (high, span), (low, span)]
    b.groups.append((rank, [b.wheel("steel", c, b.level(l), turn, 1.25, teeth=PINION, tip=b.pinion),
                            b.put("steel", W.wire([(0, 0, 0.0), (0, 0, high + thick)], 0.6 * thick, 6), c),
                            b.stand("brass", W.slab(vane, -0.25 * thick, 0.25 * thick, back=True), c, 0.0, turn)]))


def bridge(b, arbors, rank=4):
    """A bar screwed down over the two largest of the `arbors` and on under the wall beyond the first, with a
    cap over each pivot it holds."""
    held = sorted(arbors, key=lambda a: -a[1])[:2]
    if len(held) < 2:
        return
    (c0, r0, _), (c1, r1, _) = held
    out = (c0 - c1) / max(np.hypot(*(c0 - c1)), 1e-9)
    end = c0 + out * next((t for t in np.linspace(0, 3, 61) * b.reach if b.within(c0 + out * t) < -0.08 * b.reach), 0.4 * b.reach)
    tail = c1 - out * 0.22 * b.reach
    z = ABOVE * b.thick
    wide = 0.11 * b.reach
    pieces = [b.slab("brass", W.bar(end, tail, wide, 0.7 * wide), z, z + 0.8 * b.thick),
              b.put("steel", W.stud(0.45 * wide, 0.5 * b.thick), tail, z + 0.8 * b.thick)]
    pieces += [b.put("lacquer", W.stud(0.30 * wide, 0.5 * b.thick), c, z + 0.8 * b.thick) for c in (c0, c1)]
    b.groups.append((rank, pieces))


def crank(b, wheel, ways=None, rank=3):
    """A crank pin on the wheel (centre, teeth, tip) and a connecting rod from it, running out under the wall,
    of the `ways` it may (angles on the floor; any if None), the way that leaves it clearest of the other arbors."""
    c, _, tip = wheel
    thick = b.thick
    ways = 2 * np.pi * np.arange(16) / 16 if ways is None else ways
    clearance = lambda a: min([np.hypot(*(at - c - 0.6 * tip * W.ring(1.0, a))) - r for at, r, _ in b.arbors if at is not c] + [b.reach])
    a = max(ways, key=clearance)
    pin = c + 0.55 * tip * W.ring(1.0, a)
    end = pin + W.ring(1.0, a) * next((t for t in np.linspace(0.2, 3, 57) * b.reach if b.within(pin + W.ring(1.0, a) * t) < -0.1 * b.reach),
                                       1.5 * b.reach)
    z = ABOVE * b.thick
    wide = 0.075 * b.reach
    b.groups.append((rank, [b.put("steel", W.wire([(0, 0, b.level(0) + thick), (0, 0, z + 1.3 * thick)], 0.45 * wide, 6), pin),
                            b.slab("steel", W.bar(pin, end, 1.35 * wide, wide), z, z + 0.7 * thick),
                            b.put("brass", W.stud(0.8 * wide, 0.5 * thick), pin, z + 1.3 * thick)]))


def column(name, rng, frame, outline, reach, half):
    """Wheels one above another up a slot `half` long each way along the frame's y, each meshing with the next
    tooth to tooth, on alternate levels, as a spine of works. Returns the Bench."""
    b = Bench(name, rng, frame, outline, reach)
    last = None
    while last is None or last[0][1] < half:
        teeth, tip = W.teeth_for(rng.uniform(0.8, 1.1) * reach, b.pitch, 8)
        y = -half if last is None else last[0][1] + W.pitch_radius(*last[1:]) + W.pitch_radius(teeth, tip)
        l = len(b.arbors) % 2
        b.arbor(3 + l, np.array([0.0, y]), l, ("brass", "steel")[l], teeth=teeth, tip=tip, spokes=(0, 3, 4, 5)[int(rng.integers(4))])
        last = np.array([0.0, y]), teeth, tip
    return b


def ribbed(b, hx, hy, mat, rank=0):
    """A frame behind the works on a bare floor, in place of a plate: a rail up either side, `hx` out and `hy`
    up and down, and between them a rib across at every arbor's height, where a boss carries the arbor."""
    wide, thick = 0.050 * b.reach, b.thick
    heights = []
    for y in sorted(c[1] for c, _, _ in b.arbors if b.within(c) > 0):
        if not heights or y - heights[-1] > 3 * wide:
            heights.append(y)
    pieces = [b.slab(mat, W.bar((sx * hx, -hy), (sx * hx, hy), wide), -thick, 0.0) for sx in (-1, 1)]
    pieces += [b.slab(mat, W.bar((-hx, y), (hx, y), 0.8 * wide), -thick - 0.0003, -0.0003) for y in heights]
    for c, _, _ in b.arbors:
        y = min(heights, key=lambda h: abs(h - c[1]), default=c[1])
        if abs(y - c[1]) > 1e-9:                # off its rib: a strut down to it
            pieces.append(b.slab(mat, W.bar((c[0], y), c, 0.7 * wide), -thick - 0.0006, -0.0006))
        pieces.append(b.slab(mat, c + W.ring(1.9 * wide, 2 * np.pi * np.arange(10) / 10), -1.6 * thick, 0.0004))
    pieces += [b.put("steel", W.stud(1.4 * wide, 0.6 * thick), (sx * hx, y), 0.0) for sx in (-1, 1) for y in heights + [-hy, hy]]
    b.groups.append((rank, pieces))

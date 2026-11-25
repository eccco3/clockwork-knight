"""The minion's variants: the same soldier with his clockwork showing.

A variant is named flavour:seed, as open_chest:3. Its flavour sets what may be opened and how often, in FLAVOURS;
its seed draws one design from those settings, and always the same one. The contact sheet shows SHEET, numbered
in order from 1.

A design is groups of pieces, each with a rank and the names of the body's pieces it replaces. Rank 0 is what an
opening cannot do without and always stays. The rest go in by rank while the triangle ceiling has room, and what
does not fit leaves the body as it was. Before anything is shed the body gives up a little of its own detail, down
the steps of DETAILS, so every variant keeps the budget whatever it opens.
"""
import zlib
import numpy as np
from sculpt import sdf as S, gen, pieces as P
from sculpt.sdf import V
from sculpt.gen import Frame
from . import body, openings as O, works as W
from .movement import movement, mainspring, motor, column, ribbed
from .body import UP, FWD, BACK, LEFT, UPRIGHT, part

# What a flavour may set. front and back: the windows his breast and his back may have, of which the seed picks
# one; None leaves them whole. over: what may run over a movement's wheels, picked likewise. joints: the chance,
# for knees and for elbows, of a wheel on the joint's pin. bare: the limbs that may be stripped to struts, and the
# chance of each. rings: the chance of toothed rings under his shoulder caps. crest: of a wheel for his helmet's
# crest. brass: of plate in brass for lacquer. wear: the chance of each mark of a hard campaign, which also strips
# limbs on one side only.
PLAIN = dict(front=(None,), back=(None,), over=(None,), joints=0.0, bare=(), rings=0.0, crest=0.0, brass=0.0, wear=0.0)
FLAVOURS = {
    "open_chest": dict(front=("round", "arch", "door", "oval", "shield"), back=("key", None), over=("bridge", "crank", None),
                       joints=0.4),
    "skeleton": dict(front=("frame",), over=("crank",), joints=0.9,
                     bare=(("thigh", 0.8), ("upperarm", 0.6), ("forearm", 0.6))),
    "open_back": dict(front=(None, None, "porthole"), back=("door", "door", "spine", "key+spine"), over=("bridge", None),
                      joints=0.3, rings=0.3),
    "brass": dict(front=("porthole", "heart", "round", "oval"), back=("key", None), over=("bridge", None), joints=0.8,
                  rings=0.9, crest=0.8, brass=1.0),
    "dress": dict(front=("porthole", "heart", "twin"), back=("key", "key", None)),
    "field": dict(front=("torn",), back=(None, None, "torn"), wear=0.6, bare=(("forearm", 0.5),)),
}
SEEDS = 6
SHEET = ["%s:%d" % (flavour, seed) for flavour in FLAVOURS for seed in range(1, SEEDS + 1)]
DETAILS = (1.0, 0.95, 0.9, 0.85, 0.8)          # the body's detail, as body.parts takes it, from all of it to the least a variant leaves
LATTICE = (12, 8, 14)                          # an opened cuirass's lattice: coarser than the whole one's, and gathered at its rims
HEM = 0.698                                    # an opened cuirass's hem, let down inside his belt, where so coarse a lattice cannot spoil its curve
BEAD = 0.008                                   # the spacing of the points round the bead on a window's rim
CHIPS = 0.004                                  # and round the bare wood about a torn hole
COG, KEY_PLATE = ("chest_cog", "chest_cog_boss"), ("chest_key_plate",)
FRAME = 0.742, 0.925                           # a chest opened to a frame: the heights of its base's top and its yoke's underside
# A limb stripped to a strut: its material, its length, the knob left at its joint and the cuff at its far end as
# lathe profiles, the cuff's measured from the far end, how far out its rods stand, and its spring's radius.
STRUTS = {
    "thigh": ("navy", float(np.linalg.norm(body.KNEE - body.HIP)),
              gen.arc(0.0, 0.046, 180, 70, 4) + [(0.050, 0.0500), (0.060, 0.0470), (0.063, 0.0)],
              [(-0.052, 0.0), (-0.049, 0.0375), (-0.012, 0.0360), (-0.005, 0.0300), (-0.004, 0.0)], 0.031, 0.015),
    "upperarm": ("wood", body.UPPER_ARM, gen.arc(0.0, 0.045, 180, 75, 4) + [(0.040, 0.0440), (0.048, 0.0410), (0.051, 0.0)],
                 [(-0.042, 0.0), (-0.039, 0.0320), (-0.012, 0.0310), (-0.005, 0.0265), (-0.004, 0.0)], 0.025, 0.012),
    "forearm": ("wood", body.FOREARM, [(0.008, 0.0), (0.009, 0.0230), (0.030, 0.0325), (0.040, 0.0315), (0.043, 0.0)],
                [(-0.040, 0.0), (-0.037, 0.0245), (-0.012, 0.0222), (-0.004, 0.0215), (-0.003, 0.0)], 0.019, 0.0095),
}
SIDES = {1: "l", -1: "r"}


class Design:
    """What a variant changes: `groups` of (rank, pieces, the names of the body's pieces they replace), the paired
    pieces of which only one side is kept, in `halved`, and the `livery`: (how a name starts, a material, the
    material its pieces wear instead). `over` is what runs over the wheels of its movements."""

    def __init__(self, name):
        self.rng = np.random.default_rng(zlib.crc32(name.encode()))
        self.groups, self.halved, self.livery, self.over = [], {}, [], None

    def pick(self, options):
        return options[int(self.rng.integers(len(options)))]

    def chance(self, odds):
        return self.rng.uniform() < odds

    def add(self, rank, *pieces, replaces=()):
        self.groups.append((rank, list(pieces), tuple(replaces)))

    def ranked(self, groups):
        for rank, pieces in groups:
            self.add(rank, *pieces)


class Mirrored:
    """The mirror image of a frame, for the grain of a piece that is the mirror image of one cut in it."""

    def __init__(self, frame):
        self.frame = frame

    def l(self, p):
        return self.frame.l(p * P.MIRROR)


def side(pc, sx):
    """Only the left of a paired piece, or only the right if sx is -1."""
    if sx > 0:
        return dict(pc, mirror=False)
    v, q, n = list(P.sides(pc))[1]
    return dict(pc, v=v, q=q, n=n, mirror=False, grain=Mirrored(pc["grain"]))


def triangles(pieces):
    """The triangles the build makes of the pieces: a plate given thickness gains a far face and an edge."""
    total = P.triangles(pieces)
    for pc in pieces:
        if pc.get("thickness"):
            edges = np.sort(np.concatenate([np.stack([f, np.roll(f, -1)], axis=1) for f in map(np.array, pc["q"])]), axis=1)
            total += P.triangles([pc]) + 2 * (np.unique(edges, axis=0, return_counts=True)[1] == 1).sum() * (1 + pc["mirror"])
    return total


def fit(figure, design, ceiling):
    """The figure as the design has it, within `ceiling` triangles if it can be; how many groups had to be shed,
    and the triangles left over, fewer than none if what may not be shed is already too much."""
    figure = [side(pc, design.halved[pc["name"]]) if pc["name"] in design.halved else pc for pc in figure]
    cost = {pc["name"]: triangles([pc]) for pc in figure}
    room, gone, added, shed = ceiling - sum(cost.values()), set(), [], 0
    for rank, pieces, replaces in sorted(design.groups, key=lambda group: group[0]):
        net = triangles(pieces) - sum(cost[name] for name in replaces if name not in gone)
        if rank and net > room:
            shed += 1
            continue
        room -= net
        gone.update(replaces)
        added += pieces
    out = [pc for pc in figure if pc["name"] not in gone] + added
    for start, old, new in design.livery:
        out = [dict(pc, mat=new) if pc["name"].startswith(start) and pc["mat"] == old else pc for pc in out]
    return out, shed, room


def parts(name, ceiling):
    """The pieces of the variant called `name`, flavour:seed, in at most `ceiling` triangles."""
    d = Design(name)
    compose(d, {**PLAIN, **FLAVOURS[name.split(":")[0]]})
    for detail in DETAILS:
        out, shed, room = fit(body.parts(detail), d, ceiling)
        if not shed and room >= 0:
            break
    assert room >= 0, "%s needs more than %d triangles for what it cannot shed" % (name, ceiling)
    print("WORKS %s: body detail %.2f, %d groups, %d shed, %d triangles to spare" % (name, detail, len(d.groups), shed, room))
    return out


def compose(d, s):
    """Draw a design from a flavour's settings."""
    brass = d.chance(s["brass"])
    trim = "steel" if brass else "brass"
    d.over = d.pick(s["over"])
    front, back = d.pick(s["front"]), d.pick(s["back"])
    if front == "frame":
        frame(d, trim)
    else:
        sites = opened(d, FRONTS, front) + opened(d, BACKS, back)
        if sites:
            cuirass(d, sites, trim)
    if d.chance(s["joints"]):
        geared(d, "shin_knee", body.leg_frames()[1], body.KNEE_BALL, ("shin_knee_pin_out",), mirror=True)
    if d.chance(s["joints"]):
        for sx, at in SIDES.items():
            geared(d, "forearm_%s_elbow" % at, body.arm_frames(sx)[1], body.ELBOW_BALL, ("forearm_%s_elbow_pin_out" % at,))
    lame = d.pick((1, -1))
    for limb, odds in s["bare"]:
        if d.chance(odds):
            bare(d, limb, (lame,) if s["wear"] else (1, -1))
    for sx in SIDES:
        if d.chance(s["rings"]):
            ringed(d, sx, trim)
    if d.chance(s["crest"]):
        crest(d, trim)
    if brass:
        d.livery += [(start, "lacquer", "brass") for start in ("chest_cuirass", "upperarm", "thigh_tasset")]
        d.livery += [("hips_lame", "lacquer", "brass")] * d.chance(0.5) + [("head_helm", "wood_dark", "brass")] * d.chance(0.4)
    if d.chance(s["wear"]):
        capless(d, -lame)
    if d.chance(s["wear"]):
        d.halved["thigh_tasset"] = d.pick((1, -1))
    if d.chance(s["wear"]):
        patch(d, d.pick((1, -1)))
    if d.chance(s["wear"]):
        strap(d, -lame)
    if d.chance(0.6 * s["wear"]):
        peg(d, d.pick((1, -1)))


# ---------------------------------------------------------------- the chest

class Site:
    """An opening in his cuirass: a point inside it and the way out from there, the opening's outline, about half
    its width as `reach`, and the `depth` of the well behind it, which fill(design, site, floor) furnishes, given the
    frame of the well's floor, with ranked groups. `edge` is what runs round its rim: a "bead" of the trim's metal,
    the bare wood a blow leaves "chipped", or nothing; `replaces` names what the opening takes the place of."""

    def __init__(self, name, inside, toward, outline, reach, fill, depth=None, edge="bead", replaces=()):
        self.name, self.inside, self.toward, self.outline, self.reach, self.fill = name, inside, toward, outline, reach, fill
        self.depth = 0.6 * reach + 0.004 if depth is None else depth
        self.edge, self.replaces = edge, replaces


def going(wheels, over=True, peeking=2):
    """Fills a window with a movement of `wheels` between its great wheel and its escape wheel, under whatever
    the design runs over wheels if `over`, and `peeking` more wheels running in under the wall."""
    return lambda d, s, floor: movement(s.name, d.rng, floor, s.outline, s.reach, wheels, peeking,
                                        over=d.over if over else None).groups


def wound(d, s, floor):
    """Fills a window with the mainspring, its arbor up to the key."""
    return mainspring(s.name, d.rng, floor, s.outline, s.reach, post=s.depth - 0.002).groups


def driven(d, s, floor):
    """Fills a window with an automaton's motor, wound by the key."""
    return motor(s.name, d.rng, floor, s.outline, s.reach, post=s.depth - 0.002, over=d.over).groups


def spine(d, s, floor):
    """Fills the slot down his spine with a column of wheels from end to end."""
    return column(s.name, d.rng, floor, s.outline, s.reach, SPINE[1] - s.reach).groups


HEART = S.normalize(V(0.35, -1, 0))            # the way out of his chest over his heart
SPINE = 0.018, 0.048                           # the slot down his spine: half its width and half its length
FRONTS = {
    "round": [Site("chest_works", V(0, 0, 0.872), FWD, O.circle(0.055), 0.055, going(2), replaces=COG)],
    "arch": [Site("chest_works", V(0, 0, 0.862), FWD, O.arch(0.048, 0.072), 0.052, going(3), replaces=COG)],
    "door": [Site("chest_works", V(0, 0, 0.862), FWD, O.tablet(0.052, 0.066, 0.014), 0.054, going(3), replaces=COG)],
    "oval": [Site("chest_works", V(0, 0, 0.866), FWD, O.oval(0.046, 0.064), 0.050, going(3), replaces=COG)],
    "shield": [Site("chest_works", V(0, 0, 0.894), FWD, O.shield(0.050, 0.030, 0.068), 0.052, going(3), replaces=COG)],
    "porthole": [Site("chest_works", V(0, 0, 0.888), FWD, O.circle(0.031), 0.031, going(1, False), replaces=COG)],
    "heart": [Site("chest_works", V(0.046, 0, 0.898), HEART, O.circle(0.027), 0.027, going(0, False), replaces=COG)],
    "twin": [Site("chest_works", V(0, 0, 0.850), FWD, O.circle(0.031), 0.031, going(1, False), replaces=COG),
             Site("chest_beat", V(0, 0, 0.917), FWD, O.circle(0.020), 0.020, going(0, False))],
}
BACKS = {
    "key": [Site("chest_spring", body.KEY, BACK, O.circle(0.036), 0.034, wound, depth=0.024, replaces=KEY_PLATE)],
    "door": [Site("chest_motor", body.KEY, BACK, O.tablet(0.055, 0.065, 0.012), 0.055, driven, replaces=KEY_PLATE)],
    "spine": [Site("chest_spine", V(0, 0, 0.772), BACK, O.tablet(*SPINE, 0.010), SPINE[0], spine, depth=0.016, edge=None)],
}
BACKS["key+spine"] = BACKS["key"] + BACKS["spine"]


def opened(d, kinds, kind):
    """The sites of the window `kind` of those in `kinds`, or of a torn hole, or none."""
    if kind == "torn":
        return [torn(d, kinds is FRONTS)]
    return list(kinds[kind]) if kind else []


def torn(d, front):
    """A ragged hole low on one side, the lacquer knocked off round it, with a little of a movement behind it.
    Where the hole is, his side curves away too fast to hide wheels under its edge."""
    sx = d.pick((1, -1))
    outline = O.torn(0.042 if front else 0.036, int(d.rng.integers(1 << 30)))
    if front:
        return Site("chest_works", V(sx * 0.030, 0, 0.850), FWD, outline, 0.040, going(1, False, 0), depth=0.034, edge="chipped",
                    replaces=COG)
    return Site("chest_hole", V(sx * 0.042, 0, 0.800), BACK, outline, 0.036, going(1, False, 0), depth=0.032, edge="chipped")


def cuirass(d, sites, trim):
    """The cuirass opened at each site, with its well and works."""
    windows = [O.Window(Frame(body.on(body.cuirass, s.inside, s.toward), s.toward, np.cross(UP, s.toward)), s.outline) for s in sites]
    neck = body.NECK.o[:2]
    hidden = lambda p: (p[:, 2] < HEM + 0.004) | ((p[:, 2] > 0.990) & (np.hypot(*(p[:, :2] - neck).T) < 0.034))
    field = lambda p: body.cuirass(p, HEM)
    v, q, n, rims = O.opened(field, *body.CUIRASS, LATTICE, windows, body.armhole_rim, hidden)
    pieces = [W.solid("chest_cuirass", "lacquer", (v, q, n), UPRIGHT)]
    for s, window, rim in zip(sites, windows, rims):
        if s.edge == "bead":
            p, out = O.trace(window, field, BEAD)
            pieces.append(W.solid(s.name + "_bezel", trim, W.wire(p + 0.0008 * out, 0.0030, 4, closed=True), UPRIGHT))
        elif s.edge == "chipped":
            pieces.append(chipped(s.name + "_chips", window, field, d.rng))
        wall, floor = O.well(window, v[rim], s.depth)
        pieces += [W.solid(s.name + "_well", "wood_dark", wall, UPRIGHT), W.solid(s.name + "_floor", "wood_dark", floor, UPRIGHT)]
        f = window.frame
        groups = s.fill(d, s, Frame(f.w((0, 0, -s.depth)), f.dir((0, 0, 1)), f.dir((1, 0, 0))))
        d.ranked([(rank, works) for rank, works in groups if not poking(works, field)])
    d.add(0, *pieces, replaces=sum((s.replaces for s in sites), ("chest_cuirass",)))


def poking(pieces, field):
    """Whether any of the pieces would stand out of the sculpt `field`, through his cuirass beside a window or
    above its rim, where the cuirass curves away faster than the works under it sink."""
    return bool((field(np.concatenate([pc["v"] for pc in pieces])) > -0.0005).any())


def chipped(name, window, field, rng):
    """A ragged band of bare wood round a hole in the sculpt `field`, where the blow knocked the lacquer off."""
    waves = [(k, rng.uniform(0, 2 * np.pi), rng.uniform(0.5, 1.0) / np.sqrt(k)) for k in (3, 5, 9, 14)]
    grow = lambda a: 1.07 + 0.12 * np.abs(sum(w * np.sin(k * a + phase) for k, phase, w in waves))
    (inner, n0), (outer, n1) = O.trace(window, field, CHIPS), O.trace(window, field, CHIPS, grow)
    band = W.Solid()
    band.band(inner + 0.0005 * n0, outer + 0.0005 * n1, n0, n1, closed=True)
    return W.solid(name, "wood", band.made(), UPRIGHT)


def frame(d, trim):
    """His cuirass taken away but for the yoke his arms and neck are set in, which stands on four pillars over a
    base at his belt. Between them the movement fills his chest on a frame of ribs, with the mainspring's barrel
    behind it, its arbor running back to the key."""
    low, high = FRAME
    axis, oval = body.TRUNK
    yoke = lambda p: S.smax(body.cuirass(p), S.plane(p, V(0, 0, high), body.DOWN), 0.005)
    span = (V(-0.07, 0.004, 0.5 * (high + 0.998)), V(0.07, 0.004, 0.5 * (high + 0.998))), (0.15, 0.09, 0.05)
    base = [(low - 0.036, 0.0), (low - 0.036, 0.0870), (low - 0.006, 0.0850), (low, 0.0790), (low, 0.0)]
    tall = high - low + 0.004
    pillar = [(0.0, 0.0), (0.0, 0.0075), (0.009, 0.0042), (tall - 0.009, 0.0042), (tall, 0.0075), (tall, 0.0)]
    d.add(0, body.sculpted("chest_yoke", "lacquer", yoke, *span, (12, 6, 4), density=body.armhole_rim),
          part("chest_base", "lacquer", gen.lathe(base, 16, sy=oval), axis),
          *[part("chest_pillar_%d" % k, trim, gen.lathe(pillar, 6), Frame(V(0.058, 0.004 + y, low - 0.002), UP, LEFT), True)
            for k, y in enumerate((-0.036, 0.036))], replaces=("chest_cuirass",) + COG + KEY_PLATE)
    hx, hy = 0.068, 0.5 * (high - low)
    plate = Frame(V(0, 0.010, 0.5 * (high + low)), FWD, LEFT)
    works = movement("chest_works", d.rng, plate, O.tablet(hx, hy, 0.014), 0.066, 3, 0, bare=True, over=d.over,
                     ways=np.radians(np.linspace(50, 130, 9)))      # a crank drives up into the yoke, toward his arms
    ribbed(works, hx, hy, trim)
    d.ranked(works.groups)
    behind = Frame(plate.w((0, body.KEY[2] - plate.o[2], -0.006)), BACK, np.cross(UP, BACK))
    key = body.on(body.cuirass, body.KEY, BACK)[1] - 0.002
    d.ranked(mainspring("chest_spring", d.rng, behind, O.circle(0.070), 0.046, post=key - behind.o[1], bare=True).groups)


# ---------------------------------------------------------------- joints and limbs

def geared(d, name, frame, r, replaces=(), mirror=False, rank=3):
    """A wheel on the outer end of the pin of a ball joint of radius r, whose frame's x the pin lies along."""
    seat = body.pin(frame, 1, r)
    thick = 0.0045
    cap = Frame(seat.w((0, 0, thick)), seat.dir((0, 0, 1)), seat.dir((1, 0, 0)))
    d.add(rank, W.solid(name + "_gear", "brass", W.wheel(9, 0.84 * r, thick, back=True), seat, mirror),
          W.solid(name + "_gear_cap", "steel", W.stud(0.30 * r, 0.0030), cap, mirror), replaces=replaces)


def bare(d, limb, sides):
    """The limb stripped to a strut on each of `sides`: a knob at its joint and a cuff at its far end, joined by
    three brass rods about a piston in its spring. Thighs go as a pair, and their tassets with them."""
    mat, long, knob, cuff, out, coil = STRUTS[limb]
    cuff = [(long + z, r) for z, r in cuff]
    z0, z1 = knob[-1][0] - 0.004, cuff[0][0] + 0.004
    paired = limb == "thigh"
    for sx in (1,) if paired else sides:
        name = limb if paired else "%s_%s" % (limb, SIDES[sx])
        frame = body.leg_frames()[0] if paired else body.arm_frames(sx)[limb == "forearm"]
        rods = [W.wire([(*out * W.ring(1.0, a), z0), (*out * W.ring(1.0, a), z1)], 0.0032, 4) for a in 2 * np.pi * (np.arange(3) + 0.25) / 3]
        spring = Frame(frame.w((0, 0, z0)), frame.dir((0, 0, 1)), frame.dir((1, 0, 0)))
        d.add(3, part(name + "_knob", mat, gen.lathe(knob, 12), frame, paired), part(name + "_cuff", mat, gen.lathe(cuff, 12), frame, paired),
              *[W.solid("%s_rod_%d" % (name, k), "brass", rod, frame, paired) for k, rod in enumerate(rods)],
              W.solid(name + "_piston", "steel", W.wire([(0, 0, z0), (0, 0, z1)], 0.0048, 5), frame, paired),
              W.solid(name + "_spring", "steel", W.coil(z1 - z0, coil, (z1 - z0) / 0.034, 0.0040, 6), spring, paired),
              replaces=(name, "thigh_tasset") if paired else (name,))


def ringed(d, sx, mat):
    """A toothed ring under a shoulder cap, its teeth standing out all round the cap's rim."""
    cap = body.cap_frame(sx)
    seat = Frame(cap.w((0, 0, 0.008)), cap.dir((0, 0, 1)), cap.dir((1, 0, 0)))
    d.add(4, W.solid("upperarm_%s_ring" % SIDES[sx], mat, W.wheel(24, 0.064, 0.005, back=True, bore=0.046), seat))


def crest(d, mat):
    """A wheel standing fore and aft through the crown of his helmet, in place of its boss."""
    axis = body.HELM[0]
    seat = Frame(axis.w((0, 0, body.CROWN - 0.028)) - LEFT * 0.003, LEFT, FWD)
    d.add(2, W.solid("head_crest", mat, W.wheel(14, 0.056, 0.006, back=True), seat), replaces=("head_helm_boss",))


# ---------------------------------------------------------------- a hard campaign

def capless(d, sx):
    """A shoulder cap lost, and the wheel its joint turns on left bare."""
    at = SIDES[sx]
    geared(d, "upperarm_%s_shoulder" % at, body.arm_frames(sx)[0], 0.045, ("upperarm_%s_cap" % at, "upperarm_%s_cap_boss" % at), rank=0)


def patch(d, sx):
    """A plate of bare wood riveted over his flank."""
    yaw, height = np.radians(np.linspace(16, 46, 5)) * sx, np.linspace(0.770, 0.834, 5)
    skin = np.array([[body.on(body.cuirass, V(0, 0, z), V(np.sin(a), -np.cos(a), 0)) for z in height] for a in yaw[::sx]])
    out = S.gradient(body.cuirass, skin.reshape(-1, 3)).reshape(skin.shape)
    rivets = [W.solid("chest_patch_rivet_%d%d" % (i, j), "steel", W.stud(0.0036, 0.0022), Frame(skin[i, j] + 0.0045 * out[i, j], out[i, j], UP))
              for i in (1, 3) for j in (1, 3)]
    d.add(1, part("chest_patch", "wood", gen.patch(skin + 0.0045 * out, skin + 0.0005 * out), UPRIGHT), *rivets)


def strap(d, sx):
    """A leather strap buckled round an upper arm."""
    band = [(0.100, 0.0390), (0.100, 0.0450), (0.118, 0.0440), (0.118, 0.0380)]
    d.add(2, part("upperarm_%s_strap" % SIDES[sx], "leather", gen.lathe_ring(band, 12), body.arm_frames(sx)[0]))


def peg(d, sx):
    """A leg lost below the knee, and a turned peg shod in brass in its place."""
    side = V(sx, 1, 1)
    shin = Frame(body.KNEE * side, (body.ANKLE - body.KNEE) * side, LEFT)
    ground = body.KNEE[2] / -shin.dir((0, 0, 1))[2]
    turned = [(0.016, 0.0), (0.018, 0.0300), (0.034, 0.0400), (0.066, 0.0400), (0.080, 0.0300), (0.090, 0.0170),
              (0.6 * ground, 0.0130), (ground - 0.030, 0.0110), (ground - 0.0005, 0.0105), (ground, 0.0)]
    shoe = [(ground - 0.030, 0.0100), (ground - 0.030, 0.0132), (ground - 0.002, 0.0126), (ground - 0.002, 0.0100)]
    band = [(0.040, 0.0390), (0.040, 0.0424), (0.056, 0.0424), (0.056, 0.0390)]
    for name in ("shin_trousers", "shin_boot", "foot"):
        d.halved[name] = -sx
    d.add(0, part("shin_peg", "wood", gen.lathe(turned, 12), shin), part("shin_peg_shoe", "brass", gen.lathe_ring(shoe, 12), shin),
          part("shin_peg_band", "steel", gen.lathe_ring(band, 12), shin))

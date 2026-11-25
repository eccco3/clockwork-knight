"""The minion's body: a small clockwork soldier of the knight's side, an adult man two thirds her height.

He is a wooden figure like her, and for three reasons. He comes off the same bench: the Clockmaker's automata are
carved wood with brass works, and an ally cut from her timber reads as hers at a glance, against the grinners'
pale skin and rags. Turned limbs and rigid plates are the cheapest forms the toolkit makes, and many of him share
the field. And every piece is rigid on one segment, so a few bones will move him without skinning.

His design is a toy soldier's: limbs turned from pale wood on ball joints with brass axle caps, tall black
lacquered boots, a black kettle helmet rimmed in brass, and a cuirass, shoulder caps and skirt lacquered in the
crimson of the hall's banner, whose gold cog he wears on his breast. His face is a carved block with bead eyes
and a moustache; his proportions, not his likeness, make him a grown man.

World frame as the knight's: +X his left, -Y forward, +Z up, metres, feet on z = 0. He stands to attention with
the spear grounded in his right fist. Each piece's name starts with the segment that carries it: chest, hips,
head, thigh, shin, foot, upperarm, forearm or hand.
"""
import numpy as np
from sculpt import sdf as S, mesher, gen, lattice, pieces as P
from sculpt.sdf import V
from sculpt.gen import Frame

UP, DOWN, FWD, BACK, LEFT = V(0, 0, 1), V(0, 0, -1), V(0, -1, 0), V(0, 1, 0), V(1, 0, 0)
UPRIGHT = Frame(V(0, 0, 0), UP, LEFT)
KNIGHT_HEIGHT = 1.792
HEIGHT = KNIGHT_HEIGHT * 2 / 3                 # to the crown of his helmet

# ---------------------------------------------------------------- landmarks (left side)

HIP, KNEE, ANKLE = V(0.060, 0.004, 0.612), V(0.062, -0.006, 0.332), V(0.064, 0.008, 0.052)
SHOULDER = V(0.135, 0.004, 0.945)
SKULL = V(0, -0.006, 1.100)
TRUNK = Frame(V(0, 0.004, 0), UP, LEFT), 0.76  # the axis his hips are turned on, and how they are pressed oval
CORE = 0.050                                   # the radius his hips are bored out to, out of sight
NECK = Frame(V(0, -0.001, 0), UP, LEFT)
GORGET = 1.006                                 # the top of the brass collar his neck turns in
HELM = Frame(V(0, -0.002, 1.128), UP, LEFT), (0.93, 1.07)   # his helmet's axis from the root of its brim, and its oval
UPPER_ARM, FOREARM = 0.215, 0.175
# How he carries each arm, by the sign of its side: the way its upper arm runs, its forearm, and its knuckles.
# The left hangs at his side. The right is bent to hold the spear upright, its fist level.
CARRY = {1: (V(0.10, 0.03, -1), V(0.05, -0.20, -1), V(0.05, -0.20, -1)),
         -1: (V(-0.12, 0.16, -1), V(-0.04, -1, -0.50), V(-0.05, -1, 0))}
HOLLOW = V(-0.003, 0, 0.036)                   # the hollow of a fist in the hand's frame
CAP = 0.058, 1.06, 0.92                        # a shoulder cap: its radius, and how it is pressed wide and low


def arm_frames(sx):
    """One arm's upper arm, forearm and hand. Each frame's z runs from its joint down the segment and its x
    points away from his body; the hand's z runs to the knuckles, and its y to the left thumb's side."""
    upper, fore, knuckles = CARRY[sx]
    shoulder = SHOULDER * V(sx, 1, 1)
    elbow = shoulder + S.normalize(upper) * UPPER_ARM
    wrist = elbow + S.normalize(fore) * FOREARM
    return Frame(shoulder, upper, LEFT * sx), Frame(elbow, fore, LEFT * sx), Frame(wrist, knuckles, LEFT * sx)


GRIP = arm_frames(-1)[2].w(HOLLOW)             # where the spear's shaft passes through his right fist


# ---------------------------------------------------------------- making pieces

def part(name, mat, made, frame, mirror=False, **finish):
    """A piece made by formula in `frame`, which its grain runs along."""
    return dict(name=name, mat=mat, v=frame.w(made[0]), q=made[1], n=None, grain=frame, mirror=mirror, **finish)


def sculpted(name, mat, field, axis, extent, dims, frame=UPRIGHT, grain=None, mirror=False, flip=1, density=None,
             hidden=None):
    """A piece sculpted in `frame` as `field` has it, or mirrored across the frame's x and z if `flip` is -1.
    Quads that `hidden` finds wholly out of sight are left out."""
    v, q, n = mesher.wrap(field, *axis, extent, dims, relax=12, density=density)
    if hidden is not None:
        v, q, n = lattice.cull(v, q, hidden(v), (n,))
    side = V(1, flip, 1)
    v, n = frame.w(v * side), frame.dir(n * side)
    return dict(name=name, mat=mat, v=v, q=P.outward(v, q, n), n=n, grain=grain or frame, mirror=mirror)


def on(field, origin, toward):
    """The point where the ray from `origin`, inside a sculpt, leaves it toward `toward`."""
    return S.hug(field, origin, S.normalize(toward), UP, 1, 0.0, 0.0, off=0.0)[0]


def ball(name, mat, frame, r, segs, mirror=False):
    return part(name, mat, gen.lathe(gen.arc(0.0, r, 0, 180, segs // 2 + 1), segs), frame, mirror)


def stud(name, frame, size, mirror=False):
    """A brass dome rising along the frame's z."""
    return part(name, "brass", gen.dome(size, size * 0.55, 8, 2), frame, mirror)


def axle(name, frame, r, mirror=False):
    """The brass caps on both ends of the pin a ball joint turns on: the frame's x."""
    return [stud("%s_%s" % (name, end), Frame(frame.w((sx * (r - 0.003), 0, 0)), frame.dir((sx, 0, 0)), frame.dir((0, 0, 1))),
                 0.38 * r, mirror) for end, sx in (("out", 1), ("in", -1))]


# ---------------------------------------------------------------- trunk

def cuirass(p):
    q = S.mirror_x(p)
    d = S.smin(S.ellipsoid(p, V(0, 0.000, 0.895), V(0.120, 0.086, 0.120)),                       # chest
               S.ellipsoid(p, V(0, 0.002, 0.770), V(0.090, 0.068, 0.110)), 0.060)                # waist
    d = S.smin(d, S.ellipsoid(q, V(0.078, 0.006, 0.934), V(0.060, 0.060, 0.042)), 0.040)         # shoulders
    d = S.smin(d, S.cone(q, V(0, 0.008, 0.990), V(0.094, 0.006, 0.958), 0.036, 0.030), 0.030)    # the slope from neck to shoulder
    d = S.smin(d, S.ellipsoid(q, V(0.047, -0.054, 0.898), V(0.054, 0.035, 0.047)), 0.035)        # the chest's two plates
    d = S.smin(d, S.ellipsoid(p, V(0, 0.040, 0.900), V(0.098, 0.046, 0.085)), 0.040)             # shoulder blades
    d = S.smax(d, S.plane(p, V(0, 0, 0.706), DOWN), 0.008)
    d = S.smax(d, S.plane(p, V(0, 0, 0.998), UP), 0.010)
    return S.ssub(d, S.sphere(q, SHOULDER + V(0.006, 0, 0), 0.045), 0.006)                       # where the arms seat


def chest():
    """The crimson cuirass with the hall's cog on its breast, the gorget, and the winding key between his shoulder blades."""
    out = [sculpted("chest_cuirass", "lacquer", cuirass, (V(0, 0, 0.780), V(0, 0, 0.930)), (0.15, 0.10, 0.16), (16, 10, 16)),
           part("chest_gorget", "brass", gen.lathe_ring([(GORGET - 0.014, 0.036), (GORGET - 0.014, 0.047), (GORGET - 0.007, 0.0495),
                                                         (GORGET, 0.046), (GORGET, 0.036)], 16, sy=0.95), NECK)]
    breast = Frame(on(cuirass, V(0, 0, 0.900), FWD), FWD, LEFT)
    out.append(part("chest_cog", "brass", gen.gear(10, 0.0165, 0.0210), Frame(breast.w((0, 0, 0.0030)), FWD, LEFT),
                    thickness=-0.0160))
    out.append(stud("chest_cog_boss", Frame(breast.w((0, 0, 0.0030)), FWD, LEFT), 0.0075))

    spine = Frame(on(cuirass, V(0, 0.01, 0.890), BACK) - BACK * 0.002, BACK, LEFT)
    out.append(part("chest_key_plate", "brass", gen.lathe_ring([(0.0, 0.012), (0.0, 0.021), (0.004, 0.022), (0.007, 0.019),
                                                                (0.007, 0.012)], 12), spine))
    out.append(part("chest_key_shaft", "brass", gen.lathe([(0.0, 0.0), (0.0, 0.0125), (0.006, 0.0125), (0.009, 0.0060),
                                                           (0.046, 0.0052), (0.050, 0.0078), (0.054, 0.0052), (0.054, 0.0)], 8), spine))
    out.append(part("chest_key_neck", "brass", gen.box((0.0075, 0.0028, 0.0100)), Frame(spine.w((0, 0, 0.060)), BACK, LEFT)))
    for sx in (1, -1):
        bow = Frame(spine.w((sx * 0.0225, 0, 0.0700)), spine.dir((0, 1, 0)), spine.dir((1, 0, 0)))
        out.append(part("chest_key_bow_%d" % sx, "brass", gen.lathe_ring([(-0.0030, 0.0180), (0.0, 0.0235), (0.0030, 0.0180),
                                                                         (0.0, 0.0125)], 12), bow))
    return out


def hips():
    """His belt and the two lacquered lames under it, turned solid: his legs come out of the lower one's flat underside."""
    axis, oval = TRUNK
    turned = lambda section: gen.lathe_ring(section, 20, sy=oval)
    out = [part("hips_belt", "leather", turned([(0.692, 0.074), (0.6935, 0.0885), (0.7125, 0.0885), (0.714, 0.074)]), axis),
           part("hips_lame_upper", "lacquer", turned([(0.695, CORE), (0.695, 0.0865), (0.630, 0.1065), (0.627, 0.1050),
                                                      (0.627, CORE)]), axis),
           part("hips_lame_upper_bead", "brass", turned([(0.626, 0.1040), (0.631, 0.1090), (0.636, 0.1045)]), axis),
           part("hips_lame_lower", "lacquer", turned([(0.645, CORE), (0.645, 0.0920), (0.565, 0.1245), (0.560, 0.1230),
                                                      (0.560, CORE)]), axis),
           part("hips_lame_lower_bead", "brass", turned([(0.558, 0.1215), (0.563, 0.1270), (0.568, 0.1220)]), axis)]
    front = axis.w(V(0, -0.0885 * oval, 0.703))
    out.append(part("hips_buckle", "brass", gen.lathe_ring([(0.0, 0.009), (0.0, 0.014), (0.0030, 0.0145), (0.0050, 0.012),
                                                            (0.0050, 0.009)], 4), Frame(front, FWD, LEFT + UP)))
    return out


# ---------------------------------------------------------------- legs

def boot(p):
    x = ANKLE[0]
    d = S.smin(S.sphere(p, V(x, 0.030, 0.034), 0.031),
               S.cone(p, V(x, 0.008, 0.054), V(x, -0.070, 0.026), 0.032, 0.022), 0.020)          # heel and instep
    d = S.smin(d, S.ellipsoid(p, V(x, -0.076, 0.022), V(0.034, 0.045, 0.022)), 0.018)            # toe
    return S.smax(d, S.plane(p, V(0, 0, 0), DOWN), 0.004)


def legs():
    """Thighs of pale wood on ball joints, and black boots to the knee with a brass band round their tops."""
    thigh = Frame(HIP, KNEE - HIP, LEFT)
    long = np.linalg.norm(KNEE - HIP)
    prof = gen.arc(0.0, 0.046, 180, 70, 4) + [(0.050, 0.0520), (0.105, 0.0535), (0.175, 0.0465), (0.235, 0.0395),
                                               (long - 0.012, 0.0360), (long - 0.005, 0.0300), (long - 0.004, 0.0)]
    out = [part("thigh", "wood", gen.lathe(prof, 16), thigh, True)]

    shin = Frame(KNEE, ANKLE - KNEE, LEFT)
    long = np.linalg.norm(ANKLE - KNEE)
    out.append(ball("shin_knee", "wood", shin, 0.037, 12, True))
    out += axle("shin_knee_pin", shin, 0.037, True)
    prof = [(0.018, 0.0), (0.020, 0.0300), (0.040, 0.0440), (0.047, 0.0445), (0.058, 0.0405), (0.100, 0.0430),
            (0.170, 0.0365), (0.235, 0.0300), (long + 0.006, 0.0310), (long + 0.007, 0.0)]
    out.append(part("shin_boot", "wood_dark", gen.lathe(prof, 16), shin, True))
    out.append(part("shin_boot_band", "brass", gen.lathe_ring([(0.039, 0.0420), (0.040, 0.0462), (0.047, 0.0466), (0.048, 0.0420)],
                                                              16), shin, True))
    out.append(sculpted("foot", "wood_dark", boot, (V(ANKLE[0], 0.030, 0.030), V(ANKLE[0], -0.075, 0.024)), (0.04, 0.10, 0.04),
                        (5, 9, 5), grain=Frame(ANKLE, FWD, LEFT), mirror=True))
    return out


# ---------------------------------------------------------------- arms

def fist(l):
    """A closed left fist in the hand's frame: x the back of the hand, y the thumb's side, z to the knuckles."""
    d = S.box(l, HOLLOW, V(0.019, 0.026, 0.026), 0.012)
    d = S.smin(d, S.ellipsoid(l, HOLLOW + V(-0.017, 0.011, 0.006), V(0.009, 0.016, 0.012)), 0.008)     # the thumb, folded over the fingers
    return S.smin(d, S.sphere(l, V(0, 0, 0), 0.0215), 0.006)                                            # the wrist's ball


def arm(sx, side):
    """One arm: a shoulder cap of crimson lacquer over a ball joint, turned upper arm and forearm, and a fist."""
    upper, fore, hand = arm_frames(sx)
    prof = gen.arc(0.0, 0.045, 180, 75, 4) + [(0.045, 0.0445), (0.095, 0.0425), (0.155, 0.0345), (UPPER_ARM - 0.012, 0.0310),
                                               (UPPER_ARM - 0.005, 0.0265), (UPPER_ARM - 0.004, 0.0)]
    out = [part("upperarm_" + side, "wood", gen.lathe(prof, 14), upper)]
    cap = Frame(upper.o + UP * 0.002, UP * 0.84 + LEFT * sx * 0.55, BACK)
    dome = [(z * CAP[2], r) for z, r in gen.arc(0.0, CAP[0], 0, 72, 5)]
    hollow = [(0.62 * CAP[0], 0.0)]            # coned out underneath, so its rim hangs clear of the arm
    out.append(part("upperarm_%s_cap" % side, "lacquer", gen.lathe(dome + hollow, 14, sy=CAP[1]), cap))
    out.append(stud("upperarm_%s_cap_boss" % side, Frame(cap.w((0, 0, CAP[0] * CAP[2] - 0.001)), cap.dir((0, 0, 1)), BACK), 0.0085))

    out.append(ball("forearm_%s_elbow" % side, "wood", fore, 0.030, 10))
    out += axle("forearm_%s_elbow_pin" % side, fore, 0.030)
    prof = [(0.008, 0.0), (0.009, 0.0230), (0.030, 0.0325), (0.065, 0.0335), (0.120, 0.0270), (FOREARM - 0.012, 0.0222),
            (FOREARM - 0.004, 0.0215), (FOREARM - 0.003, 0.0)]
    out.append(part("forearm_" + side, "wood", gen.lathe(prof, 14), fore))
    out.append(part("forearm_%s_band" % side, "brass", gen.lathe_ring([(FOREARM - 0.034, 0.0225), (FOREARM - 0.033, 0.0262),
                                                                       (FOREARM - 0.019, 0.0248), (FOREARM - 0.018, 0.0210)], 14), fore))
    out.append(sculpted("hand_" + side, "wood", fist, (HOLLOW - V(0, 0, 0.024), HOLLOW + V(0, 0, 0.014)), (0.024, 0.030, 0.040),
                        (4, 5, 6), hand, flip=sx))
    return out


# ---------------------------------------------------------------- head

BRIM = 0.0985                                  # his helmet's brim, as a radius before pressing
BOSS = 0.0090                                  # the boss on its crown, whose top is his height
CROWN = HEIGHT - HELM[0].o[2] - 0.55 * BOSS + 0.001


def face(p):
    q = S.mirror_x(p)
    d = S.ellipsoid(p, SKULL, V(0.051, 0.061, 0.066))
    d = S.smin(d, S.ellipsoid(p, SKULL + V(0, -0.014, -0.048), V(0.041, 0.045, 0.036)), 0.030)             # jaw
    d = S.smin(d, S.box(p, SKULL + V(0, -0.047, -0.071), V(0.019, 0.010, 0.010), 0.008), 0.016)            # a square chin
    d = S.smin(d, S.tube(q, [SKULL + V(0, -0.060, 0.004), SKULL + V(0.032, -0.050, 0.006)], 0.0075), 0.012)   # brow
    d = S.smin(d, S.cone(p, SKULL + V(0, -0.058, 0.002), SKULL + V(0, -0.075, -0.026), 0.0060, 0.0105), 0.008)  # nose
    d = S.ssub(d, S.sphere(q, SKULL + V(0.021, -0.066, -0.008), 0.0115), 0.006)                            # eye sockets
    d = S.smin(d, S.ellipsoid(q, SKULL + V(0.050, 0.006, -0.016), V(0.006, 0.011, 0.016)), 0.006)          # ears
    return S.smin(d, S.cone(p, SKULL + V(0, 0.006, -0.030), NECK.w((0, 0, 0.985)), 0.0350, 0.0365), 0.012)  # the neck, down into his gorget


def head():
    """His carved head and neck with bead eyes and a moustache, under a black kettle helmet rimmed in brass."""
    axis, (sx, sy) = HELM
    features = SKULL + V(0, -0.060, -0.016)
    out = [sculpted("head", "wood", face, (SKULL + V(0, 0, -0.060), SKULL + V(0, 0, 0.020)), (0.06, 0.07, 0.11), (11, 11, 14),
                    density=lambda p: 1 + 3 * np.exp(-(S.length(p - features) / 0.045) ** 2),
                    hidden=lambda v: (v[:, 2] > axis.o[2] + 0.012) | (v[:, 2] < GORGET - 0.006)),
           ball("head_eye", "wood_dark", Frame(SKULL + V(0.021, -0.0570, -0.008), LEFT, UP), 0.0072, 10, True),
           part("head_moustache", "wood_dark", gen.tube(SKULL + V((0.0015, -0.0720, -0.0345), (0.0140, -0.0690, -0.0375),
                                                                  (0.0270, -0.0600, -0.0450)), [0.0062, 0.0056, 0.0030], 6),
                UPRIGHT, True)]

    dome = [(0.010 + (CROWN - 0.010) * np.sin(t), 0.0585 * np.cos(t)) for t in np.radians((0, 20, 39, 56, 71, 82, 90))]
    prof = [(0.016, 0.0), (0.000, 0.0500), (-0.006, 0.0640), (-0.0160, 0.0900), (-0.0190, BRIM), (-0.0150, BRIM),
            (-0.0040, 0.0800), (0.0030, 0.0615)] + dome
    out.append(part("head_helm", "wood_dark", gen.lathe(prof, 24, sx, sy), axis))
    out.append(part("head_helm_rim", "brass", gen.lathe_ring([(-0.0200, BRIM - 0.0030), (-0.0170, BRIM + 0.0022),
                                                              (-0.0140, BRIM - 0.0030)], 24, sx, sy), axis))
    out.append(stud("head_helm_boss", Frame(axis.w((0, 0, CROWN - 0.001)), UP, LEFT), BOSS))
    for k in range(6):
        a = 2 * np.pi * (k + 0.5) / 6
        out.append(stud("head_helm_rivet_%d" % k, Frame(axis.w((0.0590 * np.cos(a) * sx, 0.0590 * np.sin(a) * sy, 0.012)),
                                                        V(np.cos(a), np.sin(a), 0.2), UP), 0.0048))
    return out


def parts():
    return chest() + hips() + legs() + arm(1, "l") + arm(-1, "r") + head()

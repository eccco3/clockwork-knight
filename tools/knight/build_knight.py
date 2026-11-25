"""Builds the clockwork knight: sculpts every piece, binds it to the rig, exports GLB.

  blender --background --python build_knight.py -- [--out knight.glb] [--preview a.png]
          [--pose Action:frame] [--views 0,-40,-90/30,180] [--zoom head|upper|full|<bone> [--scale 0.34]]
          [--only a,b] [--gaps upperarm,rerebrace/chest,pauldron] [--seat culet|skirt|wrap|armour|tabard]

A view is a yaw, or yaw/pitch to look from above; --zoom <bone> centres on that bone, --scale metres wide.
--gaps prints the least air between the pieces before the slash and those after it, over every frame of every clip,
or in the --pose alone. --seat picks what covers her seat; SEAT holds the default.

Rest pose is a T-pose in Blender space: +X is the figure's left, -Y is forward, +Z up.
Every piece is rigid on one bone, but for the tabard's cloth; the gaps at the joints are deliberate.
"""
import bpy, sys, os, time, zlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import sdf as S, mesher, gen, bl, build
from sculpt.bl import opt
from sculpt.sdf import V
from sculpt.gen import Frame
from sculpt.num import smoothstep
from knight import gaps, hang, head, roll, shadow

DL = os.path.join(os.path.dirname(HERE), "downloads")
REF_RIG = os.path.join(DL, "ual2", "Universal Animation Library 2[Standard]", "Female Mannequin", "Unreal-Godot", "Mannequin_F.glb")
ANIM_SRC = [os.path.join(DL, "ual1", "Universal Animation Library[Standard]", "Unreal-Godot", "UAL1_Standard_RM.glb"),
            os.path.join(DL, "ual2", "Universal Animation Library 2[Standard]", "Unreal-Godot", "UAL2_Standard_RM.glb")]
CLIPS = ["Idle_Loop", "Walk_Loop", "Jog_Fwd_Loop", "Sprint_Loop", "Jump_Start", "Jump_Loop", "Jump_Land", "Roll",
         "Sword_Idle", "Sword_Attack", "Sword_Regular_A", "Sword_Regular_A_Rec", "Sword_Regular_B",
         "Sword_Regular_B_Rec", "Sword_Regular_C", "Sword_Regular_Combo", "Sword_Heavy_Combo", "Sword_Dash",
         "Sword_Block", "Hit_Chest", "A_TPose"]

UP, FWD, LEFT, BACK, DOWN = V(0, 0, 1), V(0, -1, 0), V(1, 0, 0), V(0, 1, 0), V(0, 0, -1)
H0 = V(0, -0.020, 1.655)                       # head frame origin (between the eyes, skull centre)
GRIP = V(-0.740, 0.062, 1.4155)                # sword grip centre in the rest pose (right hand): the hollow of her fist
BLADE_DIR = V(0.0, -1.0, 0.0)

# What covers her seat. "culet": a lame across her back. "skirt": plates hinged under her fauld, each swinging
# with its thigh. "wrap": her tassets carried on round the back of her thighs. "armour": plates hinged all
# round her fauld in her tassets' place, sprung in against her legs. "tabard": a cloth panel before and behind,
# over the wrap's tassets. Under the last two her seat is a flat block set back between the tops of her thighs.
SEAT = opt("--seat", "tabard")
RECESSED = SEAT in ("armour", "tabard")
FAULD = Frame(V(0, 0.008, 0)), V(1.07, 0.70, 1)    # the axis her fauld is turned on, and how it is pressed oval
SEAT_FLOOR = 0.946                                 # where her pelvis is cut flat over the block, level with the fauld's lower edge
HUNG_Z, HUNG_R = 0.954, 0.1715                     # where the culet or a plate hangs from under the fauld: height, and radius before pressing
# The plates under her fauld: each one's span round it, in degrees from the middle of her back, and its drop.
# One that spans the middle is a single plate; any other is a left plate and its mirror image.
PLATES = {"skirt": {"back": (3, 36, 0.104), "side": (40, 73, 0.104)},
          "armour": {"tail": (-17, 17, 0.175), "haunch": (19, 55, 0.170), "side": (57, 104, 0.160),
                     "hip": (106, 147, 0.150), "front": (149, 179.4, 0.140)}}.get(SEAT, {})
SKIRT_SWING = (np.radians(-30), np.radians(100))   # how far a plate swings in under her and out
PLATE_TUCKS = {"tail": np.radians(60), "haunch": np.radians(45)}   # how far a plate turns in under her once the thighs before it are forward
# The tabard's panels: where each hangs, in degrees round the fauld, and half its width. A panel comes out from
# under her belt, lies on the fauld to its lower edge and hangs free to mid-thigh on two chains of bones side
# by side, a half following each leg, hinged at PANEL_JOINTS. Behind, the chain curls in under her by PANEL_TUCKS.
PANELS = {"front": (180, 22), "back": (0, 40)}
PANEL_TOP, PANEL_HEM, PANEL_JOINTS = 1.020, 0.730, (0.944, 0.872, 0.800)
PANEL_R = 0.189                                    # the free part's radius round the fauld, before pressing
PANEL_SWING = (np.radians(-60), np.radians(110))   # how far a panel's top swings, and each joint below it bends
PANEL_BEND = (np.radians(-75), np.radians(30))
PANEL_TUCKS = np.radians((50, 95, 130))
SIDES = (("l", 1), ("r", -1))

PIECES = []


def add(name, bone, mat, verts, faces, normals=None, colors=None, hard=True, grain=None, mirror=False,
        thickness=0.0, sharp=38.0, bevel=0.0, grain_offset=None, skin=None):
    """`skin`, in place of the one bone, gives each bone's weights on the piece's vertices as they rest."""
    PIECES.append(dict(name=name, bone=bone, mat=mat, verts=np.asarray(verts, dtype=np.float64), faces=faces,
                       normals=normals, colors=colors, hard=hard, grain=grain or Frame(V(0, 0, 0)),
                       mirror=mirror, thickness=thickness, sharp=sharp, bevel=bevel, grain_offset=grain_offset, skin=skin))


def round_fauld(a, r=HUNG_R, z=HUNG_Z):
    """The point `a` radians round the fauld from the middle of her back, toward her left, and the way its rim runs there."""
    axis, oval = FAULD
    along = V(np.cos(a), -np.sin(a), 0) * oval
    return axis.w(V(r * np.sin(a), r * np.cos(a), z) * oval), along / np.linalg.norm(along)


def plate_bones(name):
    """The bones a plate of PLATES hangs on, each with its side and that side's sign: one for a plate across her middle."""
    if PLATES[name][0] < 0:
        return [("skirt_" + name, "lr", 1)]
    return [("skirt_%s_%s" % (name, s), s, sx) for s, sx in SIDES]


def panel_bone(name, joint, side):
    return "tabard_%s_%d_%s" % (name, joint, side)


# ============================================================== rig

def load_rig():
    bl.reset_scene()
    for path in ANIM_SRC:
        bpy.ops.import_scene.gltf(filepath=path)
        for ob in list(bpy.context.scene.objects):
            bpy.data.objects.remove(ob, do_unlink=True)
    for a in bpy.data.actions:
        a.use_fake_user = True
    bpy.ops.import_scene.gltf(filepath=REF_RIG)
    arm = None
    for ob in list(bpy.context.scene.objects):
        if ob.type == "ARMATURE":
            arm = ob
        else:
            bpy.data.objects.remove(ob, do_unlink=True)
    arm.name = "KnightRig"
    arm.data.name = "KnightRig"
    arm.animation_data_clear()
    slim_hands(arm)
    J = {b.name: np.array(b.head_local) for b in arm.data.bones}
    T = {b.name: np.array(b.tail_local) for b in arm.data.bones}
    return arm, J, T


KNUCKLES_IN, FINGERS_LONGER = 0.88, 1.06       # her knuckle line and her fingers, as fractions of the mannequin's


def slim_hands(arm):
    """Gives the mannequin's hands a woman's proportions: the knuckles drawn in toward the middle one, and the
    four fingers longer. No bone turns, so the clips curl them as before."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    for s in "lr":
        middle = eb["middle_01_" + s].head.copy()
        for fn in ("index", "middle", "ring", "pinky"):
            chain = [eb["%s_0%d_%s" % (fn, k, s)] for k in (1, 2, 3)]
            heads = [b.head.copy() for b in chain]
            tip = chain[-1].tail.copy()
            at = middle + (heads[0] - middle) * KNUCKLES_IN
            for b, here, there in zip(chain, heads, heads[1:] + [tip]):
                b.head = at
                at = at + (there - here) * FINGERS_LONGER
                b.tail = at
    bpy.ops.object.mode_set(mode="OBJECT")


def add_bones(arm, J, T):
    """Helper bones: eyes, sword socket, clockwork, and the floating guards that follow a joint at half angle."""
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones

    def new(name, parent, head_, tail_, like=None):
        b = eb.new(name)
        b.head, b.tail = tuple(head_), tuple(tail_)
        b.parent = eb[parent]
        if like:
            b.matrix = eb[like].matrix.copy()
            b.length = 0.05
        J[name], T[name] = np.array(head_), np.array(tail_)
        return b

    def hinge(name, parent, at, along, toward=None):
        """A bone at `at` whose x runs `along` a hung thing's top edge. Its y points down the thing, or as near
        `toward` as a turn about x brings it, and its z out of it."""
        to = DOWN if toward is None else toward - at
        to = to - along * np.dot(to, along)
        to /= np.linalg.norm(to)
        new(name, parent, at, at + to * 0.05).align_roll(tuple(np.cross(along, to)))

    for s, sx in SIDES:
        e = H0 + V(-sx * head.EYE[0], -head.EYE[1], head.EYE[2]) * V(-1, 1, 1)
        new("eye_" + s, "Head", e, e + FWD * 0.03)
        new("pauldron_" + s, "clavicle_" + s, J["upperarm_" + s], T["upperarm_" + s], like="upperarm_" + s)
        new("couter_" + s, "upperarm_" + s, J["lowerarm_" + s], T["lowerarm_" + s], like="lowerarm_" + s)
        new("poleyn_" + s, "thigh_" + s, J["calf_" + s], T["calf_" + s], like="calf_" + s)
    for name, (a0, a1, _) in PLATES.items():    # the skirt's plates track the knee; the armour's are turned by `hang`
        for bone, s, sx in plate_bones(name):
            hinge(bone, "pelvis", *round_fauld(sx * np.radians(0.5 * (a0 + a1))), J["calf_" + s] if SEAT == "skirt" else None)
    if SEAT == "tabard":
        for name, (middle, _) in PANELS.items():
            for s, sx in SIDES:
                above = "pelvis"
                for k, z in enumerate(PANEL_JOINTS):
                    at, along = round_fauld(np.radians(middle), PANEL_R, z)
                    hinge(panel_bone(name, k, s), above, at + LEFT * sx * 0.04, along)
                    above = panel_bone(name, k, s)
    new("weapon_r", "hand_r", GRIP, GRIP + BLADE_DIR * 0.10)
    new("key", "spine_03", V(0, 0.100, 1.400), V(0, 0.140, 1.400))
    for n, c in GEARS.items():
        new(n, "spine_03", c["o"], c["o"] + FWD * 0.02)
    bpy.ops.object.mode_set(mode="POSE")
    for s in "lr":
        for helper, src in (("pauldron_", "upperarm_"), ("couter_", "lowerarm_"), ("poleyn_", "calf_")):
            c = arm.pose.bones[helper + s].constraints.new("COPY_ROTATION")
            c.target, c.subtarget = arm, src + s
            c.target_space = c.owner_space = "LOCAL"
            c.influence = 0.5
        for plate_ in PLATES if SEAT == "skirt" else ():     # a plate turns on its hinge to follow the knee, as far as it may swing
            pb = arm.pose.bones["skirt_%s_%s" % (plate_, s)]
            c = pb.constraints.new("LOCKED_TRACK")
            c.target, c.subtarget, c.track_axis, c.lock_axis = arm, "calf_" + s, "TRACK_Y", "LOCK_X"
            c = pb.constraints.new("LIMIT_ROTATION")
            c.owner_space, c.use_limit_x, (c.min_x, c.max_x) = "LOCAL", True, SKIRT_SWING
    bpy.ops.object.mode_set(mode="OBJECT")


# ============================================================== torso

WIN_C = V(0, -0.108, 1.392)                    # heart-window gear plane centre
WIN_R = 0.034
_WF = Frame(WIN_C, FWD, LEFT)                  # local x = left, y = up, z = out of the chest
GEARS = {
    "gear_a": dict(o=_WF.w((-0.0090, 0.0040, 0.006)), teeth=16, root=0.0150, tip=0.0185, spokes=4, ratio=1.0),
    "gear_b": dict(o=_WF.w((0.0167, -0.0054, 0.006)), teeth=10, root=0.0090, tip=0.0122, spokes=0, ratio=-1.6),
    "gear_c": dict(o=_WF.w((-0.0197, 0.0269, 0.006)), teeth=8, root=0.0070, tip=0.0100, spokes=0, ratio=-2.0),
}


def torso(J):
    sh = J["upperarm_l"]

    def chest(p):
        q = S.mirror_x(p)
        rib = S.ellipsoid(p, V(0, -0.015, 1.380), V(0.138, 0.108, 0.135))
        girdle = S.ellipsoid(q, V(0.080, 0.028, 1.432), V(0.062, 0.072, 0.046))
        d = S.smin(rib, girdle, 0.045)
        d = S.smin(d, S.ellipsoid(p, V(0, 0.045, 1.415), V(0.118, 0.060, 0.075)), 0.04)
        d = S.smin(d, S.ellipsoid(q, V(0.050, -0.086, 1.380), V(0.060, 0.038, 0.058)), 0.05)
        keel = S.tube(p, [V(0, -0.124, 1.445), V(0, -0.131, 1.37), V(0, -0.116, 1.305)], [0.010, 0.012, 0.010])
        d = S.smin(d, keel, 0.03)
        d = S.smax(d, S.plane(p, V(0, 0, 1.300), DOWN), 0.012)
        d = S.smax(d, S.plane(p, V(0, 0, 1.476), UP), 0.016)
        d = S.ssub(d, S.sphere(q, sh + V(0.006, 0, 0), 0.053), 0.008)
        win = S.cylinder(p, V(0, -0.22, WIN_C[2]), V(0, -0.100, WIN_C[2]), WIN_R, 0.002)
        return S.ssub(d, win, 0.0025)

    def win_edge(p):
        r = np.sqrt(p[:, 0] ** 2 + (p[:, 2] - WIN_C[2]) ** 2)
        return np.where(p[:, 1] < -0.05, r - WIN_R, 1.0)

    v, f, n = mesher.wrap(chest, V(0, -0.015, 1.345), V(0, -0.015, 1.430), (0.16, 0.13, 0.11), (44, 32, 32),
                          relax=10, snap=win_edge)
    add("chest", "spine_03", "wood_dark", v, f, normals=n, hard=False)
    loop = S.hug(chest, V(0, -0.015, 1.3075), LEFT, FWD, 72, 0.0, 2 * np.pi * 71 / 72, off=0.0005)
    v, f = gen.tube(loop, 0.0036, 8, closed=True)
    add("chest_rim", "spine_03", "brass", v, f)

    # articulated belly lames (turned, then pressed oval)
    for name, bone, pts, cy in (
        ("lame_upper", "spine_02", [(1.186, 0.0), (1.187, 0.088), (1.193, 0.0995), (1.206, 0.1040), (1.240, 0.1095),
                                    (1.275, 0.1160), (1.287, 0.1130), (1.2925, 0.1030), (1.2935, 0.0)], -0.030),
        ("lame_lower", "spine_01", [(1.070, 0.0), (1.071, 0.1040), (1.077, 0.1175), (1.092, 0.1215), (1.130, 0.1130),
                                    (1.160, 0.1070), (1.172, 0.1035), (1.1775, 0.0940), (1.1785, 0.0)], -0.026)):
        v, f = gen.lathe(gen.turned(pts), 48, sy=0.80)
        add(name, bone, "wood_dark", v + V(0, cy, 0), f)
        z0 = pts[2][0] + 0.004
        r0 = pts[2][1] + 0.004
        v, f = gen.lathe_ring([(z0 - 0.003, r0 - 0.004), (z0 - 0.003, r0 - 0.0005), (z0, r0 + 0.0012), (z0 + 0.003, r0 - 0.0005),
                               (z0 + 0.003, r0 - 0.004)], 48, sy=0.80)
        add(name + "_bead", bone, "brass", v + V(0, cy, 0), f)

    hip = J["thigh_l"]

    def pelvis(p):
        q = S.mirror_x(p)
        d = S.ellipsoid(p, V(0, 0.008, 0.990), V(0.150, 0.100, 0.085))
        if RECESSED:
            d = S.smax(d, S.plane(p, V(0, 0, SEAT_FLOOR), DOWN), 0.008)
        else:
            d = S.smin(d, S.ellipsoid(p, V(0, 0.012, 0.915), V(0.070, 0.085, 0.075)), 0.04)
        d = S.smax(d, S.plane(p, V(0, 0, 1.060), UP), 0.014)
        d = S.ssub(d, S.sphere(q, hip + V(0.004, 0, -0.006), 0.073), 0.010)
        return d

    v, f, n = mesher.wrap(pelvis, V(-0.012, 0.01, 1.005), V(0.012, 0.01, 1.005), (0.16, 0.11, 0.12), (40, 26, 30), relax=10)
    add("pelvis", "pelvis", "wood_dark", v, f, normals=n, hard=False)
    if RECESSED:
        block = seat_block(J)
        v, f, n = mesher.wrap(block, V(0, 0.003, 0.950), V(0, 0.003, 0.915), (0.035, 0.040, 0.040), (10, 12, 14), relax=8)
        add("seat", "pelvis", "wood_dark", v, f, normals=n, hard=False)
    # fauld: two flared lames hanging from the belt
    axis, oval = FAULD
    for k, sec in enumerate((
            [(0.984, 0.158), (0.984, 0.1715), (0.988, 0.1730), (1.016, 0.1640), (1.020, 0.1625), (1.020, 0.150)],
            [(0.946, 0.166), (0.946, 0.1800), (0.950, 0.1815), (0.990, 0.1745), (0.994, 0.1730), (0.994, 0.160)])):
        v, f = gen.lathe_ring(sec, 64, sx=oval[0], sy=oval[1])
        add("fauld_%d" % k, "pelvis", "wood_dark", axis.w(v), f)
        z0, r0 = sec[1][0] + 0.004, sec[2][1]
        v, f = gen.lathe_ring([(z0 - 0.003, r0 - 0.004), (z0 - 0.003, r0 - 0.0002), (z0, r0 + 0.0014), (z0 + 0.003, r0 - 0.0002),
                               (z0 + 0.003, r0 - 0.004)], 64, sx=oval[0], sy=oval[1])
        add("fauld_bead_%d" % k, "pelvis", "brass", axis.w(v), f)
    {"skirt": skirt, "armour": skirt, "tabard": tabard}.get(SEAT, culet)()
    # her trunk, turned from the pale wood of her limbs, seen only through the gaps between the lames
    for name, bone, pts, cy in (
            ("core_lower", "spine_01", [(1.040, 0.0), (1.041, 0.066), (1.100, 0.074), (1.185, 0.070), (1.198, 0.060), (1.199, 0.0)], -0.026),
            ("core_upper", "spine_02", [(1.165, 0.0), (1.166, 0.062), (1.200, 0.072), (1.290, 0.078), (1.315, 0.068), (1.316, 0.0)], -0.028)):
        v, f = gen.lathe(gen.turned(pts), 32, sy=0.78)
        axis = Frame(V(0, cy, 0))
        add(name, bone, "wood_light", axis.w(v), f, grain=axis)
    # belt with a gear buckle
    v, f = gen.lathe_ring([(1.022, 0.150), (1.022, 0.1565), (1.030, 0.1585), (1.046, 0.1585), (1.054, 0.1565), (1.054, 0.150)],
                          56, sy=0.70)
    add("belt", "pelvis", "leather", v + V(0, 0.008, -0.004), f)
    bf = Frame(V(0, -0.104, 1.034), FWD, LEFT)
    v, f = gen.gear(14, 0.0200, 0.0245, r_hole=0.0060, spokes=5)
    add("buckle", "pelvis", "brass", bf.w(v), f, thickness=0.006)
    v, f = gen.dome(0.0075, 0.005)
    add("buckle_boss", "pelvis", "brass", bf.w(v + V(0, 0, 0.004)), f)

    # neck and gorget ring
    nf = Frame(J["neck_01"], J["Head"] - J["neck_01"], LEFT)
    v, f = gen.lathe(gen.turned([(-0.004, 0.0), (-0.003, 0.046), (0.004, 0.0495), (0.016, 0.0455), (0.034, 0.0405),
                             (0.052, 0.0395), (0.062, 0.0340), (0.0665, 0.020), (0.068, 0.0)]), 32)
    add("neck", "neck_01", "wood_light", nf.w(v), f, grain=nf)
    v, f = gen.lathe_ring([(1.472, 0.052), (1.472, 0.064), (1.480, 0.0665), (1.487, 0.064), (1.487, 0.052)], 40, sy=0.92)
    add("gorget", "spine_03", "brass", v + V(0, 0.010, 0), f)


def culet():
    """A third lame across the back only, deepest at the centre."""
    A, Zv = np.meshgrid(np.radians(np.linspace(-80, 80, 41)), np.linspace(0, 1, 6), indexing="ij")
    axis, oval = FAULD

    def cul(dr):
        z = HUNG_Z - (0.058 - 0.022 * (A / np.radians(80)) ** 2) * Zv
        r = HUNG_R + dr + 0.011 * Zv
        return np.stack([r * np.sin(A), r * np.cos(A), z], axis=-1) * oval

    plate("culet", "pelvis", cul(0.0), cul(-0.005), 0.0032, axis, hung=True)


def seat_block(J):
    """The sculpt of the flat block between the tops of her thighs, its faces set back from theirs."""
    socket = J["thigh_l"] + V(0.004, 0, -0.006)
    return lambda p: S.ssub(S.box(p, V(0, 0.003, 0.930), V(0.024, 0.031, 0.032), 0.004),
                            S.sphere(S.mirror_x(p), socket, 0.073), 0.004)


def skirt():
    """The scalloped PLATES, hung under her fauld."""
    U, Zv = np.meshgrid(np.linspace(0, 1, 15), np.linspace(0, 1, 9), indexing="ij")
    axis, oval = FAULD
    for name, (a0, a1, drop) in PLATES.items():
        A = np.radians(a0 + (a1 - a0) * U)

        def scallop(dr):
            z = HUNG_Z - (drop - 0.030 * np.abs(2 * U - 1) ** 2.6) * Zv
            r = HUNG_R + dr + 0.012 * Zv + 0.003 * np.sin(np.pi * Zv)
            return np.stack([r * np.sin(A), r * np.cos(A), z], axis=-1) * oval

        o = scallop(0.0)
        bone, paired = plate_bones(name)[0][0], len(plate_bones(name)) > 1
        plate("skirt_" + name, bone, o, scallop(-0.005), 0.0032, axis, mirror=paired, hung=True)
        for k, (iu, iv, size) in enumerate(((3, 2, 0.0042), (11, 2, 0.0042), (7, 6, 0.0060))):
            stud("skirt_%s_rivet_%d" % (name, k), bone, axis, o[iu, iv], o[iu, iv] / oval ** 2 * V(1, 1, 0), size, size * 0.7, paired)


def drape(name):
    """The weights that hang a piece of the tabard's `name` panel: on her pelvis down to the first joint, then
    on each chain's bones in turn, easing from one to the next across a joint and from her left chain to her right."""
    def skin(p):
        left = smoothstep(-0.035, 0.035, p[:, 0])
        above = [smoothstep(z - 0.012, z + 0.012, p[:, 2]) for z in PANEL_JOINTS]
        weights = {"pelvis": above[0]}
        for k, below in enumerate(above[1:] + [1.0]):
            held = (1.0 - above[k]) * below
            weights[panel_bone(name, k, "l")] = held * left
            weights[panel_bone(name, k, "r")] = held * (1.0 - left)
        return weights
    return skin


def tabard():
    """A cloth panel before and behind, piped and studded in brass, a gear on the front for her crest."""
    U, Zv = np.meshgrid(np.linspace(0, 1, 17), np.linspace(0, 1, 27), indexing="ij")
    axis, oval = FAULD
    for name, (middle, half) in PANELS.items():
        A = np.radians(middle + half * (2 * U - 1))
        z = PANEL_TOP + (PANEL_HEM + 0.030 * np.abs(2 * U - 1) ** 1.5 - PANEL_TOP) * Zv
        on_fauld = np.clip((z - PANEL_JOINTS[0]) / (PANEL_TOP - PANEL_JOINTS[0]), 0, 1)

        def sheet(dr):
            r = PANEL_R + dr - 0.0205 * on_fauld
            return np.stack([r * np.sin(A), r * np.cos(A), z], axis=-1) * oval

        o = sheet(0.003)
        plate("tabard_" + name, None, o, sheet(0.0), 0.0022, axis, hung=True, mat="cloth", skin=drape(name))
        for iu in (2, 14):
            stud("tabard_%s_stud_%d" % (name, iu), "pelvis", axis, o[iu, 1], o[iu, 1] / oval ** 2 * V(1, 1, 0), 0.0042, 0.0030, False)
    face, _ = round_fauld(np.radians(PANELS["front"][0]), PANEL_R - 0.0065, 0.980)      # on the fauld, where the cloth cannot crease it
    v, f = gen.gear(12, 0.0205, 0.0260, r_hole=0.0065, spokes=6)
    add("tabard_crest", "pelvis", "brass", Frame(face, V(0, -0.98, 0.19), LEFT).w(v), f, thickness=0.0025)


# ============================================================== limbs

def limb(name, bone, mat, frame, prof, segs, mitre=None, mirror=True, sy=1.0):
    v, f = gen.lathe(prof, segs, sy=sy)
    if mitre:
        for c, n in mitre:
            v = gen.clip(v, c, n)
    add(name, bone, mat, frame.w(v), f, grain=frame, mirror=mirror)


def girth(f, z, segs):
    """Radius of the sculpt f, given in its own frame, about that frame's z at height z: one for each of `segs` azimuths."""
    ring = S.hug(f, V(0, 0, z), V(1, 0, 0), V(0, 1, 0), segs, 0.0, 2 * np.pi * (segs - 1) / segs, off=0.0)
    return S.length(ring[:, :2])


def band(name, bone, mat, frame, along, proud=0.0022, segs=32, mirror=True):
    """Raised band hugging a part. along: (z, r) stations, r the part's radius there; one radius for a turned
    part, or `girth` for a sculpted one."""
    e = 0.0015
    (z0, r0), (z1, r1) = along[0], along[-1]
    sec = ([(z0, r0 - 0.003), (z0, r0 + proud - e), (z0 + e, r0 + proud)] + [(z, r + proud) for z, r in along[1:-1]]
           + [(z1 - e, r1 + proud), (z1, r1 + proud - e), (z1, r1 - 0.003)])
    v, f = gen.lathe_ring([(z, 1.0) for z, _ in sec], segs)
    v[:, :2] *= np.concatenate([np.broadcast_to(r, segs) for _, r in sec])[:, None]
    add(name, bone, mat, frame.w(v), f, grain=frame, mirror=mirror)


def stud(name, bone, frame, at, out, size, height, mirror=True):
    """A brass rivet head at `at`, rising along `out`, both in the frame."""
    rf = Frame(frame.w(at), frame.dir(out), frame.dir(V(0, 0, 1)))
    v, f = gen.dome(size, height, 8, 2)
    add(name, bone, "brass", rf.w(v), f, mirror=mirror)


def rivets(name, bone, frame, z, r, count, size=0.0028, mirror=True, phase=0.0):
    """A ring of rivets at radius r, or at one radius each."""
    for k, r in enumerate(np.broadcast_to(r, count)):
        a = 2 * np.pi * (k + phase) / count
        stud("%s_%d" % (name, k), bone, frame, V(r * np.cos(a), r * np.sin(a), z), V(np.cos(a), np.sin(a), 0), size,
             size * 0.6, mirror)


def plate(name, bone, outer, inner, rim, frame, mirror=False, hung=False, mat="wood_dark", skin=None):
    """Plate of dark wood, or of `mat`, between two grids in the frame, their columns running from its top edge
    down, edged in brass: all round, or on its three free sides if it is `hung` from under another piece."""
    v, f = gen.patch(outer, inner)
    add(name, bone, mat, frame.w(v), f, grain=frame, mirror=mirror, skin=skin)
    mid = 0.5 * (outer + inner)
    if hung:
        loop = np.concatenate([mid[0, 1:-1], mid[:, -1], mid[-1, -2:0:-1]])
    else:
        loop = np.concatenate([mid[:-1, 0], mid[-1, :-1], mid[:0:-1, -1], mid[0, :0:-1]])
    v, f = gen.tube(frame.w(loop), rim, 8, closed=not hung)
    add(name + "_rim", bone, "brass", v, f, mirror=mirror, skin=skin)


def guard(name, bone, frame, R, thick, theta_max, nu, nv, rim, radii=(1.0, 1.0, 1.0)):
    """Domed plate of dark wood about the frame's z, edged in brass. Returns its outer and inner grids."""
    o, i = gen.cap(R, thick, theta_max, nu, nv, radii)
    v, f = gen.patch(o, i)
    add(name, bone, "wood_dark", frame.w(v), f, grain=frame, mirror=True)
    edge = o[:, 0, :] * 0.5 + i[:, 0, :] * 0.5
    v, f = gen.tube(frame.w(edge[:-1]), rim, 8, closed=True)
    add(name + "_rim", bone, "brass", v, f, mirror=True)


FACE_TURN = np.radians(55)                     # the shoulder's joint face looks this far off the arm's axis, toward her side
FACE_REACH, FACE_ROUND = 0.036, 0.090          # the face's crown from the joint, and the radius of its shallow dome


def arms(J, T):
    sh, el, wr = J["upperarm_l"], J["lowerarm_l"], J["hand_l"]
    ua = Frame(sh, el - sh, UP)            # local x up (her outer side once the arm hangs), y forward (elbow flexion side), z down the arm
    L = np.linalg.norm(el - sh)
    inward = V(-np.sin(FACE_TURN), 0, -np.cos(FACE_TURN))

    def face(l):
        """The joint face: a shallow dome over the head of the bone, and nothing behind it."""
        return np.minimum(S.sphere(l, inward * (FACE_REACH - FACE_ROUND), FACE_ROUND), S.plane(l, inward * 0.020, inward))

    def mitre(l):
        return S.plane(l, V(0, -0.006, L - 0.007), V(0, 0.766, 0.643))

    def upperarm(l):
        """A fit woman's upper arm in the arm's frame, ending at the shoulder in a face turned to her body."""
        d = S.cone(l, V(0, 0, 0.030), V(0, 0, L - 0.030), 0.0295, 0.0300)
        d = S.smin(d, S.ellipsoid(l, V(0.003, 0, 0.011), V(0.039, 0.041, 0.047)), 0.022)              # deltoid, capping the joint
        d = S.smin(d, S.cone(l, V(0.008, -0.002, 0.030), V(0.018, -0.003, 0.100), 0.027, 0.012), 0.020)   # and tapering down the outside
        d = S.smin(d, S.ellipsoid(l, V(-0.003, 0.010, 0.118), V(0.022, 0.023, 0.062)), 0.014)         # biceps
        d = S.smin(d, S.ellipsoid(l, V(0.003, -0.009, 0.102), V(0.025, 0.025, 0.072)), 0.014)         # triceps
        d = S.smin(d, S.sphere(l, inward * 0.008, 0.036), 0.012)                                      # the head of the bone
        d = S.smax(d, face(l), 0.003)
        d = S.smax(d, S.plane(l, V(0, 0, L - 0.007), V(0, 0, 1)), 0.008)
        return S.smax(d, mitre(l), 0.005)

    v, f, _ = mesher.wrap(upperarm, V(0, 0, 0.010), V(0, 0, L - 0.030), (0.05, 0.05, 0.5 * L + 0.02), (14, 14, 44), relax=12)
    add("upperarm", "upperarm_l", "wood_light", ua.w(v), f, normals=ua.dir(S.gradient(upperarm, v)), hard=False, grain=ua, mirror=True)
    sleeve = [(z, girth(upperarm, z, 32)) for z in np.linspace(0.060, 0.150, 7)]
    band("rerebrace", "upperarm_l", "wood_dark", ua, sleeve, 0.0040)
    for trim, zs in (("a", (0.056, 0.062)), ("b", (0.148, 0.154))):
        band("rerebrace_trim_" + trim, "upperarm_l", "brass", ua, [(z, girth(upperarm, z, 32) + 0.0038) for z in zs], 0.0016)
    rivets("rerebrace_rivet", "upperarm_l", ua, 0.105, girth(upperarm, 0.105, 6) + 0.0040, 6)

    fa = Frame(el, wr - el, UP)
    Lf = np.linalg.norm(wr - el)
    prof = gen.turned([(0.0070, 0.0), (0.0075, 0.019), (0.0095, 0.0275), (0.014, 0.0305), (0.030, 0.0338), (0.070, 0.0358),
                   (0.120, 0.0328), (0.180, 0.0274), (0.235, 0.0228), (Lf - 0.016, 0.0212), (Lf - 0.010, 0.0200),
                   (Lf - 0.0085, 0.015), (Lf - 0.008, 0.0)])
    m = [(V(0, -0.006, 0.0070), V(0, 0.766, -0.643))]
    limb("forearm", "lowerarm_l", "wood_light", fa, prof, 32, m)
    # vambrace: dark sleeve flaring toward the elbow, cuff flaring over the wrist
    sec = [(0.038, 0.030), (0.038, 0.0405), (0.041, 0.0420), (0.075, 0.0412), (0.130, 0.0368), (0.190, 0.0318),
           (0.193, 0.0305), (0.193, 0.024)]
    v, f = gen.lathe_ring(sec, 32)
    add("vambrace", "lowerarm_l", "wood_dark", fa.w(v), f, grain=fa, mirror=True)
    band("vambrace_trim_a", "lowerarm_l", "brass", fa, [(0.034, 0.0410), (0.041, 0.0410)], 0.0016)
    band("vambrace_trim_b", "lowerarm_l", "brass", fa, [(0.188, 0.0312), (0.195, 0.0306)], 0.0016)
    rivets("vambrace_rivet", "lowerarm_l", fa, 0.058, 0.0425, 8)
    sec = [(0.212, 0.020), (0.212, 0.0272), (0.216, 0.0287), (Lf - 0.004, 0.0360), (Lf, 0.0370), (Lf + 0.002, 0.0360),
           (Lf + 0.002, 0.0330), (0.220, 0.020)]
    v, f = gen.lathe_ring(sec, 32)
    add("cuff", "lowerarm_l", "wood_dark", fa.w(v), f, grain=fa, mirror=True)
    band("cuff_trim", "lowerarm_l", "brass", fa, [(Lf - 0.003, 0.0358), (Lf + 0.0025, 0.0362)], 0.0018)

    # floating guards
    pf = Frame(sh + V(0, 0, 0.002), UP, LEFT)                  # local x toward the arm, y back
    def pth(az):
        c = np.cos(az)
        return np.radians(80 - 36 * np.maximum(c, 0) ** 1.4 - 34 * np.maximum(-c, 0) ** 1.4)
    guard("pauldron", "pauldron_l", pf, 0.068, 0.0065, pth, 40, 10, 0.0042, (1.0, 1.06, 0.94))
    v, f = gen.gear(12, 0.0150, 0.0185, r_hole=0.0, spokes=0)
    add("pauldron_rosette", "pauldron_l", "brass", pf.w(v + V(0, 0, 0.068 * 0.94 - 0.001)), f, thickness=-0.0045, mirror=True)
    v, f = gen.dome(0.0070, 0.0050)
    add("pauldron_boss", "pauldron_l", "brass", pf.w(v + V(0, 0, 0.068 * 0.94 + 0.003)), f, mirror=True)

    cf = Frame(el + V(0, 0.004, 0), BACK, LEFT)
    guard("couter", "couter_l", cf, 0.047, 0.005, lambda az: np.radians(60 - 6 * np.cos(2 * az)), 32, 8, 0.0033)
    v, f = gen.dome(0.0085, 0.0055)
    add("couter_boss", "couter_l", "brass", cf.w(v + V(0, 0, 0.0465)), f, mirror=True)


def hands(J, T):
    hf = Frame(J["hand_l"], T["hand_l"] - J["hand_l"], UP)       # x up (back of hand), y forward (thumb side), z to fingers
    radii = {"index": (0.0080, 0.0071, 0.0062), "middle": (0.0083, 0.0073, 0.0064), "ring": (0.0078, 0.0069, 0.0060),
             "pinky": (0.0068, 0.0060, 0.0053), "thumb": (0.0090, 0.0080, 0.0070)}
    root = {fn: hf.l(J[fn + "_01_l"]) for fn in radii}           # each finger's first joint, in the hand's frame
    carpal = {"index": V(-0.001, 0.013, 0.032), "middle": V(0.001, 0.004, 0.032), "ring": V(0.0, -0.006, 0.032),
              "pinky": V(-0.002, -0.016, 0.030)}                 # where each metacarpal leaves the wrist

    def palm(p):
        l = hf.l(p)
        d = S.ellipsoid(l, V(0, 0, 0.020), V(0.0135, 0.0210, 0.0190))
        for fn, base in carpal.items():                          # metacarpals fanning to the knuckles
            d = S.smin(d, S.cone(l, base, root[fn] - V(0, 0, 0.004), 0.0098, radii[fn][0] + 0.0006), 0.012)
        for a, b in zip(list(carpal)[:-1], list(carpal)[1:]):    # the flesh between them, ending in the webs
            d = S.smin(d, S.cone(l, 0.5 * (carpal[a] + carpal[b]), 0.5 * (root[a] + root[b]) - V(0, 0, 0.008), 0.0082, 0.0068), 0.008)
        pads = S.tube(l, [root[fn] + V(-0.0070, 0, -0.022) for fn in carpal], 0.0052)
        pads = S.smin(pads, S.ellipsoid(l, V(-0.0090, 0.017, 0.050), V(0.0090, 0.0130, 0.0260)), 0.012)    # thenar
        pads = S.smin(pads, S.ellipsoid(l, V(-0.0080, -0.021, 0.056), V(0.0070, 0.0100, 0.0320)), 0.012)   # hypothenar
        d = S.smin(d, pads, 0.012)
        d = S.smin(d, S.cone(l, V(-0.004, 0.009, 0.024), root["thumb"], 0.0122, radii["thumb"][0] + 0.0014), 0.010)   # thumb's seat
        for fn in carpal:                                        # a knuckle ball each finger turns on
            d = S.smin(d, S.sphere(l, root[fn], radii[fn][0] + 0.0004), 0.005)
        return d

    # meshed in a space where the hand is as deep as it is wide, so the lattice spreads evenly over back and palm,
    # and drawn together round the knuckles
    deep = V(2.5, 1, 1)
    flat = lambda p: hf.l(p) / deep
    near = lambda p: np.min([S.length(flat(p) - root[fn]) for fn in carpal], axis=0)
    v, f, _ = mesher.wrap(lambda p: palm(hf.w(flat(p))), hf.w((0, -0.004, 0.022)), hf.w((0, -0.004, 0.098)),
                          (0.068, 0.056, 0.065), (40, 30, 14), relax=30, density=lambda p: 1 + 5 * np.exp(-(near(p) / 0.018) ** 2))
    v = hf.w(flat(v))
    n = S.gradient(palm, v, 0.0015)                              # shaded as broadly as it is meshed
    add("palm", "hand_l", "wood_light", v, f, normals=n, hard=False, grain=hf, mirror=True)
    g = 0.0016
    for fn, rs in radii.items():
        for k in range(3):
            b = "%s_0%d_l" % (fn, k + 1)
            a, t = J[b], T[b]
            Lb = np.linalg.norm(t - a)
            fr = Frame(a, t - a, UP)
            r1 = rs[k] * (0.90 if k < 2 else 0.70)
            v, f = gen.capsule(Lb - 2 * g, rs[k], r1, 12, 3, 0.55 if k < 2 else 0.9)
            add(b[:-2], b, "wood_light", fr.w(v * V(0.9, 1.0, 1.0) + V(0, 0, g)), f, grain=fr, mirror=True)


def tasset(th):
    """A plate on her thigh, in the thigh's frame `th`, from the inner front round its outside. The wrap and the tabard
    carry it on behind her, where it ducks under the culet's end, domes over her seat about the hip, hangs lower, and rounds
    off toward her other thigh."""
    span, studs = 122, [(4, 1, 0.0042, 0.0030), (12, 1, 0.0042, 0.0030), (20, 1, 0.0042, 0.0030), (12, 8, 0.0060, 0.0042)]
    if SEAT in ("wrap", "tabard"):
        span, studs = 240, studs + [(30, 8, 0.0042, 0.0030), (39, 8, 0.0042, 0.0030)]
    nu, nv = 1 + round(span / 5.08), 11
    uu, vv = np.meshgrid(np.linspace(0, 1, nu), np.linspace(0, 1, nv), indexing="ij")
    turn = -34 + span * uu
    az = np.radians(turn)
    zt = -0.006 + 0.040 * smoothstep(88, 102, turn) - 0.082 * smoothstep(128, 156, turn) + 0.015 * smoothstep(184, 206, turn)
    zb = (0.205 - 0.075 * np.abs(2 * np.minimum((turn + 34) / 122, 1) - 1) ** 2.4 + 0.038 * smoothstep(88, 143, turn)
          - 0.075 * np.clip((turn - 150) / 56, 0, 1) ** 2.4)
    zz = zt + (zb - zt) * vv
    above = np.maximum(-0.006 - zz, 0)          # how far a point of the dome stands over the tasset's own top edge
    snug = 0.0045 * smoothstep(92, 125, turn)   # behind her it sits closer to the thigh, to pass inside the culet

    def tas(R):
        r = np.sqrt((R - snug) ** 2 - above * above) - 0.034 * zz + 0.004 * np.sin(np.pi * vv)
        return np.stack([(r - 0.009) * np.sin(az), r * np.cos(az), zz], axis=-1)

    o = tas(0.0935)
    plate("tasset", "thigh_l", o, tas(0.0885), 0.0034, th, mirror=True)
    for k, (iu, iv, size, height) in enumerate(studs):
        stud("tasset_rivet_%d" % k, "thigh_l", th, o[iu, iv], o[iu, iv] * V(1, 1, 0), size, height)


def legs(J, T):
    hip, kn, an = J["thigh_l"], J["calf_l"], J["foot_l"]
    th = Frame(hip, kn - hip, LEFT)            # local x left, y forward, z down the leg
    L = np.linalg.norm(kn - hip)
    prof = gen.arc(0.004, 0.062, 180, 62, 10) + list(gen.turned(
        [(0.040, 0.0600), (0.065, 0.0690), (0.105, 0.0735), (0.170, 0.0705), (0.250, 0.0625), (0.330, 0.0540),
         (L - 0.024, 0.0500), (L - 0.014, 0.0490), (L - 0.0090, 0.0450), (L - 0.0070, 0.030), (L - 0.0065, 0.0)]))
    limb("thigh", "thigh_l", "wood_light", th, prof, 36, [(V(0, 0.008, L - 0.0065), V(0, -0.766, 0.643))])
    sec = [(0.085, 0.060), (0.085, 0.0775), (0.089, 0.0790), (0.170, 0.0750), (0.270, 0.0640), (0.300, 0.0605),
           (0.303, 0.0590), (0.303, 0.050)]
    v, f = gen.lathe_ring(sec, 36)
    add("cuisse", "thigh_l", "wood_dark", th.w(v), f, grain=th, mirror=True)
    band("cuisse_trim_a", "thigh_l", "brass", th, [(0.081, 0.0772), (0.089, 0.0772)], 0.0018, 36)
    band("cuisse_trim_b", "thigh_l", "brass", th, [(0.298, 0.0598), (0.306, 0.0590)], 0.0018, 36)
    rivets("cuisse_rivet", "thigh_l", th, 0.108, 0.0795, 8)

    if SEAT != "armour":                    # the armour's plates hang in the tassets' place
        tasset(th)

    cf = Frame(kn, an - kn, LEFT)
    Lc = np.linalg.norm(an - kn)
    prof = gen.turned([(0.0070, 0.0), (0.0075, 0.030), (0.0095, 0.0420), (0.016, 0.0460), (0.050, 0.0495), (0.110, 0.0525),
                   (0.170, 0.0495), (0.250, 0.0410), (0.330, 0.0330), (Lc - 0.058, 0.0305), (Lc - 0.042, 0.0295),
                   (Lc - 0.037, 0.0270), (Lc - 0.0348, 0.016), (Lc - 0.034, 0.0)])
    limb("calf", "calf_l", "wood_light", cf, prof, 36, [(V(0, 0.008, 0.0070), V(0, -0.766, -0.643))])
    sec = [(0.040, 0.040), (0.040, 0.0530), (0.044, 0.0545), (0.110, 0.0570), (0.170, 0.0540), (0.250, 0.0452),
           (0.320, 0.0375), (0.350, 0.0352), (0.353, 0.0338), (0.353, 0.026)]
    v, f = gen.lathe_ring(sec, 36)
    add("greave", "calf_l", "wood_dark", cf.w(v), f, grain=cf, mirror=True)
    band("greave_trim_a", "calf_l", "brass", cf, [(0.036, 0.0528), (0.044, 0.0532)], 0.0018, 36)
    band("greave_trim_b", "calf_l", "brass", cf, [(0.348, 0.0348), (0.356, 0.0342)], 0.0018, 36)
    rivets("greave_rivet", "calf_l", cf, 0.064, 0.0565, 8)

    kf = Frame(kn + V(0, 0.006, 0), FWD, LEFT)
    guard("poleyn", "poleyn_l", kf, 0.064, 0.006, lambda az: np.radians(62 + 6 * np.cos(2 * az)), 36, 9, 0.0040,
          (1.0, 1.08, 1.0))
    v, f = gen.gear(10, 0.0125, 0.0158)
    add("poleyn_rosette", "poleyn_l", "brass", kf.w(v + V(0, 0, 0.0635)), f, thickness=-0.004, mirror=True)
    v, f = gen.dome(0.0060, 0.0045)
    add("poleyn_boss", "poleyn_l", "brass", kf.w(v + V(0, 0, 0.0665)), f, mirror=True)

    x = an[0]

    SOLE = 0.012

    def foot_body(p):
        heel = S.sphere(p, V(x, 0.068, 0.047), 0.0365)
        instep = S.cone(p, V(x, 0.030, 0.072), V(x, -0.098, 0.037), 0.036, 0.027)
        d = S.smin(heel, instep, 0.024)
        d = S.smin(d, S.ellipsoid(p, V(x, -0.080, 0.034), V(0.0455, 0.050, 0.0265)), 0.02)
        return S.smin(d, S.ellipsoid(p, V(x, 0.040, 0.074), V(0.0355, 0.041, 0.030)), 0.02)

    def foot(p):
        d = S.smax(foot_body(p), S.plane(p, V(0, 0, SOLE), DOWN), 0.003)
        return S.smax(d, S.plane(p, V(0, -0.108, 0), FWD), 0.004)

    v, f, n = mesher.wrap(foot, V(x, 0.045, 0.042), V(x, -0.080, 0.032), (0.05, 0.11, 0.06), (18, 34, 16), relax=8)
    add("foot", "foot_l", "wood_dark", v, f, normals=n, hard=False, mirror=True)
    # lame edges across the instep, and the ankle ball
    for k, y in enumerate((0.006, -0.040, -0.086)):
        loop = S.hug(foot, V(x, y, 0.030), LEFT, UP, 28, np.radians(-22), np.radians(202), off=0.0002)
        v, f = gen.tube(loop, 0.0026, 8)
        add("sabaton_band_%d" % k, "foot_l", "brass", v, f, mirror=True)
    af = Frame(an, UP, LEFT)
    v, f = gen.lathe(gen.arc(0.0, 0.0285, 0, 180, 15), 28)
    add("ankle", "foot_l", "wood_light", af.w(v), f, grain=af, mirror=True)

    def toe_body(p):
        d = S.ellipsoid(p, V(x, -0.150, 0.031), V(0.0435, 0.056, 0.0245))
        ridge = S.cone(p, V(x, -0.116, 0.041), V(x, -0.214, 0.024), 0.022, 0.0065)
        return S.smin(d, ridge, 0.02)

    def toe(p):
        d = S.smax(toe_body(p), S.plane(p, V(0, 0, SOLE), DOWN), 0.003)
        return S.smax(d, S.plane(p, V(0, -0.1175, 0), BACK), 0.004)

    v, f, n = mesher.wrap(toe, V(x, -0.132, 0.027), V(x, -0.190, 0.026), (0.05, 0.05, 0.03), (16, 18, 10), relax=8)
    add("toe", "ball_l", "wood_dark", v, f, normals=n, hard=False, mirror=True)

    # leather soles: the footprint of each part, a little proud, as a slab
    def slab(body, cut):
        def fn(p):
            q = np.array(p, dtype=np.float64)
            q[:, 2] = 0.034
            d = body(q) - 0.0035
            d = S.smax(d, S.plane(p, V(0, 0, SOLE + 0.0012), UP), 0.0015)
            d = S.smax(d, S.plane(p, V(0, 0, 0.0005), DOWN), 0.0015)
            return S.smax(d, cut(p), 0.0015)
        return fn

    v, f, n = mesher.wrap(slab(foot_body, lambda p: S.plane(p, V(0, -0.108, 0), FWD)), V(x, 0.060, 0.007), V(x, -0.085, 0.007),
                          (0.055, 0.06, 0.008), (16, 30, 4), relax=6)
    add("sole", "foot_l", "leather", v, f, normals=n, hard=False, mirror=True)
    v, f, n = mesher.wrap(slab(toe_body, lambda p: S.plane(p, V(0, -0.1175, 0), BACK)), V(x, -0.132, 0.007), V(x, -0.190, 0.007),
                          (0.055, 0.04, 0.008), (16, 16, 4), relax=6)
    add("sole_toe", "ball_l", "leather", v, f, normals=n, hard=False, mirror=True)


# ============================================================== head

FACE_GRAIN = V(0.09, 0.05, 0.60)                # the head frame's origin in the face's grain space


def from_head(p):
    return H0 + np.asarray(p) * V(-1, -1, 1)


def to_head(p):
    return (p - H0) * V(-1, -1, 1)


HELM_VB = 0.438                                # height of the brow line on the helm (0 rim .. 1 crown)


def helmet_point(al, v, R, flute=0.0):
    C = V(0, -0.012, 0.022)
    aa = np.abs(al)
    s = np.clip((aa - np.radians(40)) / np.radians(45), 0, 1)
    e0 = np.radians(-30 + (-58 + 30) * s * s * (3 - 2 * s))
    e = e0 + (np.pi / 2 - e0) * v
    h = np.where(e >= 0, np.cos(e), 1 - (1 - np.cos(e)) * 0.35)
    zz = np.sin(e) * np.where(e >= 0, 1.0, 1.15)
    flare = 0.20 * np.clip(1 - v / 0.22, 0, 1) ** 2 * np.cos(np.clip(aa / np.radians(75), 0, 1) * np.pi / 2) ** 2
    if flute:
        # fourteen shallow channels between crisp ridges, fading out above the brow band and into the crown
        f = np.clip((v - (HELM_VB + 0.064)) / 0.05, 0, 1)
        f = f * f * (3 - 2 * f) * (1 - np.clip((v - 0.88) / 0.11, 0, 1) ** 2)
        h = h * (1 - flute * 0.040 * f * (1 - np.abs(np.cos(al * 7.0)) ** 0.6))
    return np.stack([C[0] + R[0] * h * (1 + 0.3 * flare) * np.sin(al),
                     C[1] - R[1] * h * (1 + flare) * np.cos(al),
                     C[2] + R[2] * zz + 0.006 * v ** 6], axis=-1)


def head_pieces(res=64):
    f = lambda p: head.field(to_head(p))
    v, q, n = mesher.wrap(f, H0 + V(0, 0.012, -0.035), H0 + V(0, 0.012, 0.045), (0.08, 0.10, 0.12),
                          (res, int(res * 0.8), int(res * 1.25)), relax=14,
                          density=lambda p: head.density(to_head(p)),
                          snap=[(lambda p, g=g: g(to_head(p)),
                                 None if inner is None else (lambda p, inner=inner: from_head(inner(to_head(p)))), off)
                                for g, inner, off in head.FEATURES])
    # the lacquer (lips, brows, lash line) is a front-projected texture in the game, so the face carries
    # no vertex paint; its grain offset is fixed because the shader places the texture from it
    add("face", "Head", "wood_face", v, q, normals=n, hard=False, grain=Frame(H0, UP, LEFT), grain_offset=FACE_GRAIN)
    for s, sx in (("l", 1), ("r", -1)):
        c = from_head(V(-sx * head.EYE[0], head.EYE[1], head.EYE[2]))
        ef = Frame(c, FWD, LEFT)
        ev, efc = gen.lathe(gen.arc(0.0, head.EYE_R, 0, 180, 25), 48)
        add("eye_" + s, "eye_" + s, "eye", ef.w(ev), efc, grain=ef, sharp=180)

    # open-faced helm: a hood of dark wood closed above the brow, its skull carved in shallow flutes
    vb, v1, W0 = HELM_VB, 0.30, np.radians(62)
    vs = np.concatenate([vb * (1 - (1 - np.linspace(0, 1, 25)) ** 2.0), np.linspace(vb, 1, 31)[1:]])
    us = np.linspace(0, 1, 141)                 # ten columns to a flute, so every ridge runs down a column

    def cover(v):
        t = np.clip((v - v1) / (vb - v1), 0, 1)
        w = W0 * (1 - t ** 3) ** (1 / 3) * (1 - 0.22 * np.clip((v1 - v) / v1, 0, 1) ** 2)
        return np.where(v >= vb, np.pi, np.pi - w)

    U, Vv = np.meshgrid(us, vs, indexing="ij")
    AL = (2 * U - 1) * cover(Vv)
    Ro = V(0.0865, 0.1070, 0.1020)
    C = from_head(V(0, -0.012, 0.022))
    outer = from_head(helmet_point(AL, Vv, Ro, 1.0))
    inner = from_head(helmet_point(AL, Vv, Ro - 0.006))
    pv, pf = gen.patch(outer, inner)
    add("helm", "Head", "wood_dark", pv, pf, grain=Frame(H0, FWD, LEFT), sharp=50)
    mid = 0.5 * (outer + inner)
    jb = int(np.argmin(np.abs(vs - vb)))
    loop = np.concatenate([mid[:, 0, :], mid[-1, 1:jb + 1, :], mid[0, jb - 1:0:-1, :]])
    for _ in range(2):                          # ease the corners of the opening so the rim sweeps round them
        loop = 0.5 * loop + 0.25 * (np.roll(loop, 1, axis=0) + np.roll(loop, -1, axis=0))
    tv, tf = gen.tube(loop, 0.0042, 12, closed=True)
    add("helm_rim", "Head", "brass", tv, tf)
    # a fine brass stringing line let into the wood a finger's width in from the rim
    k = 5
    line = np.concatenate([outer[k:-k, 2, :], outer[-1 - k, 3:jb + 2, :], outer[k, jb + 1:2:-1, :]])
    tv, tf = gen.tube(line + S.normalize(line - C) * 0.0003, 0.0012, 8, closed=True)
    add("helm_inlay", "Head", "brass", tv, tf)
    # brow band right round the skull, carrying the rivets
    bv = vb + np.array([0.010, 0.016, 0.026, 0.035, 0.044, 0.054, 0.060])
    proud = np.array([0.0004, 0.0019, 0.0025, 0.0026, 0.0025, 0.0019, 0.0004])
    alb = (2 * np.linspace(0, 1, 141) - 1) * np.pi
    b_out = np.stack([helmet_point(alb, np.full(len(alb), bv[j]), Ro + proud[j]) for j in range(len(bv))], axis=1)
    b_in = np.stack([helmet_point(alb, np.full(len(alb), bv[j]), Ro - 0.001) for j in range(len(bv))], axis=1)
    pv, pf = gen.patch(from_head(b_out), from_head(b_in))
    add("helm_band", "Head", "brass", pv, pf, sharp=60)
    # comb over the crown from brow to nape, with a boss where it meets the band
    crest = np.concatenate([outer[-1, jb:, :], outer[70, -2:0:-1, :]])
    tv, tf = gen.tube(crest + (crest - C) * 0.02, 0.0050, 10, squash=1.6)
    add("helm_comb", "Head", "brass", tv, tf)
    p = from_head(helmet_point(np.array(np.pi), np.array(vb + 0.035), Ro + 0.0036))
    rf = Frame(p, p - C, UP)
    rv, rfc = gen.dome(0.0078, 0.0048, 20, 4)
    add("helm_boss", "Head", "brass", rf.w(rv), rfc)
    # brow band rivets and temple rosettes
    for sx in (1, -1):
        for k, a in enumerate((158, 140, 122, 104, 84, 62, 40, 18)):
            p = from_head(helmet_point(np.array(np.radians(a) * sx), np.array(vb + 0.035), Ro + 0.0024))
            rf = Frame(p, p - C, UP)
            rv, rfc = gen.dome(0.0034, 0.0023, 16, 3)
            add("helm_rivet_%d_%d" % (k, sx), "Head", "brass", rf.w(rv), rfc)
        p = from_head(helmet_point(np.array(np.radians(98) * sx), np.array(0.36), Ro))
        rf = Frame(p, (p - C) * V(1, 1, 0.3), UP)
        gv, gf = gen.gear(12, 0.0125, 0.0158, r_hole=0.0035, spokes=0)
        add("helm_rosette_%d" % sx, "Head", "brass", rf.w(gv + V(0, 0, 0.0035)), gf, thickness=-0.004)
        gv, gf = gen.dome(0.0048, 0.004, 16, 3)
        add("helm_rosette_boss_%d" % sx, "Head", "brass", rf.w(gv + V(0, 0, 0.003)), gf)


# ============================================================== clockwork and sword

def clockwork():
    v, f = gen.lathe_ring([(-0.004, WIN_R - 0.003), (-0.004, WIN_R + 0.0055), (0.0005, WIN_R + 0.0065), (0.004, WIN_R + 0.004),
                           (0.004, WIN_R - 0.001), (0.001, WIN_R - 0.003)], 48)
    add("bezel", "spine_03", "brass", Frame(V(0, -0.1235, WIN_C[2]), FWD, LEFT).w(v), f)
    v, f = gen.lathe([(0.0, 0.0), (0.0, WIN_R + 0.002), (0.0012, WIN_R + 0.002), (0.0012, 0.0)], 48)
    add("movement_plate", "spine_03", "brass_dark", Frame(V(0, -0.1005, WIN_C[2]), FWD, LEFT).w(v), f)
    for name, g in GEARS.items():
        gf = Frame(g["o"], FWD, LEFT)
        v, f = gen.gear(g["teeth"], g["root"], g["tip"], r_hole=0.0022, spokes=g["spokes"])
        add(name, name, "brass", gf.w(v + V(0, 0, 0.0025)), f, thickness=-0.005)
        v, f = gen.lathe([(-0.006, 0.0), (-0.006, 0.0022), (0.0040, 0.0022), (0.0052, 0.0012), (0.0055, 0.0)], 10)
        add(name + "_arbor", "spine_03", "steel", gf.w(v), f)
    # bridge bar across the movement
    bfr = Frame(V(0.004, -0.1175, WIN_C[2] - 0.014), V(0.94, 0, 0.34), FWD)
    v, f = gen.box((0.0018, 0.0035, 0.030))
    add("bridge", "spine_03", "brass_dark", bfr.w(v), f, bevel=0.0006)

    kf = Frame(V(0, 0.098, 1.400), BACK, LEFT)
    v, f = gen.lathe([(0.0, 0.0), (0.0, 0.0105), (0.004, 0.0105), (0.006, 0.0050), (0.036, 0.0042), (0.040, 0.0060),
                      (0.043, 0.0042), (0.043, 0.0)], 16)
    add("key_shaft", "key", "brass", kf.w(v), f)
    for sx in (1, -1):
        rf = Frame(kf.w((sx * 0.0185, 0, 0.056)), kf.dir((0, 1, 0)), kf.dir((1, 0, 0)))
        v, f = gen.lathe_ring([(-0.0022, 0.0105), (-0.0022, 0.0165), (0.0, 0.0178), (0.0022, 0.0165), (0.0022, 0.0105),
                               (0.0, 0.0095)], 24)
        add("key_bow_%d" % sx, "key", "brass", rf.w(v), f)
    v, f = gen.box((0.006, 0.0022, 0.008))
    add("key_neck", "key", "brass", kf.w(v + V(0, 0, 0.047)), f, bevel=0.0007)
    v, f = gen.lathe_ring([(0.0, 0.010), (0.0, 0.0165), (0.0030, 0.0175), (0.0055, 0.0150), (0.0055, 0.010)], 24)
    add("key_escutcheon", "spine_03", "brass", kf.w(v + V(0, 0, 0.002)), f)


def sword():
    sf = Frame(GRIP, BLADE_DIR, LEFT)              # local x = blade width, y = thickness, z = toward the tip
    z0, z1 = 0.058, 0.840
    rings, verts, faces = [], [], []
    N = 28
    for k in range(N + 1):
        t = k / N
        z = z0 + (z1 - z0) * (1 - (1 - t) ** 1.15)
        tip = np.clip((t - 0.90) / 0.10, 0, 1)
        w = (0.0235 - 0.0075 * t) * (1 - tip ** 1.6)
        th = (0.0030 - 0.0014 * t) * (1 - 0.8 * tip)
        fu = 0.0011 * np.clip(1 - t / 0.62, 0, 1) ** 0.5
        if k == N:
            rings.append([len(verts)])
            verts.append((0, 0, z1))
            continue
        sec = [(w, 0), (0.42 * w, th), (0.16 * w, th - fu * 0.2), (0, th - fu), (-0.16 * w, th - fu * 0.2), (-0.42 * w, th),
               (-w, 0), (-0.42 * w, -th), (-0.16 * w, -th + fu * 0.2), (0, -th + fu), (0.16 * w, -th + fu * 0.2), (0.42 * w, -th)]
        rings.append(list(range(len(verts), len(verts) + len(sec))))
        verts += [(x, y, z) for x, y in sec]
    for A, B in zip(rings[:-1], rings[1:]):
        m = len(A)
        for k in range(m):
            k1 = (k + 1) % m
            faces.append((A[k], A[k1], B[0]) if len(B) == 1 else (A[k], A[k1], B[k1], B[k]))
    faces.append(tuple(reversed(rings[0])))
    add("blade", "weapon_r", "steel", sf.w(np.array(verts)), faces, sharp=25, grain=sf)
    # guard: gently swept quillons with rounded finials
    xs = np.linspace(-0.098, 0.098, 23)
    pts = np.stack([xs, np.zeros_like(xs), 0.050 + 0.016 * (xs / 0.098) ** 2], axis=1)
    rad = 0.0072 - 0.0026 * np.abs(xs / 0.098) ** 1.5
    v, f = gen.tube(sf.w(pts), rad, 10, squash=0.8)
    add("guard", "weapon_r", "brass", v, f)
    for sx in (1, -1):
        ff = Frame(sf.w((sx * 0.098, 0, 0.066)), sf.dir((sx, 0, 0.3)), sf.dir((0, 1, 0)))
        v, f = gen.lathe(gen.arc(0.003, 0.0070, 180, 0, 9), 12)
        add("guard_finial_%d" % sx, "weapon_r", "brass", ff.w(v), f)
    v, f = gen.lathe(gen.turned([(0.040, 0.0), (0.041, 0.0125), (0.046, 0.0150), (0.054, 0.0150), (0.060, 0.0120), (0.061, 0.0)], 2), 16, sy=0.72)
    add("guard_block", "weapon_r", "brass", sf.w(v), f)
    v, f = gen.lathe(gen.turned([(-0.052, 0.0), (-0.051, 0.0085), (-0.040, 0.0091), (-0.010, 0.0102), (0.020, 0.0098),
                             (0.040, 0.0090), (0.042, 0.0)], 3), 20, sy=0.82)
    add("grip", "weapon_r", "leather", sf.w(v), f, grain=sf)
    for z in (-0.046, -0.016, 0.014, 0.038):
        v, f = gen.lathe_ring([(z - 0.0012, 0.0078), (z - 0.0012, 0.0103), (z, 0.0108), (z + 0.0012, 0.0103), (z + 0.0012, 0.0078)], 20, sy=0.82)
        add("grip_wire_%d" % int(z * 1000), "weapon_r", "brass", sf.w(v), f)
    pfm = Frame(sf.w((0, 0, -0.070)), sf.dir((0, 1, 0)), sf.dir((1, 0, 0)))
    v, f = gen.gear(12, 0.0185, 0.0228)
    add("pommel", "weapon_r", "brass", pfm.w(v + V(0, 0, 0.007)), f, thickness=-0.014)
    for sy in (1, -1):
        v, f = gen.dome(0.0100, 0.0050)
        add("pommel_boss_%d" % sy, "weapon_r", "brass", pfm.w(v * V(1, 1, sy) + V(0, 0, sy * 0.0068)), f)


# ============================================================== assembly

MATS = {
    "wood_light": dict(base=(0.60, 0.38, 0.20), rough=0.38),
    "wood_face": dict(base=(0.66, 0.45, 0.27), rough=0.34),
    "wood_dark": dict(base=(0.17, 0.085, 0.045), rough=0.28),
    "brass": dict(base=(0.86, 0.62, 0.26), rough=0.28, metallic=1.0),
    "brass_dark": dict(base=(0.42, 0.29, 0.13), rough=0.40, metallic=1.0),
    "steel": dict(base=(0.74, 0.76, 0.80), rough=0.22, metallic=1.0),
    "leather": dict(base=(0.16, 0.075, 0.04), rough=0.6),
    "cloth": dict(base=(0.05, 0.16, 0.14), rough=0.85),
    "eye": dict(base=(0.9, 0.87, 0.8), rough=0.06),
}


def material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bl.clay(name, **{k: v for k, v in MATS[name].items()}, vertex_color=(name == "wood_face"))
    if name == "eye":
        nt = m.node_tree
        bsdf = nt.nodes["Principled BSDF"]
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UV2"
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        div = nt.nodes.new("ShaderNodeMath")
        div.operation = "DIVIDE"
        div.inputs[1].default_value = head.EYE_R
        ramp = nt.nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "CONSTANT"
        e = ramp.color_ramp.elements
        e[0].position, e[0].color = 0.0, (0.90, 0.87, 0.80, 1)
        e[1].position, e[1].color = 0.905, (0.28, 0.15, 0.05, 1)
        e.new(0.915).color = (0.62, 0.36, 0.10, 1)
        e.new(0.975).color = (0.02, 0.015, 0.01, 1)
        nt.links.new(uv.outputs[0], sep.inputs[0])
        nt.links.new(sep.outputs["X"], div.inputs[0])
        nt.links.new(div.outputs[0], ramp.inputs[0])
        nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    return m


def realize(only=None):
    """Every piece, and its mirror image, as an object in the rest pose with its bone as its one vertex group."""
    objs = []
    for pc in PIECES:
        if only and not any(pc["name"].startswith(o) for o in only):
            continue
        for side in ((1, -1) if pc["mirror"] else (1,)):
            v = pc["verts"] * V(side, 1, 1)
            faces = pc["faces"] if side == 1 else [tuple(reversed(f)) for f in pc["faces"]]
            nrm = None if pc["normals"] is None else pc["normals"] * V(side, 1, 1)
            name = pc["name"] if side == 1 else pc["name"] + "_R"
            bone = pc["bone"] if side == 1 else pc["bone"][:-2] + "_r"
            ob = bl.mesh_object(name, v, faces, nrm, pc["colors"], pc["hard"], pc["thickness"], pc["sharp"], pc["bevel"])
            me = ob.data
            me.materials.append(material(pc["mat"]))
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            g = pc["grain"].l(co * V(side, 1, 1))
            rng = np.random.default_rng(zlib.crc32(name.encode()))      # each piece's own grain, whatever else is built
            if pc["mat"] != "eye":
                ang = rng.uniform(0, 2 * np.pi)
                off = V(np.cos(ang), np.sin(ang), 0) * rng.uniform(0.05, 0.16) + V(0, 0, rng.uniform(-2, 2))
                g = g + (off if pc["grain_offset"] is None else pc["grain_offset"])
            bl.grain_layers(me, g, rng.uniform(0, 1))
            for bone, weights in (pc["skin"](co) if pc["skin"] else {bone: np.ones(len(co))}).items():
                vg = ob.vertex_groups.new(name=bone)
                for weight in np.unique(weights[weights > 0]):
                    vg.add(np.flatnonzero(weights == weight).tolist(), float(weight), "REPLACE")
            objs.append(ob)
    return objs


def bind(arm, objs):
    body = bl.join(objs, "Knight")
    mod = body.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    return body


def set_pose(arm, name, frame):
    act = bpy.data.actions[name]
    arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    bpy.context.scene.frame_set(int(frame))


def every_frame(arm):
    """Poses the rig in each frame of each clip in turn, yielding its name, and leaves it at rest."""
    for name in CLIPS:
        first, last = bpy.data.actions[name].frame_range
        for frame in range(int(first), int(last) + 1):
            set_pose(arm, name, frame)
            yield "%s:%d" % (name, frame)
    unpose(arm)


def unpose(arm):
    arm.animation_data_clear()
    for pb in arm.pose.bones:
        pb.matrix_basis.identity()


def held(arm, pose):
    """Poses the rig in the one `pose`, a clip and frame as "Action:frame", yielding its name."""
    set_pose(arm, *pose.split(":"))
    yield pose


ZOOMS = {"full": ((0, 0, 0.93), 2.02, (520, 1000)), "upper": ((0, 0, 1.36), 1.05, (640, 640)),
         "head": ((0, -0.03, 1.66), 0.34, (600, 600))}


def carried(bone):
    """The vertices at rest of every piece that `bone` carries, or carries most of the weight of."""
    parts = []
    for pc in PIECES:
        if pc["skin"]:
            parts.append(pc["verts"][pc["skin"](pc["verts"]).get(bone, np.zeros(len(pc["verts"]))) > 0.5])
        elif pc["bone"] == bone:
            parts.append(pc["verts"])
        elif pc["mirror"] and bone == pc["bone"][:-2] + "_r":
            parts.append(pc["verts"] * V(-1, 1, 1))
    return np.concatenate(parts)


def hung():
    """What `hang` turns, parents first, and her legs for it to rest on: each leg bone's pieces as spheres."""
    hinges = []
    for name in PLATES:
        for bone, s, _ in plate_bones(name):
            tuck = PLATE_TUCKS.get(name, 0.0)
            hinges.append(hang.Hinge(bone, carried(bone), (-tuck, SKIRT_SWING[1]), tuck=tuck, thighs=s))
    for name in PANELS if SEAT == "tabard" else ():
        for s, _ in SIDES:
            above = None
            for k in range(len(PANEL_JOINTS)):
                bone = panel_bone(name, k, s)
                above = hang.Hinge(bone, carried(bone), PANEL_BEND if above else PANEL_SWING, above,
                                   PANEL_TUCKS[k] if name == "back" else 0.0, s)
                hinges.append(above)
    legs = {part + s: hang.spheres(carried(part + s)) for part in ("thigh", "poleyn", "calf", "foot") for s in ("_l", "_r")}
    return hinges, legs


def preview(arm, path, views, zoom):
    if zoom in ZOOMS:
        target, scale, res = ZOOMS[zoom]
        if opt("--pose"):
            hips = arm.pose.bones["pelvis"].head
            target = (hips.x, hips.y, target[2] + hips.z - 0.917)
    else:
        bpy.context.view_layer.update()
        target, scale, res = tuple(arm.matrix_world @ arm.pose.bones[zoom].head), float(opt("--scale", "0.34")), (600, 600)
    bl.turnaround(path, views, target, scale, res, bl.studio((2.6, 1.2, 2.4), (900, 220, 600)), 40)


def export(arm, body, path, extra=()):
    for ob in (body, *extra):
        ob.parent = arm
    arm.animation_data_create()
    arm.animation_data.action = None
    for name in CLIPS:
        act = bpy.data.actions.get(name)
        if act is None:
            print("MISSING CLIP", name)
            continue
        tr = arm.animation_data.nla_tracks.new()
        tr.name = name
        st = tr.strips.new(name, int(act.frame_range[0]), act)
        if hasattr(st, "action_slot") and act.slots:
            st.action_slot = act.slots[0]
        tr.mute = False
    bl.export_glb(path, (arm, body, *extra), active=arm, export_animations=True, export_animation_mode="NLA_TRACKS",
                  export_force_sampling=True, export_frame_step=1, export_skins=True, export_def_bones=False,
                  export_tangents=False, export_vertex_color="ACTIVE", export_all_vertex_colors=True,
                  export_active_vertex_color_when_no_material=True, export_optimize_animation_size=False,
                  export_anim_slide_to_zero=True, export_reset_pose_bones=True)


def main():
    t0 = time.time()
    arm, J, T = load_rig()
    roll.tuck_opening(arm, bpy.data.actions["Roll"])
    add_bones(arm, J, T)
    only = opt("--only")
    only = only.split(",") if only else None
    torso(J)
    arms(J, T)
    hands(J, T)
    legs(J, T)
    head_pieces(int(opt("--res", "96")))
    clockwork()
    sword()
    if RECESSED:
        block = seat_block(J)
        hang.bake(arm, {name: bpy.data.actions[name] for name in CLIPS}, *hung(), set_pose,
                  lambda p: np.minimum(block(p), S.plane(p, V(0, 0, SEAT_FLOOR), DOWN)))
        unpose(arm)
    objs = realize(only)
    if opt("--gaps"):
        movers, others = (side.split(",") for side in opt("--gaps").split("/"))
        gaps.report(arm, objs, movers, others, held(arm, opt("--pose")) if opt("--pose") else every_frame(arm))
    body = bind(arm, objs)
    print("BUILT pieces=%d verts=%d polys=%d  t=%.1fs" % (len(PIECES), len(body.data.vertices), len(body.data.polygons), time.time() - t0))
    if opt("--pose"):
        set_pose(arm, *opt("--pose").split(":"))
    if opt("--preview"):
        views = [tuple(float(x) for x in a.split("/")) for a in opt("--views", "0,-40,-90,180").split(",")]
        preview(arm, opt("--preview"), views, opt("--zoom", "full"))
    if opt("--out"):
        caster = shadow.shadow_mesh(body, 3000)
        print("SHADOW MESH tris=%d" % len(caster.data.polygons))
        export(arm, body, opt("--out"), [caster])
        build.face_paint(os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "textures", "knight", "face_paint.png"),
                         head, FACE_GRAIN)
    print("DONE t=%.1fs" % (time.time() - t0))


main()

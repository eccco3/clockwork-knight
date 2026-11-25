"""Builds Rosalyn: sculpts every piece, bakes her dress and hair from the sculpt, rigs and animates her, and
exports GLB with her clips.

  blender --background --python build_rosalyn.py -- [--out rosalyn.glb] [--shots dir] [--detail 1.0] [--size 2048]
          [--clay a.png] [--pose stand] [--clip Idle --at 0.25] [--only a,b] [--wire] [--views 0,-40,-90,180]
          [--zoom full,upper,head,face,hand,clasp,feet] [--light 1.0]

--clay alone renders the bare game mesh, for judging forms quickly; --pose puts it in one of clips.POSES first,
and --clip in the pose one of clips.CLIPS has at the phase --at. --out and --shots run the whole build; --shots
renders her turnarounds, clay and painted, her test poses and the idle's contact sheets.
--detail scales every lattice, and with it the triangle count: 1.0 comes to about 225,000 of her 300,000, 0.7 to half that.
Rest pose in Blender space: +X is her left, -Y is forward, +Z up.

Her wood, brass and eyes carry the game's solid grain space instead of textures, and the game dresses them
by material name (scripts/looks.gd). The paint on her face is written beside this build's other textures.
"""
import bpy, sys, os, time, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, bake, build, pieces as P, rig as R
from sculpt.bl import argv, opt
from sculpt.pieces import under, either, on_left
from sculpt.sdf import V
from sculpt.gen import Frame
from rosalyn import body, head, hair, dress, trim, rig, pose, clips

NAME = "rosalyn"                                # her working name: every file and object this build makes is called after it
BUDGET = 300000                                 # triangles she may have; --detail 1.0 uses three quarters of them
CLAY_LIGHT = 0.15                               # pale clay wants the lamps this much dimmer than her wood
ROOT = os.path.dirname(os.path.dirname(HERE))
FACE_PAINT = os.path.join(ROOT, "assets", "textures", NAME, "face_paint.png")
HEAD = body.HEAD
UPRIGHT = Frame(V(0, 0, 0), body.UP, body.LEFT)
FACE_GRAIN = V(0.09, 0.05, 0.60)                # the head frame's origin in the face's grain space
BAKED = {"cloth": dict(grain=bake.weave), "hair": dict(grain=bake.pores)}
CARVED = {                                      # how Blender previews what the game dresses by name
    "wood": dict(base=(0.62, 0.44, 0.27), rough=0.30),
    "wood_face": dict(base=(0.66, 0.48, 0.30), rough=0.30, vertex_color=True),
    "lacquer": dict(base=(0.72, 0.52, 0.16), rough=0.22),
    "brass": dict(base=(0.86, 0.62, 0.26), rough=0.28, metallic=1.0),
    "eye": dict(base=(1.0, 1.0, 1.0), rough=0.06, vertex_color=True),
}


def in_head(f):
    return lambda p: f(HEAD.l(p))


def on_head(wrap):
    """A mesh made in the head frame, set on her shoulders."""
    def mesh(detail):
        v, q, n, lat = wrap(detail)
        return HEAD.w(v), q, HEAD.dir(n), lat
    return mesh


FACE, HAIR = in_head(head.field), in_head(hair.field)
FACE_WOOD = dict(mat="wood_face", grain=Frame(HEAD.o, body.UP, body.LEFT), grain_offset=FACE_GRAIN, tint=in_head(head.paint))
SPECS = {                                       # a piece with a `bone` rides it whole; the rest are skinned by rig.weights
    "head": dict(FACE_WOOD, mesh=on_head(head.wrap), field=FACE, mirror=False, bone="head",
                 hidden=either(under(body.chest, 0.0015), under(HAIR, 0.0012))),
    "hair": dict(mat="hair", mesh=on_head(hair.wrap), field=HAIR, detail=in_head(hair.detail), paint=in_head(hair.paint),
                 seam=hair.seam, mirror=False, boost=1.0, hidden=under(FACE, 0.0012), bone="head"),
    "chest": dict(mat="wood", boxes=body.chest_boxes, field=body.chest, mirror=False, grain=UPRIGHT,
                  hidden=either(under(FACE, 0.0015), under(on_left(body.arm), 0.0015), under(dress.cloth, 0.003))),
    "arm": dict(mat="wood", boxes=body.arm_boxes, field=body.arm, mirror=True, hidden=under(dress.cloth, 0.003),
                grain=Frame(body.SHOULDER, body.WRIST - body.SHOULDER, body.LEFT)),
    "leg": dict(mat="wood", boxes=body.leg_boxes, field=body.leg, mirror=True, grain=UPRIGHT,
                hidden=either(under(dress.cloth, 0.004), under(body.shoe, 0.0015))),
    "shoe": dict(mat="lacquer", mesh=body.shoe_wrap, field=body.shoe, mirror=True, hidden=under(body.leg, 0.0015),
                 grain=Frame(body.ANKLE, body.FWD, body.LEFT)),
    "dress": dict(mat="cloth", boxes=dress.boxes, field=dress.cloth, detail=dress.detail, paint=dress.paint, seam=dress.seam,
                  mirror=False, boost=1.0, grain=0.20, pitch=0.0018, grain_tint=0.08,
                  hidden=either(under(body.torso, 0.002), under(on_left(body.arm), 0.002), under(on_left(body.leg), 0.003))),
}


def small_parts():
    """Eyes, their sleeping lids and brass: made by formula, each in the frame its grain runs in."""
    v, faces, n, tint = head.eyeball()
    eye = dict(name="eye", mat="eye", v=rig.EYE.w(v), q=faces, n=rig.EYE.dir(n), tint=lambda p: tint, mirror=True,
               grain=rig.EYE, grain_offset=0.0, bone="eye")
    v, faces, n = head.lid()
    v, n = HEAD.w((v + head.EYE) * P.MIRROR), HEAD.dir(n * P.MIRROR)
    lid = dict(FACE_WOOD, name="lid", v=v, q=P.outward(v, faces, n), n=n, mirror=True, bone="lid")
    return [eye, lid] + trim.parts()


def sides(pieces):
    """Each piece once for each side it has, with whether that is the right."""
    return [(pc, right) for pc in pieces for right in ((False, True) if pc["mirror"] else (False,))]


def ridden(pieces, mat):
    """The one bone that a baked material's pieces ride, or None if they are skinned by where they stand."""
    (bone,) = {pc.get("bone") for pc in pieces if pc["mat"] == mat}
    return bone


def carve(pieces, seed=11):
    """The pieces the game dresses, and their mirror images, as one skinned object in grain space. Each is cut
    from its own block: its grain is set off by `grain_offset`, or at random."""
    rng = np.random.default_rng(seed)
    objs = []
    for pc in pieces:
        for side, (v, faces, n) in enumerate(P.sides(pc)):
            ob = bl.mesh_object(pc["name"], v, faces, n, pc["tint"](v) if "tint" in pc else None, hard=n is None,
                                thickness=pc.get("thickness", 0.0))
            me = ob.data
            me.materials.append(bpy.data.materials.get(pc["mat"]) or bl.clay(pc["mat"], **CARVED[pc["mat"]]))
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            turn = rng.uniform(0, 2 * np.pi)
            offset = V(np.cos(turn), np.sin(turn), 0) * rng.uniform(0.05, 0.16) + V(0, 0, rng.uniform(-2, 2))
            g = pc["grain"].l(co.reshape(-1, 3) * (P.MIRROR if side else 1.0))
            bl.grain_layers(me, g + pc.get("grain_offset", offset), rng.uniform(0, 1))
            rig.weigh(ob, pc.get("bone"), bool(side))
            objs.append(ob)
    ob = bl.join(objs, NAME.capitalize())
    cut = ob.modifiers.new("ngons", "TRIANGULATE")              # the exporter's tangents need triangles and quads
    cut.min_vertices, cut.keep_custom_normals = 5, True
    bpy.ops.object.modifier_apply(modifier=cut.name)
    return ob


ZOOMS = {"full": ((0, 0, 0.93), 2.02, (520, 1000)), "upper": ((0, 0, 1.36), 1.05, (640, 640)), "neck": ((0, -0.03, 1.44), 0.50, (720, 720)),
         "head": ((0, -0.03, 1.635), 0.34, (600, 600)), "face": ((0, -0.03, 1.605), 0.19, (720, 720)),
         "hand": ((0.36, -0.06, 0.86), 0.30, (720, 720)), "feet": ((0, 0, 0.17), 0.60, (720, 720)),
         "clasp": ((0, -0.14, 0.97), 0.36, (720, 720)), "open": ((0, -0.05, 1.25), 1.20, (640, 640)),
         "wrist": ((0.35, -0.05, 0.91), 0.12, (720, 720)),
         "eye": ((0.028, -0.08, 1.630), 0.055, (720, 720)), "mouth": ((0, -0.10, 1.570), 0.075, (720, 720))}
POSED = {"stand": ("full", "upper", "clasp"), "asleep": ("face",), "glance": ("head",), "bow": ("full",), "sway": ("full",),
         "open": ("open",), "raise": ("open",)}  # the poses --shots shows, and the zooms of each
CLASP_VIEWS = [0, -50, 50, (0, 55)]             # her hands from before her, from either side and from above
SHEETS = {"full": [0, -90], "face": [0]}        # the idle's contact sheets: her weight from before her and the side, her eyes
STEPS, ACROSS = 16, 8                           # frames on each, evenly from the clip's start, and to a row


def turnaround(path, views, zoom, light=1.0, samples=40):
    """The knight's preview lighting and scale, so the two stand side by side; `light` and --light scale the lamps."""
    target, scale, res = ZOOMS[zoom]
    dim = light * float(opt("--light", "1.0"))
    bl.turnaround(path, views, target, scale, res, bl.studio((2.6, 1.2, 2.4), (900 * dim, 220 * dim, 600 * dim)), samples)


def contact_sheet(path, skeleton, action, zoom):
    """A clip at STEPS even frames from its start, left to right ACROSS to a row, view after view."""
    R.use(skeleton, action)
    width, strips = ZOOMS[zoom][2][0], []
    for k in range(STEPS):
        bpy.context.scene.frame_set(round(k * action.frame_range[1] / STEPS))
        turnaround(path + ".step.png", SHEETS[zoom], zoom, samples=24)
        strips.append(bl.read_image(path + ".step.png"))
    os.remove(path + ".step.png")
    rows = [np.concatenate([s[:, v * width:(v + 1) * width] for s in strips[k:k + ACROSS]], axis=1)
            for v in range(len(SHEETS[zoom])) for k in range(0, STEPS, ACROSS)]
    bpy.data.images.remove(bl.save_image(path, np.concatenate(rows[::-1], axis=0)))
    R.use(skeleton, None)
    print("SHEET", path)


def asked():
    """The controls that --pose, or --clip and --at, ask for."""
    if opt("--clip"):
        return clips.CLIPS[opt("--clip")][0](float(opt("--at", "0")))
    return clips.POSES[opt("--pose")]


def export(path, skeleton, meshes, actions):
    R.shelve(skeleton, actions)
    bl.export_glb(path, [skeleton] + meshes, active=skeleton, export_animations=True, export_animation_mode="NLA_TRACKS",
                  export_force_sampling=True, export_optimize_animation_size=False, export_reset_pose_bones=True,
                  export_skins=True, export_tangents=True, export_vertex_color="NONE")


def main():
    t0 = time.time()
    bl.reset_scene()
    detail = float(opt("--detail", "1.0"))
    names = opt("--only").split(",") if opt("--only") else list(SPECS)
    views = [float(a) for a in opt("--views", "0,-40,-90,180").split(",")]
    zooms = opt("--zoom", "full").split(",")
    pieces = [P.sculpt(name, SPECS[name], detail) for name in names]
    for pc in pieces:
        pc["q"] = P.outward(pc["v"], pc["q"], pc["n"])
    pieces += small_parts()
    count = P.triangles(pieces)
    print("SCULPTED tris=%d of %d  t=%.1fs" % (count, int(BUDGET * detail * detail), time.time() - t0))
    if not (opt("--out") or opt("--shots")):
        if opt("--clay"):
            clay = build.clay_objects(pieces, "--wire" in argv, black=("eye",))
            if opt("--pose") or opt("--clip"):
                skeleton = rig.armature("rig")
                for ob, (pc, right) in zip(clay, sides(pieces)):
                    rig.weigh(ob, pc.get("bone"), right)
                    R.attach(ob, skeleton)
                pose.strike(skeleton, asked())
            for zoom in zooms:
                turnaround(opt("--clay").replace(".png", "_%s.png" % zoom), CLASP_VIEWS if zoom == "clasp" else views, zoom,
                           CLAY_LIGHT)
        return
    assert count <= BUDGET * max(detail, 1.0) ** 2, "over the triangle budget"

    folder = opt("--textures") or tempfile.mkdtemp(prefix=NAME + "_")
    baked = {mat: BAKED[mat] for mat in BAKED if any(pc["mat"] == mat for pc in pieces)}
    painted, clay = build.textures(pieces, baked, int(opt("--size", "2048")), folder, NAME)
    figure = [carve([pc for pc in pieces if pc["mat"] in CARVED])]
    for mat, look in zip(baked, painted):
        figure.append(build.assemble(NAME.capitalize() + mat.capitalize(), pieces, [mat], [look]))
        rig.weigh(figure[-1], ridden(pieces, mat))
    skeleton = rig.armature("rig")
    for ob in figure:
        R.attach(ob, skeleton)
        print("MESH %s: %d triangles, materials %s" % (ob.name, sum(len(f.vertices) - 2 for f in ob.data.polygons),
                                                       ", ".join(m.name for m in ob.data.materials)))
    actions = {name: pose.record(skeleton, name, clip, frames) for name, (clip, frames) in clips.CLIPS.items()}
    R.use(skeleton, None)
    pose.strike(skeleton, {})
    if opt("--shots"):
        grey = bl.clay("clay", base=(0.62, 0.60, 0.58), rough=0.55, vertex_color=False)
        dark = bl.clay("clay_eye", base=(0.01, 0.01, 0.01), rough=0.05, vertex_color=False)
        wears = [list(ob.data.materials) for ob in figure]
        bare = [[dark if m.name == "eye" else grey for m in wears[0]]] + [[c] for c in clay]
        for zoom, angles in (("full", views), ("upper", views), ("head", views), ("face", [0, -40, -90, 40]),
                             ("hand", [0, -90, 180, 90])):
            if opt("--zoom") and zoom not in zooms:
                continue
            for kind, mats, light in (("clay", bare, CLAY_LIGHT), ("painted", wears, 1.0)):
                for ob, slots in zip(figure, mats):
                    for k, m in enumerate(slots):
                        ob.data.materials[k] = m
                turnaround(os.path.join(opt("--shots"), "%s_%s.png" % (kind, zoom)), angles, zoom, light)
        for name in () if opt("--zoom") else POSED:
            pose.strike(skeleton, clips.POSES[name])
            for zoom in POSED[name]:
                turnaround(os.path.join(opt("--shots"), "pose_%s_%s.png" % (name, zoom)),
                           CLASP_VIEWS if zoom == "clasp" else views, zoom)
        pose.strike(skeleton, {})
        for zoom in () if opt("--zoom") else SHEETS:
            contact_sheet(os.path.join(opt("--shots"), "sheet_idle_%s.png" % zoom), skeleton, actions["Idle"], zoom)
    if opt("--out"):
        export(opt("--out"), skeleton, figure, actions.values())
        build.face_paint(FACE_PAINT, head, FACE_GRAIN)
    print("DONE t=%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()

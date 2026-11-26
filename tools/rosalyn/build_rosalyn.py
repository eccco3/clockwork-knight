"""Builds Rosalyn: sculpts every piece, bakes her dress and hair from the sculpt, rigs and animates her, and
exports GLB with her clips.

  blender --background --python build_rosalyn.py -- [--out rosalyn.glb] [--shots dir] [--detail 1.0] [--size 2048]
          [--clay a.png] [--pose stand] [--clip Idle --at 0.25] [--jaw 1.5] [--mouth ah [--pivot]] [--only a,b]
          [--wire] [--views 0,-40,-90,180] [--zoom full,upper,head,face,hand,clasp,feet,mouth] [--light 1.0]

--clay alone renders the bare game mesh, for judging forms quickly; --pose puts it in one of clips.POSES first,
and --clip in the pose one of clips.CLIPS has at the phase --at; --jaw opens her jaw that many degrees. --mouth
shows the face without lips instead, wearing the lip pieces carved in one of mouth.SHAPES, or with --pivot the
pivots' pieces in it; --only mouth builds that face and its pieces alone. --out and --shots run the whole build;
--shots renders her turnarounds, clay and painted, her test poses, each loop's contact sheets, with her brows at
rest, and a sheet of her mouths. --detail scales every lattice, and with it the triangle count: 1.0 comes to
about 225,000 of her 300,000, 0.7 to half that. Rest pose in Blender space: +X is her left, -Y is forward, +Z up.

Her wood, brass and eyes carry the game's solid grain space instead of textures, and the game dresses them
by material name (scripts/looks.gd). The paint on her face, and her brow apart from it, are written to
assets/textures/rosalyn.

Her face is an object of its own, and so is each part of the mouth trial, which only the game shows one way at a
time: the face without lips, every carved shape of lip pieces, and every piece on a pivot. The lip pieces ride no
skin; the game sets them on her head, and moves the pivots' pieces as the skeleton's extras `mouths` say.
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
from rosalyn import body, head, hair, dress, trim, rig, pose, clips, mouth

NAME = "rosalyn"                                # her working name: every file and object this build makes is called after it
BUDGET = 300000                                 # triangles she may have; --detail 1.0 uses three quarters of them
CLAY_LIGHT = 0.15                               # pale clay wants the lamps this much dimmer than her wood
ROOT = os.path.dirname(os.path.dirname(HERE))
FACE_PAINT = os.path.join(ROOT, "assets", "textures", NAME, "face_paint.png")
INLAID_PAINT = os.path.join(ROOT, "assets", "textures", NAME, "face_paint_inlaid.png")
BROW_PAINT = os.path.join(ROOT, "assets", "textures", NAME, "brow.png")
HEAD = body.HEAD
UPRIGHT = Frame(V(0, 0, 0), body.UP, body.LEFT)
FACE_GRAIN = V(0.09, 0.05, 0.60)                # the head frame's origin in the face's grain space
BAKED = {"cloth": dict(grain=bake.weave), "hair": dict(grain=bake.pores)}
CARVED = {                                      # how Blender previews what the game dresses by name
    "wood": dict(base=(0.62, 0.44, 0.27), rough=0.30),
    "wood_face": dict(base=(0.66, 0.48, 0.30), rough=0.30, vertex_color=True),
    "wood_face_inlaid": dict(base=(0.66, 0.48, 0.30), rough=0.30, vertex_color=True),
    "lacquer": dict(base=(0.72, 0.52, 0.16), rough=0.22),
    "lip": dict(base=(0.62, 0.24, 0.19), rough=0.18),
    "brass": dict(base=(0.86, 0.62, 0.26), rough=0.28, metallic=1.0),
    "eye": dict(base=(1.0, 1.0, 1.0), rough=0.06, vertex_color=True),
}
LIP_CLAY = (0.55, 0.30, 0.27)                   # the lip pieces' clay, to tell them from the face's


def in_head(f):
    return lambda p: f(HEAD.l(p))


def on_head(wrap):
    """A mesh made in the head frame, set on her shoulders."""
    def mesh(detail):
        v, q, n, lat = wrap(detail)
        return HEAD.w(v), q, HEAD.dir(n), lat
    return mesh


FACE, HAIR = in_head(head.field), in_head(hair.field)
FACE_WOOD = dict(mat="wood_face", grain=Frame(HEAD.o, body.UP, body.LEFT), grain_offset=FACE_GRAIN, tint=in_head(head.at_rest))
SPECS = {                                       # a piece with a `bone` rides it whole; the rest are skinned by rig.weights
    "head": dict(FACE_WOOD, mesh=on_head(head.wrap), field=FACE, mirror=False, bone="face", apart="Face",
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
INLAID = dict(FACE_WOOD, mat="wood_face_inlaid", tint=in_head(lambda p: head.at_rest(p, True)), mirror=False,
              mesh=on_head(lambda detail: head.wrap(detail, True)), bone="head", apart="FaceInlaid",
              hidden=either(under(body.chest, 0.0015), under(HAIR, 0.0012)))


def small_parts():
    """Eyes, their sleeping lids and brass: made by formula, each in the frame its grain runs in."""
    v, faces, n, tint = head.eyeball()
    eye = dict(name="eye", mat="eye", v=rig.EYE.w(v), q=faces, n=rig.EYE.dir(n), tint=lambda p: tint, mirror=True,
               grain=rig.EYE, grain_offset=0.0, bone="eye")
    v, faces, n = head.lid()
    v, n = HEAD.w((v + head.EYE) * P.MIRROR), HEAD.dir(n * P.MIRROR)
    lid = dict(FACE_WOOD, name="lid", v=v, q=P.outward(v, faces, n), n=n, mirror=True, bone="lid")
    return [eye, lid] + trim.parts()


def _camel(name):
    return "".join(word.capitalize() for word in name.split("_"))


def mouth_parts(detail):
    """The mouth trial's pieces: the face without lips, and the lip pieces, carved shapes and pivots, each shape and
    each pivot an object apart that rides no skin."""
    face = P.sculpt("inlaid", INLAID, detail)
    face["q"] = P.outward(face["v"], face["q"], face["n"])
    grain = Frame(HEAD.w(V(0, 0.080, -0.062)), body.LEFT, body.UP)
    out = [face]
    for name, (v, q, n) in mouth.pieces(detail).items():
        shape = name.split("_")[0] in mouth.SHAPES
        v, n = HEAD.w(v), HEAD.dir(n)
        out.append(dict(name="lip_" + name, mat="lip", v=v, q=P.outward(v, q, n), n=n, mirror=False, grain=grain,
                        skinned=False, apart=("Lips" + _camel(name.split("_")[0])) if shape else "Lip" + _camel(name)))
    return out


def head_move(m):
    """A move made in the head frame, as one in Blender's space."""
    h = np.eye(4)
    h[:3, :3], h[:3, 3] = HEAD.R, HEAD.o
    return h @ m @ np.linalg.inv(h)


def staged(pieces):
    """The pieces --mouth asks to see: the face with lips and no lip pieces, or the face without lips and the lip
    pieces of one shape, carved or, with --pivot, the pivots' pieces moved into it."""
    shape = opt("--mouth")
    if not shape:
        return [pc for pc in pieces if pc["mat"] not in ("wood_face_inlaid", "lip")]
    moves = mouth.poses()[shape]
    out = []
    for pc in pieces:
        part = pc["name"][4:] if pc["mat"] == "lip" else None
        if pc["name"] == "head" or (part is not None and (part in moves) != ("--pivot" in argv)):
            continue
        if part is not None and not part.startswith(shape + "_") and part not in moves:
            continue
        if part in moves:
            m = head_move(moves[part])
            pc = dict(pc, v=pc["v"] @ m[:3, :3].T + m[:3, 3], n=pc["n"] @ m[:3, :3].T)
        out.append(pc)
    return out


def lip_clay(ob):
    ob.data.materials[0] = bpy.data.materials.get("clay_lip") or bl.clay("clay_lip", LIP_CLAY, 0.4, False)


def clay_figure(pieces):
    """The pieces in clay, split as the game mesh is: an object for each `apart` name, skinned to a rig unless it
    rides no skin. Returns the rig and the objects."""
    skeleton = rig.armature("rig")
    groups = {}
    for pc in pieces:
        groups.setdefault(pc.get("apart", ""), []).append(pc)
    out = []
    for apart, group in groups.items():
        objs = build.clay_objects(group, black=("eye",))
        for ob, (pc, right) in zip(objs, sides(group)):
            if pc["mat"] == "lip":
                lip_clay(ob)
            if pc.get("skinned", True):
                rig.weigh(ob, pc.get("bone"), right)
        out.append(bl.join(objs, NAME.capitalize() + apart))
        if group[0].get("skinned", True):
            R.attach(out[-1], skeleton)
    return skeleton, out


def sides(pieces):
    """Each piece once for each side it has, with whether that is the right."""
    return [(pc, right) for pc in pieces for right in ((False, True) if pc["mirror"] else (False,))]


def ridden(pieces, mat):
    """The one bone that a baked material's pieces ride, or None if they are skinned by where they stand."""
    (bone,) = {pc.get("bone") for pc in pieces if pc["mat"] == mat}
    return bone


def carve(pieces, seed=11):
    """The pieces the game dresses, and their mirror images, in grain space: one skinned object of all but those
    that stand `apart`, which make an object of each name, skinned unless a piece rides no skin. Each is cut from
    its own block: its grain is set off by `grain_offset`, or at random. Returns the objects and whether each is
    skinned."""
    rng = np.random.default_rng(seed)
    groups, skinned = {}, {}
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
            apart = pc.get("apart", "")
            skinned[apart] = pc.get("skinned", True)
            if skinned[apart]:
                rig.weigh(ob, pc.get("bone"), bool(side))
            groups.setdefault(apart, []).append(ob)
    out = []
    for apart, objs in groups.items():
        ob = bl.join(objs, NAME.capitalize() + apart)
        cut = ob.modifiers.new("ngons", "TRIANGULATE")          # the exporter's tangents need triangles and quads
        cut.min_vertices, cut.keep_custom_normals = 5, True
        bpy.ops.object.modifier_apply(modifier=cut.name)
        out.append((ob, skinned[apart]))
    return out


ZOOMS = {"full": ((0, 0, 0.93), 2.02, (520, 1000)), "upper": ((0, 0, 1.36), 1.05, (640, 640)), "neck": ((0, -0.03, 1.44), 0.50, (720, 720)),
         "head": ((0, -0.03, 1.635), 0.34, (600, 600)), "face": ((0, -0.03, 1.605), 0.19, (720, 720)),
         "hand": ((0.36, -0.06, 0.86), 0.30, (720, 720)), "feet": ((0, 0, 0.17), 0.60, (720, 720)),
         "clasp": ((0, -0.14, 0.97), 0.36, (720, 720)), "open": ((0, -0.05, 1.25), 1.20, (640, 640)),
         "wrist": ((0.35, -0.05, 0.91), 0.12, (720, 720)),
         "eye": ((0.028, -0.08, 1.630), 0.055, (720, 720)), "mouth": ((0, -0.10, 1.570), 0.075, (720, 720))}
POSED = {"stand": ("full", "upper", "clasp"), "asleep": ("face",), "glance": ("head",), "bow": ("full",), "sway": ("full",),
         "open": ("open",), "raise": ("open",)}  # the poses --shots shows, and the zooms of each
CLASP_VIEWS = [0, -50, 50, (0, 55)]             # her hands from before her, from either side and from above
SHEETS = {"full": [0, -90], "face": [0]}        # each loop's contact sheets: her weight from before her and the side, her eyes
STEPS, ACROSS = 16, 8                           # frames on each, evenly from the clip's start, and to a row
MOUTH_VIEWS = [0, -35]                          # the sheet of mouths: from before her and from her left


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


def mouth_sheet(path, skeleton, objects, light=1.0):
    """Every shape of mouth.SHAPES, left to right, three ways down: her lips parting on the jaw, the carved lip
    pieces swapped in, and the pivots' pieces moved into it; each from MOUTH_VIEWS, side by side."""
    by_name = {ob.name[len(NAME):]: ob for ob in objects}
    moves = mouth.poses()
    pivots = {"Lip" + _camel(part): part for part in moves["rest"]}
    rests = {name: by_name[name].matrix_world.copy() for name in pivots}

    def shown(name, way, shape):
        if name in ("Face", "FaceInlaid"):
            return (name == "Face") == (way == "jaw")
        if name in pivots:
            return way == "pivots"
        return way == "carved" and name == "Lips" + _camel(shape) if name.startswith("Lips") else True
    rows = []
    for way in ("jaw", "carved", "pivots"):
        tiles = []
        for shape in mouth.SHAPES:
            for name, ob in by_name.items():
                ob.hide_render = not shown(name, way, shape)
            for name, part in pivots.items():
                by_name[name].matrix_world = rests[name] if way != "pivots" else \
                    bl.Matrix(head_move(moves[shape][part]).tolist()) @ rests[name]
            pose.strike(skeleton, {"jaw": mouth.SHAPES[shape]["jaw"] if way == "jaw" else 0.0})
            turnaround(path + ".tile.png", MOUTH_VIEWS, "mouth", light)
            tiles.append(bl.read_image(path + ".tile.png"))
        rows.append(np.concatenate(tiles, axis=1))
    os.remove(path + ".tile.png")
    for name, ob in by_name.items():
        ob.hide_render = not shown(name, "jaw", "rest")
    for name in pivots:
        by_name[name].matrix_world = rests[name]
    pose.strike(skeleton, {})
    bpy.data.images.remove(bl.save_image(path, np.concatenate(rows[::-1], axis=0)))
    print("SHEET", path)


def asked():
    """The controls that --pose, or --clip and --at, ask for, with --jaw."""
    controls = clips.CLIPS[opt("--clip")][0](float(opt("--at", "0"))) if opt("--clip") else dict(clips.POSES.get(opt("--pose"), {}))
    return dict(controls, jaw=float(opt("--jaw", "0")))


def gltf(m):
    """A move in Blender's space as Godot reads it from glTF, y up: its basis' columns and its origin, flat."""
    c = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], dtype=np.float64)
    g = c @ m @ c.T
    return [float(x) for x in np.concatenate([g[:3, 0], g[:3, 1], g[:3, 2], g[:3, 3]])]


def export(path, skeleton, meshes, actions):
    """Write the GLB. Which clips are her speech rides on the skeleton as the custom property `speech`, which
    import_rosalyn.gd reads; each mouth shape as `mouths`: shape -> the jaw's opening in degrees, as `jaw`, and
    each pivot's piece -> its move into the shape."""
    R.shelve(skeleton, actions)
    skeleton["speech"] = list(clips.SPEECH)
    skeleton["mouths"] = {shape: dict({part: gltf(head_move(m)) for part, m in moves.items()}, jaw=mouth.SHAPES[shape]["jaw"])
                          for shape, moves in mouth.poses().items()}
    bl.export_glb(path, [skeleton] + meshes, active=skeleton, export_animations=True, export_animation_mode="NLA_TRACKS",
                  export_force_sampling=True, export_optimize_animation_size=False, export_reset_pose_bones=True,
                  export_skins=True, export_tangents=True, export_vertex_color="NONE", export_extras=True)


def brows(path):
    """Paint her brow for the game to lay over her face wherever the brow's bone has carried it, and write beside
    it the size it covers: across, deep and high, in metres."""
    import json
    bl.save_image(path, head.brow()[::-1], alpha=True)
    with open(os.path.splitext(path)[0] + ".json", "w", newline="\n") as f:
        json.dump(dict(size=[float(x) for x in head.BROW_BOX]), f)
        f.write("\n")
    print("PAINT", path)


def main():
    t0 = time.time()
    bl.reset_scene()
    detail = float(opt("--detail", "1.0"))
    names = opt("--only").split(",") if opt("--only") else list(SPECS) + ["mouth"]
    views = [float(a) for a in opt("--views", "0,-40,-90,180").split(",")]
    zooms = opt("--zoom", "full").split(",")
    pieces = [P.sculpt(name, SPECS[name], detail) for name in names if name in SPECS]
    for pc in pieces:
        pc["q"] = P.outward(pc["v"], pc["q"], pc["n"])
    pieces += small_parts()
    count = P.triangles(pieces)
    trial = mouth_parts(detail) if "mouth" in names else []
    print("SCULPTED tris=%d of %d, and %d for the mouth trial  t=%.1fs" % (count, int(BUDGET * detail * detail),
                                                                          P.triangles(trial), time.time() - t0))
    pieces += trial
    if not (opt("--out") or opt("--shots")):
        if opt("--clay") and opt("--mouth") == "all":
            mouth_sheet(opt("--clay"), *clay_figure(pieces), light=CLAY_LIGHT)
        elif opt("--clay"):
            shown = staged(pieces)
            clay = build.clay_objects(shown, "--wire" in argv, black=("eye",))
            for ob, (pc, right) in zip(clay, sides(shown)):
                if pc["mat"] == "lip":
                    lip_clay(ob)
            if opt("--pose") or opt("--clip") or opt("--jaw"):
                skeleton = rig.armature("rig")
                for ob, (pc, right) in zip(clay, sides(shown)):
                    rig.weigh(ob, "head" if pc["mat"] == "lip" else pc.get("bone"), right)
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
    carved = carve([pc for pc in pieces if pc["mat"] in CARVED])
    figure = [ob for ob, _ in carved]
    for mat, look in zip(baked, painted):
        figure.append(build.assemble(NAME.capitalize() + mat.capitalize(), pieces, [mat], [look]))
        rig.weigh(figure[-1], ridden(pieces, mat))
    skeleton = rig.armature("rig")
    loose = {ob for ob, skinned in carved if not skinned}
    for ob in figure:
        if ob not in loose:
            R.attach(ob, skeleton)
        print("MESH %s: %d triangles, materials %s" % (ob.name, sum(len(f.vertices) - 2 for f in ob.data.polygons),
                                                       ", ".join(m.name for m in ob.data.materials)))
    actions = {name: pose.record(skeleton, name, clip, frames) for name, (clip, frames) in clips.CLIPS.items()}
    R.use(skeleton, None)
    pose.strike(skeleton, {})
    if opt("--shots"):
        for ob in figure:
            ob.hide_render = ob.name.startswith((NAME.capitalize() + "FaceInlaid", NAME.capitalize() + "Lip"))
        grey = bl.clay("clay", base=(0.62, 0.60, 0.58), rough=0.55, vertex_color=False)
        dark = bl.clay("clay_eye", base=(0.01, 0.01, 0.01), rough=0.05, vertex_color=False)
        wears = [list(ob.data.materials) for ob in figure]
        bare = [[dark if m.name == "eye" else grey for m in slots] for slots in wears[:len(carved)]] + [[c] for c in clay]
        for zoom, angles in (("full", views), ("upper", views), ("head", views), ("face", [0, -40, -90, 40]),
                             ("hand", [0, -90, 180, 90])):
            if opt("--zoom") and zoom not in zooms:
                continue
            for kind, mats, light in (("clay", bare, CLAY_LIGHT), ("painted", wears, 1.0)):
                for ob, slots in zip(figure, mats):
                    for k, m in enumerate(slots):
                        ob.data.materials[k] = m
                turnaround(os.path.join(opt("--shots"), "%s_%s.png" % (kind, zoom)), angles, zoom, light)
        if not opt("--zoom") or "mouth" in zooms:
            mouth_sheet(os.path.join(opt("--shots"), "sheet_mouths.png"), skeleton, figure)
        for name in () if opt("--zoom") else POSED:
            pose.strike(skeleton, clips.POSES[name])
            for zoom in POSED[name]:
                turnaround(os.path.join(opt("--shots"), "pose_%s_%s.png" % (name, zoom)),
                           CLASP_VIEWS if zoom == "clasp" else views, zoom)
        pose.strike(skeleton, {})
        for name in () if opt("--zoom") else ("Idle", *clips.SPEECH):
            for zoom in SHEETS:
                contact_sheet(os.path.join(opt("--shots"), "sheet_%s_%s.png" % (name.lower(), zoom)), skeleton,
                              actions[name], zoom)
    if opt("--out"):
        export(opt("--out"), skeleton, figure, actions.values())
        build.face_paint(FACE_PAINT, head, FACE_GRAIN)
        build.face_paint(INLAID_PAINT, head.INLAID, FACE_GRAIN)
        brows(BROW_PAINT)
    print("DONE t=%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()

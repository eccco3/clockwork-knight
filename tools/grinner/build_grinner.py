"""Builds a kind of grinner: sculpts every piece, bakes its textures from the sculpt, rigs and animates it, and
exports GLB with detail levels and clips. The kinds share the sculpt; each has its own rig, clips and model.

  blender --background --python build_grinner.py -- [--kind scuttler] [--out grinner.glb] [--shots dir]
          [--size 2048] [--clay a.png] [--pose crouch] [--clip Pounce] [--only a,b] [--sub 2] [--wire]
          [--views 0,-40,-90,180] [--zoom full|head|face|hand|legs]

--kind names one of KINDS: the walking grinner unless given. --clay alone renders the bare game mesh, for
judging forms quickly; --pose puts it in one of the kind's poses first, and --clip makes the picture a contact
sheet of one of its clips.
--out and --shots run the whole build. Rest pose in Blender space: +X is the figure's left, -Y is forward, +Z up.
"""
import sys, os, time, tempfile
import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, bake, build, pieces as P
from sculpt.bl import argv, opt
from sculpt.pieces import under, either, on_left
from grinner import body, head, rig, pose, clips, scuttler
from grinner.keys import FPS

KINDS = {kind.name: kind for kind in (clips.GRINNER, scuttler.SCUTTLER)}
LODS = (40000, 20000, 10000, 5000)              # triangle ceilings, full detail first
MATS = {"skin": dict(grain=bake.pores), "cloth": dict(grain=bake.weave)}


def in_head(f):
    return lambda p: f(head.to_head(p))


HEAD_FLIP = np.array([-1.0, -1.0, 1.0])


def wrap_head(sub):
    v, q, n, lat = head.wrap(sub)
    return head.from_head(v), q, n * HEAD_FLIP, lat


SKIN = dict(mat="skin", grain=0.07, pitch=0.0016, grain_tint=0.03)
SPECS = {
    "arm": dict(SKIN, boxes=body.arm_boxes, field=body.arm, detail=body.arm_detail, paint=body.arm_paint,
                seam=body.arm_seam, mirror=True, hidden=under(body.shirt, 0.003), pin=body.arm_pin, boost=1.15),
    "leg": dict(SKIN, boxes=body.leg_boxes, field=body.leg, detail=body.leg_detail, paint=body.leg_paint,
                seam=body.leg_seam, mirror=True, hidden=under(body.shorts, 0.004), boost=0.9),
    "shirt": dict(mat="cloth", boxes=body.shirt_boxes, field=body.shirt, detail=body.shirt_detail, paint=body.shirt_paint,
                  seam=body.shirt_seam, mirror=False, grain=0.22, pitch=0.0020, grain_tint=0.10, boost=1.0,
                  hidden=either(under(body.shorts, 0.004), under(on_left(body.arm), 0.002),
                                under(in_head(head.field), 0.002))),
    "shorts": dict(mat="cloth", boxes=body.shorts_boxes, field=body.shorts, detail=body.shorts_detail,
                   paint=body.shorts_paint, seam=body.shorts_seam, mirror=False, grain=0.28, pitch=0.0024,
                   grain_tint=0.12, boost=0.9, hidden=either(under(on_left(body.leg), 0.002), under(body.shirt, 0.003))),
    "head": dict(SKIN, mesh=wrap_head, field=in_head(head.field), detail=in_head(head.detail), paint=in_head(head.paint),
                 seam=head.seam, mirror=False, hidden=under(body.shirt, 0.003), boost=1.55, favour=in_head(head.face)),
}


def small_parts():
    """Teeth, collar and eyeballs: made by formula, painted through a chart instead of from a sculpt."""
    v, q, n, chart = head.teeth()
    out = [dict(name="teeth", mat="skin", v=head.from_head(v), q=q, n=n * HEAD_FLIP, chart=chart, paint=head.teeth_paint,
                mirror=False, size=head.CHART, boost=3.0)]
    v, q, n, chart = body.collar()
    out.append(dict(name="collar", mat="cloth", v=v, q=q, n=n, chart=chart, paint=body.collar_paint, mirror=False,
                    size=(0.29, 0.05), boost=1.0, grain=0.22, pitch=0.0020, grain_tint=0.10))
    v, q, n, chart = head.eyeball()
    out.append(dict(name="eye", mat="skin", v=head.from_head(v + head.EYE), q=q, n=n * HEAD_FLIP, chart=chart,
                    paint=head.eye_paint, mirror=True, size=(0.0284, 0.0284), boost=1.0))
    return out


ZOOMS = {"full": ((0, 0.02, 0.63), 1.36, (640, 900)), "upper": ((0, 0.0, 1.00), 0.72, (720, 720)),
         "head": ((0, -0.03, 1.135), 0.34, (720, 720)), "face": ((0, -0.03, 1.11), 0.17, (720, 720)),
         "hand": ((0.42, -0.15, 0.36), 0.26, (720, 720)), "legs": ((0, 0.06, 0.30), 0.70, (720, 720)),
         "foot": ((0.09, -0.005, 0.06), 0.30, (720, 720)), "pose": ((0, 0, 0.66), 1.70, (800, 800)),
         "arms": ((0, -0.05, 0.95), 1.30, (800, 800)), "walk": ((0, 0, 0.62), 1.34, (480, 600)),
         "leap": ((0, -0.15, 0.86), 2.05, (640, 640)), "strike": ((0, -0.10, 0.66), 1.90, (600, 520)),
         "fall": ((0, 0.65, 0.66), 2.60, (720, 480)),
         "prowl": ((0, 0, 0.36), 1.50, (640, 480)), "gallop": ((0, 0, 0.40), 1.90, (640, 440)),
         "spring": ((0, -0.25, 0.62), 2.50, (720, 520)), "sprawl": ((0, 0.25, 0.36), 2.10, (720, 440)),
         "maw": ((0, -0.42, 0.50), 0.34, (720, 720))}
POSED = {"grinner": {"crouch": ("pose", "legs"), "stride": ("pose", "legs"), "kick": ("pose", "legs"),
                     "reach": ("pose", "arms"), "claw": ("hand",), "splay": ("hand",)},
         "scuttler": {"prowl": ("prowl",), "gape": ("prowl", "maw"), "stretch": ("gallop",), "gather": ("gallop",)}}
STANCE = {"grinner": ("stride", "pose"), "scuttler": ("prowl", "prowl")}            # each kind's detail levels, posed
SHEETS = {"grinner": {"Waddle": (12, (-90, -25), "walk"), "Idle": (12, (-25,), "walk"),     # steps through the clip,
                      "Pounce": (16, (-90, -25), "leap"), "Swipe": (12, (-25, -90), "strike"),  # the views of each,
                      "Flinch": (8, (-25, -90), "strike"), "Death": (16, (-90, -25), "fall")},   # and the zoom
          "scuttler": {"Run": (14, (-90, -25), "gallop"), "Idle": (12, (-25, -90), "prowl"),
                       "Pounce": (16, (-90, -25), "spring"), "Bite": (12, (-90, -25), "prowl"),
                       "Flinch": (8, (-90, -25), "prowl"), "Death": (16, (-90, -25), "sprawl")}}
ACROSS = 8
GROUND, GROUND_HIT = (0.20, 0.20, 0.21, 1.0), (0.60, 0.08, 0.06, 1.0)


def turnaround(path, views, zoom, samples=48, at=(0.0, 0.0)):
    (x, y, z), scale, res = ZOOMS[zoom]
    lights = bl.studio((z + 1.6, z + 0.3, z + 1.5), (250, 60, 200), key=(1.0, 0.95, 0.90))
    bl.turnaround(path, views, (x + at[0], y + at[1], z), scale, res, lights, samples)


def contact_sheet(path, skeleton, action, kind):
    """A clip at even steps from its start, left to right in rows of ACROSS, view after view. The camera keeps
    pace with the root, and the ground reddens while a hit window is open."""
    steps, views, zoom = SHEETS[kind.name][action.name]
    ground = bl.to_object("ground", [(x, y, z) for z in (-0.02, 0) for x, y in ((-4, -4), (4, -4), (4, 4), (-4, 4))],
                          [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    ground.data.materials.append(bl.clay("ground", base=GROUND[:3], rough=0.9, vertex_color=False))
    colour = ground.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"]
    pose.use(skeleton, action)
    end = action.frame_range[1]
    width, strips = ZOOMS[zoom][2][0], []
    for k in range(steps):
        frame = round(k * end / (steps if action.name in kind.loops else steps - 1))
        bpy.context.scene.frame_set(frame)
        colour.default_value = GROUND_HIT if kind.phase(action.name, frame / FPS) == "hit" else GROUND
        root = skeleton.pose.bones["root"].head
        ground.location = (root.x, root.y, 0.0)
        turnaround(path + ".step.png", views, zoom, 32, (root.x, root.y))
        strips.append(bl.read_image(path + ".step.png"))
    os.remove(path + ".step.png")
    blank = np.tile(strips[0][:1, :1], (strips[0].shape[0], width, 1))
    rows = [np.concatenate([s[:, v * width:(v + 1) * width] for s in strips[k:k + ACROSS]] + [blank] * (k + ACROSS - steps),
                           axis=1) for v in range(len(views)) for k in range(0, steps, ACROSS)]
    bpy.data.images.remove(bl.save_image(path, np.concatenate(rows[::-1], axis=0)))
    bpy.data.objects.remove(ground, do_unlink=True)
    pose.use(skeleton, None)
    print("SHEET", path)


def export(path, skeleton, meshes, actions, kind):
    """Write the GLB. The moves' marks and the looping clips' places in the gait ride on the skeleton as the custom
    properties `marks` and `gait`, which import_grinner.gd turns into markers on Godot's animations and its blend."""
    skeleton["marks"], skeleton["gait"] = kind.marks, kind.gait
    pose.shelve(skeleton, actions)
    bl.export_glb(path, [skeleton] + meshes, active=skeleton, export_animations=True, export_extras=True,
                  export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_optimize_animation_size=False,
                  export_reset_pose_bones=True, export_skins=True, export_tangents=True)


def main():
    t0 = time.time()
    bl.reset_scene()
    kind = KINDS[opt("--kind", "grinner")]
    names = opt("--only").split(",") if opt("--only") else list(SPECS)
    views = [float(a) for a in opt("--views", "0,-40,-90,180").split(",")]
    pieces = [P.sculpt(name, SPECS[name], int(opt("--sub", "1"))) for name in names]
    if "head" in names:
        pieces += small_parts()
    for pc in pieces:
        pc["q"] = P.outward(pc["v"], pc["q"], pc["n"])
    count = P.triangles(pieces)
    print("SCULPTED tris=%d  t=%.1fs" % (count, time.time() - t0))
    if not (opt("--out") or opt("--shots")):
        if opt("--clay"):
            build.clay_objects(pieces, "--wire" in argv, black=("eye",))
            if opt("--pose") or opt("--clip"):
                skeleton = rig.armature(kind.name, kind.jaw)
                for ob in [ob for ob in bpy.context.scene.objects if ob.type == "MESH"]:
                    rig.bind(ob, skeleton)
            if opt("--clip"):
                contact_sheet(opt("--clay"), skeleton, pose.record(skeleton, opt("--clip"), *kind.clips[opt("--clip")]), kind)
                return
            if opt("--pose"):
                pose.strike(skeleton, kind.poses[opt("--pose")])
            turnaround(opt("--clay"), views, opt("--zoom", "pose" if opt("--pose") else "full"), 40)
        return
    assert count <= LODS[0], "over the triangle budget"

    folder = opt("--textures") or tempfile.mkdtemp(prefix=kind.name + "_")
    painted, clay = build.textures(pieces, MATS, int(opt("--size", "2048")), folder, kind.name)
    levels = [build.assemble(kind.name + "_lod0", pieces, list(MATS), painted)]
    for level, ceiling in enumerate(LODS[1:], 1):
        levels.append(build.reduce(levels[0], "%s_lod%d" % (kind.name, level), ceiling))
    for ob, ceiling in zip(levels, LODS):
        n = len(ob.data.polygons)
        print("LOD %s: %d triangles (ceiling %d), %d materials" % (ob.name, n, ceiling, len(ob.data.materials)))
        assert n <= ceiling and all(len(p.vertices) == 3 for p in ob.data.polygons)

    skeleton = rig.armature(kind.name, kind.jaw)
    for ob in levels:
        rig.bind(ob, skeleton)
    actions = {name: pose.record(skeleton, name, clip, frames) for name, (clip, frames) in kind.clips.items()}
    pose.use(skeleton, None)
    pose.strike(skeleton, {})

    if opt("--shots"):
        shots = opt("--shots")
        for zoom, angles in (("full", views), ("head", views), ("hand", [0, -90, 180, 90]), ("legs", views)):
            if opt("--zoom") and zoom not in opt("--zoom").split(","):
                continue
            build.show(levels, levels[0], clay)
            turnaround(os.path.join(shots, "clay_%s.png" % zoom), angles, zoom)
            build.show(levels, levels[0], painted)
            turnaround(os.path.join(shots, "painted_%s.png" % zoom), angles, zoom)
        if not opt("--zoom"):
            for ob in levels[1:]:
                build.show(levels, ob, painted)
                turnaround(os.path.join(shots, "painted_%s.png" % ob.name[-4:]), [0, -40], "full")
            for name, zooms in POSED[kind.name].items():
                pose.strike(skeleton, kind.poses[name])
                for zoom in zooms:
                    for look, mats in (("clay", clay), ("painted", painted)):
                        build.show(levels, levels[0], mats)
                        turnaround(os.path.join(shots, "pose_%s_%s_%s.png" % (name, zoom, look)), views, zoom)
            stance, zoom = STANCE[kind.name]
            pose.strike(skeleton, kind.poses[stance])
            for ob in levels[1:]:
                build.show(levels, ob, painted)
                turnaround(os.path.join(shots, "pose_%s_%s.png" % (stance, ob.name[-4:])), [-40, 140], zoom)
            pose.strike(skeleton, {})
            build.show(levels, levels[0], painted)
            for name in SHEETS[kind.name]:
                contact_sheet(os.path.join(shots, "sheet_%s.png" % name.lower()), skeleton, actions[name], kind)
    if opt("--out"):
        for ob in levels:
            ob.hide_render = False
        export(opt("--out"), skeleton, levels, actions.values(), kind)
    print("DONE t=%.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()

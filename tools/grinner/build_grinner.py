"""Builds the grinner: sculpts every piece, bakes its textures from the sculpt, rigs and animates it, and exports
GLB with detail levels and clips.

  blender --background --python build_grinner.py -- [--out grinner.glb] [--shots dir] [--size 2048]
          [--clay a.png] [--pose crouch] [--only a,b] [--sub 2] [--wire] [--views 0,-40,-90,180]
          [--zoom full|head|face|hand|legs]

--clay alone renders the bare game mesh, for judging forms quickly; --pose puts it in one of clips.POSES first.
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
from grinner import body, head, rig, pose, clips

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
         "arms": ((0, -0.05, 0.95), 1.30, (800, 800)), "walk": ((0, 0, 0.62), 1.34, (480, 600))}
POSED = {"crouch": ("pose", "legs"), "stride": ("pose", "legs"), "kick": ("pose", "legs"), "reach": ("pose", "arms"),
         "claw": ("hand",), "splay": ("hand",)}
SHEETS = {"Waddle": (12, (-90, -25)), "Idle": (12, (-25,))}        # steps round the loop, and the views of each


def turnaround(path, views, zoom, samples=48, at=(0.0, 0.0)):
    (x, y, z), scale, res = ZOOMS[zoom]
    lights = bl.studio((z + 1.6, z + 0.3, z + 1.5), (250, 60, 200), key=(1.0, 0.95, 0.90))
    bl.turnaround(path, views, (x + at[0], y + at[1], z), scale, res, lights, samples)


def contact_sheet(path, skeleton, action, steps, views):
    """A clip at even steps round its loop, left to right, with a row per view. The camera keeps pace with the root."""
    ground = bl.to_object("ground", [(x, y, z) for z in (-0.02, 0) for x, y in ((-4, -4), (4, -4), (4, 4), (-4, 4))],
                          [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    ground.data.materials.append(bl.clay("ground", base=(0.20, 0.20, 0.21), rough=0.9, vertex_color=False))
    pose.use(skeleton, action)
    width, strips = ZOOMS["walk"][2][0], []
    for k in range(steps):
        bpy.context.scene.frame_set(round(k * action.frame_range[1] / steps))
        root = skeleton.pose.bones["root"].head
        turnaround(path + ".step.png", views, "walk", 32, (root.x, root.y))
        strips.append(bl.read_image(path + ".step.png"))
    os.remove(path + ".step.png")
    rows = [np.concatenate([s[:, v * width:(v + 1) * width] for s in strips], axis=1) for v in range(len(views))]
    bpy.data.images.remove(bl.save_image(path, np.concatenate(rows[::-1], axis=0)))
    bpy.data.objects.remove(ground, do_unlink=True)
    pose.use(skeleton, None)
    print("SHEET", path)


def main():
    t0 = time.time()
    bl.reset_scene()
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
            if opt("--pose"):
                skeleton = rig.armature("grinner")
                for ob in [ob for ob in bpy.context.scene.objects if ob.type == "MESH"]:
                    rig.bind(ob, skeleton)
                pose.strike(skeleton, clips.POSES[opt("--pose")])
            turnaround(opt("--clay"), views, opt("--zoom", "pose" if opt("--pose") else "full"), 40)
        return
    assert count <= LODS[0], "over the triangle budget"

    folder = opt("--textures") or tempfile.mkdtemp(prefix="grinner_")
    painted, clay = build.textures(pieces, MATS, int(opt("--size", "2048")), folder, "grinner")
    levels = [build.assemble("grinner_lod0", pieces, list(MATS), painted)]
    for level, ceiling in enumerate(LODS[1:], 1):
        levels.append(build.reduce(levels[0], "grinner_lod%d" % level, ceiling))
    for ob, ceiling in zip(levels, LODS):
        n = len(ob.data.polygons)
        print("LOD %s: %d triangles (ceiling %d), %d materials" % (ob.name, n, ceiling, len(ob.data.materials)))
        assert n <= ceiling and all(len(p.vertices) == 3 for p in ob.data.polygons)

    skeleton = rig.armature("grinner")
    for ob in levels:
        rig.bind(ob, skeleton)
    actions = {name: pose.record(skeleton, name, clip, frames) for name, (clip, frames) in clips.CLIPS.items()}
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
            for name, zooms in POSED.items():
                pose.strike(skeleton, clips.POSES[name])
                for zoom in zooms:
                    for look, mats in (("clay", clay), ("painted", painted)):
                        build.show(levels, levels[0], mats)
                        turnaround(os.path.join(shots, "pose_%s_%s_%s.png" % (name, zoom, look)), views, zoom)
            pose.strike(skeleton, clips.POSES["stride"])
            for ob in levels[1:]:
                build.show(levels, ob, painted)
                turnaround(os.path.join(shots, "pose_stride_%s.png" % ob.name[-4:]), [-40, 140], "pose")
            pose.strike(skeleton, {})
            build.show(levels, levels[0], painted)
            for name, (steps, angles) in SHEETS.items():
                contact_sheet(os.path.join(shots, "sheet_%s.png" % name.lower()), skeleton, actions[name], steps, angles)
    if opt("--out"):
        for ob in levels:
            ob.hide_render = False
        pose.shelve(skeleton, actions.values())
        bl.export_glb(opt("--out"), [skeleton] + levels, active=skeleton, export_animations=True,
                      export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_optimize_animation_size=False,
                      export_reset_pose_bones=True, export_skins=True, export_tangents=True)
    print("DONE t=%.1fs" % (time.time() - t0))


main()

"""Builds the grinner: sculpts every piece, bakes its textures from the sculpt, exports GLB with detail levels.

  blender --background --python build_grinner.py -- [--out grinner.glb] [--shots dir] [--size 2048]
          [--clay a.png] [--only a,b] [--sub 2] [--wire] [--views 0,-40,-90,180] [--zoom full|head|face|hand|legs]

--clay alone renders the bare game mesh, for judging forms quickly. --out and --shots run the whole build.
Rest pose in Blender space: +X is the figure's left, -Y is forward, +Z up. Unrigged.
"""
import bpy, sys, os, math, time, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from knight import sdf as S, mesher, bl
from knight.sdf import V
from grinner import lattice, body, head, bake

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


MIRROR = np.array([-1.0, 1.0, 1.0])
LODS = (40000, 20000, 10000, 5000)              # triangle ceilings, full detail first
MATS = {"skin": dict(grain=bake.pores), "cloth": dict(grain=bake.weave)}


def under(field, depth):
    return lambda v: field(v) < -depth


def either(*tests):
    return lambda v: np.any([t(v) for t in tests], axis=0)


def on_left(field):
    return lambda v: field(S.mirror_x(v))


def in_head(f):
    return lambda p: f(head.to_head(p))


HEAD_RES = (32, 30, 44)
HEAD_FLIP = np.array([-1.0, -1.0, 1.0])


def head_seam(a, b, n=1):
    """One island, opened down the back of the skull."""
    def on(c):
        i, j, k = c[:, 0], c[:, 1], c[:, 2]
        return (i == HEAD_RES[0] * n // 2) & ((j == 0) | ((j <= HEAD_RES[1] * n // 2) & ((k == 0) | (k == HEAD_RES[2] * n))))
    return on(a) & on(b)


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
    "head": dict(SKIN, field=in_head(head.field), detail=in_head(head.detail), paint=in_head(head.paint),
                 seam=head_seam, mirror=False, hidden=under(body.shirt, 0.003), boost=1.45, favour=in_head(head.face)),
}


# ============================================================== sculpting

def wrap_head(sub):
    dims = tuple(r * sub for r in HEAD_RES)
    v, q, n = mesher.wrap(head.field, V(0, -0.012, 0.050), V(0, -0.024, -0.050), (0.095, 0.125, 0.150), dims,
                          relax=14, density=head.density, snap=head.FEATURES)
    unit = mesher.cube_lattice(*dims)[0]
    lat = np.rint((unit + 1.0) / 2.0 * np.array(dims)).astype(np.int64)
    return head.from_head(v), q, n * HEAD_FLIP, lat


def sculpt(name, sub=1):
    spec = SPECS[name]
    t0 = time.time()
    if name == "head":
        v, q, n, lat = wrap_head(sub)
    else:
        pin = (lambda c: spec["pin"](c, sub)) if "pin" in spec else None
        v, q, n, lat = lattice.fit(spec["field"], spec["boxes"](sub), relax=40, pin=pin)
    total = len(q)
    v, q, n, lat = lattice.cull(v, q, spec["hidden"](v), (n, lat))
    a, b, c = v[q[:, 0]], v[q[:, 1]], v[q[:, 2]]
    flipped = int(((np.cross(b - a, c - a) * n[q[:, 0]]).sum(-1) < 0).sum())
    el = lattice.edges_of(q)
    el = S.length(v[el[:, 0]] - v[el[:, 1]])
    print("PIECE %-7s quads=%d of %d  flipped=%d  edge %.1f..%.1f mm (median %.1f)  t=%.1fs" % (
        name, len(q), total, flipped, el.min() * 1e3, el.max() * 1e3, np.median(el) * 1e3, time.time() - t0))
    return dict(spec, name=name, v=v, q=q, n=n, lat=lat, sub=sub)


def small_parts():
    """Teeth, collar and eyeballs: made by formula, painted through a chart instead of from a sculpt."""
    v, q, n, chart = head.teeth()
    out = [dict(name="teeth", mat="skin", v=head.from_head(v), q=q, n=n * HEAD_FLIP, chart=chart, paint=head.teeth_paint,
                mirror=False, size=(0.0048, 0.0125), boost=3.0)]
    v, q, n, chart = body.collar()
    out.append(dict(name="collar", mat="cloth", v=v, q=q, n=n, chart=chart, paint=body.collar_paint, mirror=False,
                    size=(0.29, 0.05), boost=1.0, grain=0.22, pitch=0.0020, grain_tint=0.10))
    v, q, n, chart = head.eyeball()
    out.append(dict(name="eye", mat="skin", v=head.from_head(v + head.EYE), q=q, n=n * HEAD_FLIP, chart=chart,
                    paint=head.eye_paint, mirror=True, size=(0.0284, 0.0284), boost=1.0))
    return out


def outward(v, faces, n):
    """Faces as tuples, each wound to face the way its normals point."""
    out = []
    for f in faces:
        f = tuple(int(i) for i in dict.fromkeys(f))
        a, b, c = v[f[0]], v[f[1]], v[f[2]]
        out.append(f if np.cross(b - a, c - a) @ n[list(f)].sum(0) >= 0 else f[::-1])
    return out


def sides(pc):
    """The piece's instances: (verts, faces, normals) for itself and, if paired, its mirror image."""
    yield pc["v"], pc["q"], pc["n"]
    if pc["mirror"]:
        yield pc["v"] * MIRROR, [f[::-1] for f in pc["q"]], pc["n"] * MIRROR


# ============================================================== texture coordinates

def edit(obs, fn):
    bpy.ops.object.select_all(action="DESELECT")
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    fn()
    bpy.ops.object.mode_set(mode="OBJECT")


def loop_uv(me, values=None):
    data = me.uv_layers[0].data
    if values is None:
        out = np.empty(len(data) * 2)
        data.foreach_get("uv", out)
        return out.reshape(-1, 2)
    data.foreach_set("uv", np.asarray(values, dtype=np.float64).ravel())


def area(p):
    """Total area of triangles (T,3,2) or (T,3,3)."""
    a, b = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
    if p.shape[-1] == 2:
        return 0.5 * np.abs(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]).sum()
    return 0.5 * S.length(np.cross(a, b)).sum()


def triangles(pc, uv):
    """Split the piece's faces along their shorter diagonals: vertices (T,3) and corner uv (T,3,2)."""
    tris, tuv, at = [], [], 0
    for f in pc["q"]:
        if len(f) == 4 and np.linalg.norm(pc["v"][f[1]] - pc["v"][f[3]]) < np.linalg.norm(pc["v"][f[0]] - pc["v"][f[2]]):
            split = ((0, 1, 3), (1, 2, 3))
        else:
            split = tuple((0, k, k + 1) for k in range(1, len(f) - 1))
        for t in split:
            tris.append([f[i] for i in t])
            tuv.append([uv[at + i] for i in t])
        at += len(f)
    return np.array(tris), np.array(tuv)


def unwrap(group):
    """Cut each sculpted piece along its seams, flatten it with the least stretch, and pack the group's islands
    into one square at an even texel density (times each piece's boost; a piece's `favour` mask enlarges part
    of it). Sets tris (T,3) and uv (T,3,2) on every piece and returns the density in texture units per metre."""
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    obs = []
    for pc in group:
        me = bpy.data.meshes.new("uv_" + pc["name"])
        me.from_pydata([tuple(x) for x in pc["v"]], [], pc["q"])
        me.uv_layers.new(name="UVMap")
        if "chart" not in pc:
            ev = np.empty(len(me.edges) * 2, dtype=np.int32)
            me.edges.foreach_get("vertices", ev)
            ev = ev.reshape(-1, 2)
            me.edges.foreach_set("use_seam", pc["seam"](pc["lat"][ev[:, 0]], pc["lat"][ev[:, 1]], pc["sub"]))
        ob = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(ob)
        obs.append(ob)
        if "chart" not in pc:
            favour = ob.vertex_groups.new(name="favour")
            weight = pc["favour"](pc["v"]) if "favour" in pc else np.zeros(len(pc["v"]))
            for index, w in enumerate(weight):
                favour.add([index], float(w), "REPLACE")

    def pack(merge):
        bpy.ops.uv.pack_islands(rotate=True, margin_method="ADD", margin=0.004, merge_overlap=merge)

    def flatten():
        bpy.ops.uv.unwrap(method="MINIMUM_STRETCH", iterations=40, use_weights=True, weight_group="favour",
                          weight_factor=3.0, margin=0.0)
        bpy.ops.uv.average_islands_scale()
    sculpted = [(ob, pc) for ob, pc in zip(obs, group) if "chart" not in pc]
    edit([ob for ob, pc in sculpted], flatten)
    for ob, pc in sculpted:
        loop_uv(ob.data, loop_uv(ob.data) * pc["boost"])
    edit([ob for ob, pc in sculpted], lambda: pack(False))
    ob, pc = sculpted[0]
    tris, tuv = triangles(pc, loop_uv(ob.data))
    density = math.sqrt(area(tuv) / area(pc["v"][tris])) / pc["boost"]
    for k, (ob, pc) in enumerate(zip(obs, group)):
        if "chart" in pc:                                       # set aside, every copy of the chart on the same spot
            li = np.empty(len(ob.data.loops), dtype=np.int32)
            ob.data.loops.foreach_get("vertex_index", li)
            loop_uv(ob.data, pc["chart"][li] * np.array(pc["size"]) * density * pc["boost"] + (2.0 + k, 0.0))
    edit(obs, lambda: pack(True))
    for ob, pc in zip(obs, group):
        pc["tris"], pc["uv"] = triangles(pc, loop_uv(ob.data))
        if "chart" not in pc:
            density = math.sqrt(area(pc["uv"]) / area(pc["v"][pc["tris"]])) / pc["boost"]
        lo, hi = pc["uv"].min((0, 1)), pc["uv"].max((0, 1))
        print("UV %-7s tris=%d  u %.3f..%.3f  v %.3f..%.3f" % (pc["name"], len(pc["tris"]), lo[0], hi[0], lo[1], hi[1]))
        if "favour" in pc:
            m = pc["favour"](pc["v"][pc["tris"]].mean(1)) > 0.5
            print("UV %-7s favoured part %.2f times the piece's texel density" % (pc["name"], math.sqrt(
                area(pc["uv"][m]) / area(pc["v"][pc["tris"][m]]) * area(pc["v"][pc["tris"]]) / area(pc["uv"]))))
        bpy.data.objects.remove(ob, do_unlink=True)
    return density


def mesh_of(name, v, tris, uv, n, slot=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(x) for x in v], [], [tuple(int(i) for i in t) for t in tris])
    me.uv_layers.new(name="UVMap")
    loop_uv(me, uv.reshape(-1, 2))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if slot is not None:
        me.polygons.foreach_set("material_index", slot)
    me.normals_split_custom_set_from_vertices([tuple(x) for x in n])
    return me


def tangents(pc):
    """The tangent frame the renderer will use for this piece's normal map."""
    me = mesh_of("tan", pc["v"], pc["tris"], pc["uv"], pc["n"])
    me.calc_tangents(uvmap="UVMap")
    tan, sign = np.empty(len(me.loops) * 3), np.empty(len(me.loops))
    me.loops.foreach_get("tangent", tan)
    me.loops.foreach_get("bitangent_sign", sign)
    pc["tan"], pc["sign"] = tan.reshape(-1, 3, 3), sign.reshape(-1, 3)
    bpy.data.meshes.remove(me)


def occluder(pieces):
    """Everything that can shade a surface point: the nearest of the broad sculpts."""
    solids = [(pc["field"], pc["v"].min(0) - 0.08, pc["v"].max(0) + 0.08, pc["mirror"]) for pc in pieces if "field" in pc]

    def f(p):
        d = np.full(len(p), 1.0)
        for field, lo, hi, paired in solids:
            x = S.mirror_x(p) if paired else p
            m = np.all((x > lo) & (x < hi), axis=1)
            if m.any():
                d[m] = np.minimum(d[m], field(x[m]))
        return d
    return f


# ============================================================== materials and meshes

def save_image(name, rgb, folder, colour):
    img = bpy.data.images.new(name, rgb.shape[1], rgb.shape[0], alpha=False)
    px = np.ones(rgb.shape[:2] + (4,), dtype=np.float32)
    px[..., :3] = rgb
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = os.path.join(os.path.abspath(folder), name + ".png")
    img.file_format = "PNG"
    img.save()
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def material(name, albedo, normal, orm, clay=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]

    def tex(img):
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        return node
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nm.uv_map = "UVMap"
    nt.links.new(tex(normal).outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if clay:
        bsdf.inputs["Base Color"].default_value = (0.60, 0.58, 0.56, 1)
        bsdf.inputs["Roughness"].default_value = 0.55
        return m
    nt.links.new(tex(albedo).outputs["Color"], bsdf.inputs["Base Color"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex(orm).outputs["Color"], sep.inputs["Color"])
    nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
    nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    group = bpy.data.node_groups.get("glTF Material Output")
    if group is None:                                           # the exporter reads occlusion from a group of this name
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    out = nt.nodes.new("ShaderNodeGroup")
    out.node_tree = group
    nt.links.new(sep.outputs["Red"], out.inputs["Occlusion"])
    return m


def assemble(pieces, mats):
    """Every piece and its mirror image as one mesh, a material slot per texture set."""
    v, tris, uv, n, slot, at = [], [], [], [], [], 0
    for index, mat in enumerate(MATS):
        for pc in pieces:
            if pc["mat"] != mat:
                continue
            for flip in ((False, True) if pc["mirror"] else (False,)):
                v.append(pc["v"] * (MIRROR if flip else 1.0))
                n.append(pc["n"] * (MIRROR if flip else 1.0))
                tris.append((pc["tris"][:, ::-1] if flip else pc["tris"]) + at)
                uv.append(pc["uv"][:, ::-1] if flip else pc["uv"])
                slot.append(np.full(len(pc["tris"]), index))
                at += len(pc["v"])
    me = mesh_of("grinner_lod0", np.concatenate(v), np.concatenate(tris), np.concatenate(uv), np.concatenate(n),
                 np.concatenate(slot))
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new("grinner_lod0", me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def reduce(base, level, ceiling):
    """A copy of the full mesh collapsed to at most `ceiling` triangles, shaded with the full mesh's normals."""
    ob = base.copy()
    ob.data = base.data.copy()
    ob.name = ob.data.name = "grinner_lod%d" % level
    bpy.context.scene.collection.objects.link(ob)
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    dec = ob.modifiers.new("collapse", "DECIMATE")
    dec.ratio = 0.985 * ceiling / len(base.data.polygons)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    nrm = ob.modifiers.new("normals", "DATA_TRANSFER")
    nrm.object = base
    nrm.use_loop_data = True
    nrm.data_types_loops = {"CUSTOM_NORMAL"}
    nrm.loop_mapping = "POLYINTERP_NEAREST"
    bpy.ops.object.modifier_apply(modifier=nrm.name)
    return ob


# ============================================================== pictures

ZOOMS = {"full": ((0, 0.02, 0.63), 1.36, (640, 900)), "upper": ((0, -0.05, 1.00), 0.72, (720, 720)),
         "head": ((0, -0.10, 1.125), 0.34, (720, 720)), "face": ((0, -0.10, 1.10), 0.17, (720, 720)),
         "hand": ((0.42, -0.19, 0.36), 0.26, (720, 720)), "legs": ((0, 0.06, 0.30), 0.70, (720, 720)),
         "foot": ((0.09, -0.03, 0.06), 0.30, (720, 720))}


def turnaround(path, views, zoom, samples=48):
    """One render per view (camera and lights orbit together), stitched side by side."""
    bl.setup_cycles(samples)
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    target, scale, res = ZOOMS[zoom]
    pivot = bpy.data.objects.new("turntable", None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.location = (target[0], target[1], 0)
    t0 = (0, 0, target[2])
    rig = [bl.light("key", (1.2, -3.0, target[2] + 1.6), 250, 2.0, (1.0, 0.95, 0.90), t0),
           bl.light("fill", (-2.5, -2.0, target[2] + 0.3), 60, 3.0, (0.8, 0.88, 1.0), t0),
           bl.light("rim", (0.5, 3.0, target[2] + 1.5), 200, 2.0, (1, 1, 1), t0),
           bl.camera_ortho((0, -6.0, target[2]), t0, scale, res)]
    for o in rig:
        o.parent = pivot
    tiles = []
    for i, yaw in enumerate(views):
        pivot.rotation_euler = (0, 0, math.radians(-yaw))
        tmp = path + ".%d.png" % i
        bl.render(tmp)
        img = bpy.data.images.load(tmp)
        tiles.append(np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4))
        bpy.data.images.remove(img)
        os.remove(tmp)
    sheet = np.concatenate(tiles, axis=1)
    out = bpy.data.images.new("sheet", sheet.shape[1], sheet.shape[0], alpha=False)
    out.pixels.foreach_set(sheet.ravel())
    out.filepath_raw = path
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(out)
    for o in rig + [pivot]:
        bpy.data.objects.remove(o, do_unlink=True)
    print("SHOT", path)


def clay_objects(pieces):
    grey = bl.clay("clay", base=(0.62, 0.60, 0.58), rough=0.55, vertex_color=False)
    black = bl.clay("clay_eye", base=(0.01, 0.01, 0.01), rough=0.05, vertex_color=False)
    wire = bl.clay("wire", base=(0.02, 0.02, 0.02), rough=0.8, vertex_color=False)
    for pc in pieces:
        for v, faces, n in sides(pc):
            ob = bl.to_object(pc["name"], v, faces, n)
            ob.data.materials.append(black if pc["name"] == "eye" else grey)
            if "--wire" in argv:
                w = bl.to_object(pc["name"] + "_wire", v, faces)
                w.data.materials.append(wire)
                mod = w.modifiers.new("wire", "WIREFRAME")
                mod.thickness, mod.use_even_offset = 0.0005, False


def show(obs, visible, mats):
    for ob in obs:
        ob.hide_render = ob is not visible
    for k, m in enumerate(mats):
        visible.data.materials[k] = m


# ============================================================== build

def main():
    t0 = time.time()
    bl.reset_scene()
    names = opt("--only").split(",") if opt("--only") else list(SPECS)
    views = [float(a) for a in opt("--views", "0,-40,-90,180").split(",")]
    pieces = [sculpt(name, int(opt("--sub", "1"))) for name in names]
    if "head" in names:
        pieces += small_parts()
    for pc in pieces:
        pc["q"] = outward(pc["v"], pc["q"], pc["n"])
    count = sum(sum(len(f) - 2 for f in pc["q"]) * (2 if pc["mirror"] else 1) for pc in pieces)
    print("SCULPTED tris=%d  t=%.1fs" % (count, time.time() - t0))
    if not (opt("--out") or opt("--shots")):
        if opt("--clay"):
            clay_objects(pieces)
            turnaround(opt("--clay"), views, opt("--zoom", "full"), 40)
        return
    assert count <= LODS[0], "over the triangle budget"

    size = int(opt("--size", "2048"))
    folder = opt("--textures") or tempfile.mkdtemp(prefix="grinner_")
    os.makedirs(folder, exist_ok=True)
    shade = occluder(pieces)
    painted, clay = [], []
    for mat, spec in MATS.items():
        group = [pc for pc in pieces if pc["mat"] == mat]
        density = unwrap(group)
        for pc in group:
            tangents(pc)
        print("UV %s: %.2f mm per texel  t=%.1fs" % (mat, 1e3 / (density * size), time.time() - t0))
        albedo, normal, orm = bake.bake(group, size, shade, spec["grain"], density)
        images = [save_image("%s_%s" % (mat, kind), img, folder, kind == "albedo")
                  for kind, img in (("albedo", albedo), ("normal", normal), ("orm", orm))]
        painted.append(material("grinner_" + mat, *images))
        clay.append(material("grinner_%s_clay" % mat, *images, clay=True))
        print("BAKE %s done  t=%.1fs" % (mat, time.time() - t0))

    levels = [assemble(pieces, painted)]
    for level, ceiling in enumerate(LODS[1:], 1):
        levels.append(reduce(levels[0], level, ceiling))
    for ob, ceiling in zip(levels, LODS):
        n = len(ob.data.polygons)
        print("LOD %s: %d triangles (ceiling %d), %d materials" % (ob.name, n, ceiling, len(ob.data.materials)))
        assert n <= ceiling and all(len(p.vertices) == 3 for p in ob.data.polygons)

    if opt("--shots"):
        shots = opt("--shots")
        for zoom, angles in (("full", views), ("head", views), ("hand", [0, -90, 180, 90]), ("legs", views)):
            if opt("--zoom") and zoom not in opt("--zoom").split(","):
                continue
            show(levels, levels[0], clay)
            turnaround(os.path.join(shots, "clay_%s.png" % zoom), angles, zoom)
            show(levels, levels[0], painted)
            turnaround(os.path.join(shots, "painted_%s.png" % zoom), angles, zoom)
        if not opt("--zoom"):
            for ob in levels[1:]:
                show(levels, ob, painted)
                turnaround(os.path.join(shots, "painted_%s.png" % ob.name[-4:]), [0, -40], "full")
    if opt("--out"):
        for ob in levels:
            ob.hide_render = False
        bpy.ops.object.select_all(action="DESELECT")
        for ob in levels:
            ob.select_set(True)
        path = os.path.abspath(opt("--out"))
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_animations=False,
                                  export_skins=False, export_normals=True, export_tangents=True, export_texcoords=True,
                                  export_materials="EXPORT", export_yup=True, export_apply=False)
        print("EXPORTED", path, "%.1f MB" % (os.path.getsize(path) / 1e6))
    print("DONE t=%.1fs" % (time.time() - t0))


main()

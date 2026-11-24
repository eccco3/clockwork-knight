"""Texture coordinates for pieces: seams, least-stretch flattening, packing, and the renderer's tangents."""
import bpy, math
import numpy as np
from . import sdf as S


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

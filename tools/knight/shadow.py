"""Shadow stand-in: a low-polygon copy of a skinned body that only shadow maps draw."""
import bpy, bmesh


def shadow_mesh(body, tris=4000, min_size=0.015, min_tris=12, name=None):
    """Copy of `body` (same vertex groups and armature modifier) cut to about `tris` triangles.
    Each loose part gets triangles in proportion to its area, so thin parts such as a blade keep
    their outline; parts smaller than `min_size` metres are dropped."""
    ob = body.copy()
    ob.data = body.data.copy()
    ob.name = ob.data.name = name or body.name + "Shadow"
    body.users_collection[0].objects.link(ob)
    me = ob.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    while me.color_attributes:
        me.color_attributes.remove(me.color_attributes[0])
    me.materials.clear()

    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()

    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    parts = []
    for p in bpy.context.selected_objects:
        if max(p.dimensions) < min_size:
            bpy.data.objects.remove(p)
        else:
            parts.append((p, sum(f.area for f in p.data.polygons)))
    total = sum(a for _, a in parts)
    for p, area in parts:
        want = max(min_tris, tris * area / total)
        if want < len(p.data.polygons):
            dec = p.modifiers.new("Decimate", "DECIMATE")
            dec.decimate_type = "COLLAPSE"
            dec.ratio = want / len(p.data.polygons)
            dec.use_collapse_triangulate = True
            p.modifiers.move(len(p.modifiers) - 1, 0)
            with bpy.context.temp_override(object=p, active_object=p):
                bpy.ops.object.modifier_apply(modifier=dec.name)

    ob = parts[0][0]
    bpy.ops.object.select_all(action="DESELECT")
    for p, _ in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()
    ob.name = ob.data.name = name or body.name + "Shadow"
    ob.data.polygons.foreach_set("use_smooth", [False] * len(ob.data.polygons))
    ob.data.update()
    return ob

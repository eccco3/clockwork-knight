"""Blender-side helpers: numpy mesh -> object, preview rendering."""
import bpy, bmesh
import numpy as np
from mathutils import Vector, Matrix


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30


def to_object(name, verts, quads, normals=None, colors=None, collection=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(int(i) for i in q) for q in quads])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    if colors is not None:
        attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        rgba = np.ones((len(verts), 4))
        rgba[:, :colors.shape[1]] = colors
        attr.data.foreach_set("color", rgba.ravel())
    if normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


def clay(name, base=(0.62, 0.42, 0.26), rough=0.45, vertex_color=True, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metallic
    if vertex_color:
        vc = m.node_tree.nodes.new("ShaderNodeVertexColor")
        vc.layer_name = "Col"
        mix = m.node_tree.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs[0].default_value = 1.0
        mix.inputs[1].default_value = (*base, 1)
        m.node_tree.links.new(vc.outputs["Color"], mix.inputs[2])
        m.node_tree.links.new(mix.outputs[0], b.inputs["Base Color"])
    else:
        b.inputs["Base Color"].default_value = (*base, 1)
    return m


def setup_cycles(samples=48):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices:
                    d.use = d.type == kind
                sc.cycles.device = "GPU"
                break
        except Exception:
            pass
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Filmic" if "Filmic" in [i.identifier for i in type(sc.view_settings).bl_rna.properties["view_transform"].enum_items] else "AgX"
    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.11, 0.12, 0.14, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    sc.world = world


def light(kind, loc, energy, size=1.0, color=(1, 1, 1), target=(0, 0, 0)):
    ld = bpy.data.lights.new(kind, "AREA")
    ld.energy, ld.size, ld.color = energy, size, color
    ob = bpy.data.objects.new(kind, ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def camera_ortho(loc, target, scale, res):
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = scale
    ob = bpy.data.objects.new("cam", cd)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc = bpy.context.scene
    sc.collection.objects.link(ob)
    sc.camera = ob
    sc.render.resolution_x, sc.render.resolution_y = res
    return ob


def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


def mesh_object(name, verts, faces, normals=None, colors=None, hard=False, thickness=0.0, sharp=38.0, bevel=0.0):
    """numpy mesh -> object. hard=True welds, fixes winding and marks creases; soft meshes keep
    their vertex order so per-vertex normals / colours can be attached."""
    import math
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, v)) for v in verts], [], [tuple(int(i) for i in f) for f in faces])
    if hard:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-5)
        if thickness:
            bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=thickness)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bevel:
            sharp_edges = [e for e in bm.edges if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(50)]
            if sharp_edges:
                bmesh.ops.bevel(bm, geom=sharp_edges, offset=bevel, segments=2, profile=0.6, affect="EDGES")
        bm.to_mesh(me)
        bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    rgba = np.ones((len(me.vertices), 4))
    if colors is not None and not hard:
        rgba[:, :colors.shape[1]] = colors
    attr.data.foreach_set("color", rgba.ravel())
    if hard:
        me.set_sharp_from_angle(angle=math.radians(sharp))
    elif normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(map(float, n)) for n in normals])
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob

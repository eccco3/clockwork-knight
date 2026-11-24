"""Blender-side helpers: script arguments, numpy mesh -> object, images, turnarounds, GLB export."""
import bpy, bmesh, math, os, sys
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default


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


def save_image(path, px, colour=True):
    """Write (H, W, 3 or 4) floats, bottom row first, as a PNG. Returns the image, named after the file."""
    path = os.path.abspath(path)
    img = bpy.data.images.new(os.path.splitext(os.path.basename(path))[0], px.shape[1], px.shape[0], alpha=False)
    rgba = np.ones(px.shape[:2] + (4,), dtype=np.float32)
    rgba[..., :px.shape[2]] = px
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    img.colorspace_settings.name = "sRGB" if colour else "Non-Color"
    return img


def read_image(path):
    """A picture file as (H, W, 4) floats, bottom row first."""
    img = bpy.data.images.load(os.path.abspath(path))
    px = np.array(img.pixels[:], dtype=np.float32).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return px


def studio(heights, energies, key=(1.0, 0.93, 0.85)):
    """Key, fill and rim lights for `turnaround`, at the given heights and energies."""
    return [("key", (1.2, -3.0, heights[0]), energies[0], 2.0, key),
            ("fill", (-2.5, -2.0, heights[1]), energies[1], 3.0, (0.8, 0.88, 1.0)),
            ("rim", (0.5, 3.0, heights[2]), energies[2], 2.0, (1, 1, 1))]


def turnaround(path, views, target, scale, res, lights, samples=48):
    """One render per view in degrees (camera and lights orbit `target` together), stitched side by side."""
    setup_cycles(samples)
    path = os.path.abspath(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pivot = bpy.data.objects.new("turntable", None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.location = (target[0], target[1], 0)
    t0 = (0, 0, target[2])
    rig = [light(name, loc, energy, size, colour, t0) for name, loc, energy, size, colour in lights]
    rig.append(camera_ortho((0, -6.0, target[2]), t0, scale, res))
    for o in rig:
        o.parent = pivot
    tiles = []
    for i, yaw in enumerate(views):
        pivot.rotation_euler = (0, 0, math.radians(-yaw))
        tmp = path + ".%d.png" % i
        render(tmp)
        tiles.append(read_image(tmp))
        os.remove(tmp)
    bpy.data.images.remove(save_image(path, np.concatenate(tiles, axis=1)))
    for o in rig + [pivot]:
        bpy.data.objects.remove(o, do_unlink=True)
    print("SHOT", path)


def export_glb(path, objects, active=None, **options):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.select_set(True)
    if active is not None:
        bpy.context.view_layer.objects.active = active
    path = os.path.abspath(path)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_normals=True,
                              export_texcoords=True, export_materials="EXPORT", export_yup=True, export_apply=False,
                              **options)
    print("EXPORTED", path, "%.1f MB" % (os.path.getsize(path) / 1e6))


def mesh_object(name, verts, faces, normals=None, colors=None, hard=False, thickness=0.0, sharp=38.0, bevel=0.0):
    """numpy mesh -> object. hard=True welds, fixes winding and marks creases; soft meshes keep
    their vertex order so per-vertex normals / colours can be attached."""
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

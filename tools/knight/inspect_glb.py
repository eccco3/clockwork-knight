"""blender --background --python inspect_glb.py -- file.glb [bones] [actions]"""
import bpy, sys
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
path, what = args[0], set(args[1:]) or {"bones", "actions"}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
print("FPS", bpy.context.scene.render.fps)
for ob in bpy.data.objects:
    print("OBJ", ob.type, ob.name, "parent=", ob.parent.name if ob.parent else None,
          "loc", tuple(round(v, 3) for v in ob.location), "rot", tuple(round(v, 3) for v in ob.rotation_euler),
          "scale", tuple(round(v, 3) for v in ob.scale),
          ("verts=%d" % len(ob.data.vertices)) if ob.type == "MESH" else "")
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
if "bones" in what:
    M = arm.matrix_world
    for b in arm.data.bones:
        h = M @ b.head_local
        t = M @ b.tail_local
        x = (M.to_3x3() @ b.matrix_local.to_3x3().col[0])
        z = (M.to_3x3() @ b.matrix_local.to_3x3().col[2])
        print("BONE %-16s par=%-14s head=(%7.4f %7.4f %7.4f) tail=(%7.4f %7.4f %7.4f) x=(%5.2f %5.2f %5.2f) z=(%5.2f %5.2f %5.2f)" % (
            b.name, b.parent.name if b.parent else "-", h.x, h.y, h.z, t.x, t.y, t.z, x.x, x.y, x.z, z.x, z.y, z.z))
if "actions" in what:
    for a in bpy.data.actions:
        print("ACTION %-28s frames %6.1f..%6.1f" % (a.name, a.frame_range[0], a.frame_range[1]))

"""blender --background --python preview_head.py -- out.png [res]
Turnaround of the face sculpt: front, three-quarter, profile."""
import bpy, sys, os, time, math
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from knight import sdf as S, mesher, head, bl
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
out = args[0]
res = int(args[1]) if len(args) > 1 else 56
mode = args[2] if len(args) > 2 else "turn"
t0 = time.time()
bl.reset_scene()
v, q, n = mesher.wrap(head.field, S.V(0, -0.012, -0.035), S.V(0, -0.012, 0.045), (0.08, 0.10, 0.12),
                      (res, int(res * 0.8), int(res * 1.25)), relax=14, density=head.density, snap=head.FEATURES)
col = head.paint(v)
print("head verts", len(v), "t=%.1fs" % (time.time() - t0))

wood = bl.clay("wood", base=(0.66, 0.44, 0.27), rough=0.38)
eye_m = bpy.data.materials.new("eye")
eye_m.use_nodes = True
nt = eye_m.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.06
tc = nt.nodes.new("ShaderNodeTexCoord")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Object"], sep.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "CONSTANT"
e = ramp.color_ramp.elements
e[0].position, e[0].color = 0.0, (0.90, 0.87, 0.80, 1)
e[1].position, e[1].color = math.cos(head.IRIS), (0.16, 0.10, 0.04, 1)
e.new(math.cos(head.IRIS) + 0.006).color = (0.36, 0.22, 0.08, 1)
e.new(math.cos(0.15)).color = (0.02, 0.015, 0.01, 1)
div = nt.nodes.new("ShaderNodeMath")
div.operation = "DIVIDE"
div.inputs[1].default_value = head.EYE_R
nt.links.new(sep.outputs["Y"], div.inputs[0])
nt.links.new(div.outputs[0], ramp.inputs[0])
nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])


def make(offset_x, yaw):
    ob = bl.to_object("head", v, q, n, col)
    ob.data.materials.append(wood)
    ob.rotation_euler = (0, 0, math.radians(yaw))
    ob.location = (offset_x, 0, 0)
    for sx in (1, -1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=head.EYE_R)
        e = bpy.context.active_object
        bpy.ops.object.shade_smooth()
        e.data.materials.append(eye_m)
        e.parent = ob
        e.location = (sx * head.EYE[0], head.EYE[1], head.EYE[2])
        # normalised object coords: y=1 at the pole facing forward
        e.scale = (1, 1, 1)
        tcn = e


if mode == "turn":
    for x, yaw in ((0.215, 0), (0.025, -38), (-0.205, -90)):
        make(x, yaw)
else:
    make(0.0, float(mode))

bl.setup_cycles(40)
bl.light("key", (0.35, 0.9, 0.45), 28, 0.5, (1.0, 0.93, 0.85))
bl.light("fill", (-0.7, 0.7, 0.0), 6, 1.0, (0.8, 0.88, 1.0))
bl.light("rim", (0.0, -0.8, 0.5), 20, 0.6)
if mode == "turn":
    bl.camera_ortho((0, 2.0, -0.030), (0, 0, -0.030), 0.66, (1848, 640))
else:
    bl.camera_ortho((0, 2.0, -0.032), (0, 0, -0.032), 0.165, (1100, 1100))
bl.render(out)
print("done t=%.1fs" % (time.time() - t0))

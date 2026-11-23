"""Print the reference mannequin's envelope (proportion guide only; its mesh is never used)."""
import bpy, sys
import numpy as np

path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=path)
ob = next(o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 1000)
v = np.array([tuple(ob.matrix_world @ p.co) for p in ob.data.vertices])
print("BBOX", v.min(0).round(3), v.max(0).round(3))
print("-- torso/legs: z slice | x-range (x>0 half) | y-range   [body only, |x|<0.22]")
for z in np.arange(0.0, 1.80, 0.05):
    m = (np.abs(v[:, 2] - z) < 0.02) & (np.abs(v[:, 0]) < 0.22)
    if m.sum() < 3:
        continue
    s = v[m]
    r = s[s[:, 0] > 0]
    print("z=%.2f  x %.3f..%.3f   y %.3f..%.3f  n=%d" % (z, r[:, 0].min(), r[:, 0].max(), s[:, 1].min(), s[:, 1].max(), m.sum()))
print("-- arm: x slice | y-range | z-range")
for x in np.arange(0.15, 0.92, 0.05):
    m = np.abs(v[:, 0] - x) < 0.015
    if m.sum() < 3:
        continue
    s = v[m]
    print("x=%.2f  y %.3f..%.3f   z %.3f..%.3f" % (x, s[:, 1].min(), s[:, 1].max(), s[:, 2].min(), s[:, 2].max()))

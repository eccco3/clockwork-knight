"""Great hall generator. Run:  blender --background --python tools/build_hall.py
Writes assets/models/hall.glb (+ .import with external material mapping) and
assets/models/hall_layout.json (colliders, candle/light/glass positions for the Godot side)."""
import bpy, sys, os, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hall_lib
from hall_lib import *

# material -> (tile size in metres, texture axis the grain follows)
for name, size, grain in [
    ('wood_beam', 0.9, 'v'), ('wood_floor', 1.5, 'u'), ('wood_panel', 1.6, 'v'), ('wood_dark', 1.0, 'v'),
    ('wood_red', 1.2, 'u'), ('wood_oak', 1.0, 'v'), ('wood_roof', 2.2, 'u'), ('wood_table', 1.0, 'v'),
    ('plaster', 2.4, 'v'), ('stone', 1.3, 'v'), ('stone_flag', 1.6, 'v'), ('mortar', 1.0, 'v'),
    ('iron', 0.5, 'v'), ('pewter', 0.5, 'v'), ('brass', 0.5, 'v'), ('wax', 0.3, 'v'), ('ceramic', 0.5, 'v'),
    ('bark', 0.7, 'v'), ('endgrain', 0.45, 'u'), ('ember', 0.5, 'v'), ('log_burn', 0.5, 'v'),
    ('leather', 0.5, 'v'), ('paper', 0.5, 'v'), ('velvet', 0.45, 'v'), ('linen', 0.5, 'v'), ('wool', 0.6, 'v'),
    ('rug', 1.0, 'v'), ('banner', 1.0, 'v'), ('tapestry', 1.0, 'v'), ('paint', 1.0, 'v'), ('hessian', 0.5, 'v'),
    ('clockface', 1.0, 'v'), ('shield', 1.0, 'v'), ('food', 0.3, 'v'), ('rope', 0.2, 'v'),
]:
    defmat(name, size, grain)

import hall_shell, hall_fireplace, hall_props

t0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
b = Builder(seed=11)
hall_shell.build_shell(b)
hall_fireplace.build_fireplace(b)
hall_props.build_props(b)
b.mark('spawn', (0, 0, 5.5))
objs = b.build_objects()
print("built %d mesh objects, %d tris in %.1fs" % (len(objs), b.tris, time.time() - t0))
by_group = {}
for (g, m), geo in b.geo.items():
    by_group[g] = by_group.get(g, 0) + sum(len(f) - 2 for f in geo.f)
print("tris by group:", by_group)

out = os.path.join(ROOT, 'assets', 'models', 'hall.glb')
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_yup=False, export_apply=False,
                          export_normals=True, export_tangents=False, export_vertex_color='ACTIVE',
                          export_all_vertex_colors=False, export_active_vertex_color_when_no_material=True,
                          export_materials='EXPORT', export_image_format='NONE', export_cameras=False,
                          export_lights=False, export_animations=False, export_skins=False, export_morph=False)

with open(os.path.join(ROOT, 'assets', 'models', 'hall_layout.json'), 'w') as f:
    json.dump({'colliders': b.colliders, 'marks': b.marks,
               'dims': {'hw': hall_shell.HW, 'hl': hall_shell.HL, 'eaves': hall_shell.EH, 'apex': hall_shell.APEX}}, f)

# .import with every material redirected to an external Godot material
imp = out + '.import'
mats = sorted({'hall_' + m for (_, m) in b.geo.keys()})
sub = ',\n'.join('"%s": {\n"use_external/enabled": true,\n"use_external/path": "res://materials/%s.tres"\n}' % (m, m) for m in mats)
uid_line = ''
if os.path.exists(imp):
    for line in open(imp):
        if line.startswith('uid='):
            uid_line = line
with open(imp, 'w', newline='\n') as f:
    f.write('[remap]\n\nimporter="scene"\nimporter_version=1\ntype="PackedScene"\n' + uid_line +
            'path="res://.godot/imported/hall.glb-PLACEHOLDER.scn"\n\n[deps]\n\nsource_file="res://assets/models/hall.glb"\n\n[params]\n\n'
            'nodes/root_type=""\nnodes/root_name=""\nnodes/apply_root_scale=true\nnodes/root_scale=1.0\n'
            'meshes/ensure_tangents=true\nmeshes/generate_lods=false\nmeshes/create_shadow_meshes=true\nmeshes/light_baking=2\n'
            'meshes/lightmap_texel_size=0.04\nmeshes/force_disable_compression=false\nskins/use_named_skins=true\n'
            'animation/import=false\nimport_script/path="res://builders/hall_import.gd"\n_subresources={\n"materials": {\n' + sub + '\n}\n}\n')
print("materials:", mats)
print("done in %.1fs" % (time.time() - t0))

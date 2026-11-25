"""Carved pieces: the parts of a figure that the game dresses by material name (scripts/looks.gd). They carry
its solid grain space in place of texture coordinates, so rings and brushing run through each as through its block.

A carved piece gives name, mat, v, q, mirror and grain, the frame whose z its fibres run along. A sculpted one
brings its normals as n. One made by formula has n None: it is welded, creased where its faces turn by more than
`sharp` degrees, and given `thickness` if it is a plate. tint (points -> colours) paints a sculpted piece.
"""
import bpy, zlib
import numpy as np
from . import bl, pieces as P
from .sdf import V


def carve(name, pieces, previews):
    """The pieces and their mirror images as one object of triangles called `name`, with a slot per material.
    Each is cut from its own block, whose place in the tree is the piece's `grain_offset` or else drawn from
    its name, so a piece keeps its grain whatever else is built.
    previews: material name -> how Blender shows it, as bl.clay's arguments."""
    objs = []
    for pc in pieces:
        rng = np.random.default_rng(zlib.crc32(pc["name"].encode()))
        for side, (v, faces, n) in enumerate(P.sides(pc)):
            ob = bl.mesh_object(pc["name"], v, faces, n, pc["tint"](v) if "tint" in pc else None, hard=n is None,
                                thickness=pc.get("thickness", 0.0), sharp=pc.get("sharp", 38.0))
            me = ob.data
            me.materials.append(bpy.data.materials.get(pc["mat"]) or bl.clay(pc["mat"], **previews[pc["mat"]]))
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            turn = rng.uniform(0, 2 * np.pi)
            offset = V(np.cos(turn), np.sin(turn), 0) * rng.uniform(0.05, 0.16) + V(0, 0, rng.uniform(-2, 2))
            g = pc["grain"].l(co.reshape(-1, 3) * (P.MIRROR if side else 1.0))
            bl.grain_layers(me, g + pc.get("grain_offset", offset), rng.uniform(0, 1))
            objs.append(ob)
    ob = bl.join(objs, name)
    cut = ob.modifiers.new("triangles", "TRIANGULATE")
    cut.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=cut.name)
    return ob

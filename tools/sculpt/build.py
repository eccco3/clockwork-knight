"""Turns sculpted pieces into Blender objects: clay previews, baked materials, the game mesh and its detail levels."""
import bpy, os, time
import numpy as np
from . import bl, uv, bake, pieces as P


def clay_objects(pieces, wire=False, black=()):
    """The bare pieces in grey clay; those named in `black` gloss black, and `wire` draws every edge."""
    grey = bl.clay("clay", base=(0.62, 0.60, 0.58), rough=0.55, vertex_color=False)
    dark = bl.clay("clay_eye", base=(0.01, 0.01, 0.01), rough=0.05, vertex_color=False)
    line = bl.clay("wire", base=(0.02, 0.02, 0.02), rough=0.8, vertex_color=False)
    for pc in pieces:
        for v, faces, n in P.sides(pc):
            ob = bl.to_object(pc["name"], v, faces, n)
            ob.data.materials.append(dark if pc["name"] in black else grey)
            if wire:
                w = bl.to_object(pc["name"] + "_wire", v, faces)
                w.data.materials.append(line)
                mod = w.modifiers.new("wire", "WIREFRAME")
                mod.thickness, mod.use_even_offset = 0.0005, False


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


def textures(pieces, mats, size, folder, prefix):
    """Unwrap and bake one texture set per material. mats: name -> dict(grain=the material's fine relief).
    Returns the painted materials and their clay twins, in the order of `mats`."""
    t0 = time.time()
    os.makedirs(folder, exist_ok=True)
    shade = P.occluder(pieces)
    painted, clay = [], []
    for mat, spec in mats.items():
        group = [pc for pc in pieces if pc["mat"] == mat]
        density = uv.unwrap(group)
        for pc in group:
            uv.tangents(pc)
        print("UV %s: %.2f mm per texel  t=%.1fs" % (mat, 1e3 / (density * size), time.time() - t0))
        maps = zip(("albedo", "normal", "orm"), bake.bake(group, size, shade, spec["grain"], density))
        images = [bl.save_image(os.path.join(folder, "%s_%s.png" % (mat, kind)), img, kind == "albedo") for kind, img in maps]
        painted.append(material("%s_%s" % (prefix, mat), *images))
        clay.append(material("%s_%s_clay" % (prefix, mat), *images, clay=True))
        print("BAKE %s done  t=%.1fs" % (mat, time.time() - t0))
    return painted, clay


def face_paint(path, head, origin, width=1024):
    """Bake a head's lacquer (head.paint over head.field, as far as head.PAINT_X, PAINT_Z0 and PAINT_Z1) to a
    PNG, unless the head's source has not changed since the last bake, and write beside it where the game's
    wood shader places it: on the head frame, whose origin lies at `origin` in the face's grain space."""
    import hashlib, json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(os.path.splitext(path)[0] + ".json", "w", newline="\n") as f:
        json.dump(dict(origin=list(origin),half_width=head.PAINT_X, bottom=head.PAINT_Z0, top=head.PAINT_Z1), f)
        f.write("\n")
    tag = hashlib.sha1(open(head.__file__, "rb").read() + str(width).encode()).hexdigest()
    stamp = path + ".stamp"
    if os.path.exists(path) and os.path.exists(stamp) and open(stamp).read() == tag:
        return
    rgb = bake.front_view(head.field, head.paint, head.PAINT_X, head.PAINT_Z0, head.PAINT_Z1, width)
    bl.save_image(path, rgb[::-1])
    open(stamp, "w").write(tag)
    print("PAINT", path, rgb.shape)


def assemble(name, pieces, order, mats):
    """Every piece and its mirror image as one mesh, with a slot per material name in `order`."""
    v, tris, tuv, n, slot, at = [], [], [], [], [], 0
    for index, mat in enumerate(order):
        for pc in pieces:
            if pc["mat"] != mat:
                continue
            for flip in ((False, True) if pc["mirror"] else (False,)):
                v.append(pc["v"] * (P.MIRROR if flip else 1.0))
                n.append(pc["n"] * (P.MIRROR if flip else 1.0))
                tris.append((pc["tris"][:, ::-1] if flip else pc["tris"]) + at)
                tuv.append(pc["uv"][:, ::-1] if flip else pc["uv"])
                slot.append(np.full(len(pc["tris"]), index))
                at += len(pc["v"])
    me = uv.mesh_of(name, np.concatenate(v), np.concatenate(tris), np.concatenate(tuv), np.concatenate(n),
                    np.concatenate(slot))
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def reduce(base, name, ceiling):
    """A copy of the full mesh collapsed to at most `ceiling` triangles, shaded with the full mesh's normals."""
    ob = base.copy()
    ob.data = base.data.copy()
    ob.name = ob.data.name = name
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


def show(obs, visible, mats):
    """Render only `visible`, wearing `mats`."""
    for ob in obs:
        ob.hide_render = ob is not visible
    for k, m in enumerate(mats):
        visible.data.materials[k] = m

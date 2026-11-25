"""The contact sheet of the minion's variants: a row to a flavour, every row led by the minion as he is now, each
tile a view from in front and one from behind over its number and the name that builds it."""
import bpy, os
import numpy as np
from sculpt import bl

VIEWS, TARGET, SCALE, SIZE = (-28, 152), (0, 0, 0.615), 1.34, (300, 580)
STRIP = 46                                     # the height of a tile's caption, in pixels
LIGHTS = bl.studio((2.2, 0.9, 2.1), (250, 60, 200))
FONT = "DejaVuSansMono.woff2"                  # of Blender's own, a face whose 1, l and I differ


def captions(texts, width):
    """Each text as a strip of picture `width` wide, bottom row first: all set as one page and rendered once."""
    bl.reset_scene()
    bl.setup_cycles(8)
    font = bpy.data.fonts.load(os.path.join(bpy.utils.system_resource("DATAFILES"), "fonts", FONT), check_existing=True)
    ink = bpy.data.materials.new("ink")
    ink.use_nodes = True
    glow = ink.node_tree.nodes.new("ShaderNodeEmission")
    glow.inputs["Strength"].default_value = 3.0
    ink.node_tree.links.new(glow.outputs[0], ink.node_tree.nodes["Material Output"].inputs["Surface"])
    lines = []
    for row, text in enumerate(texts):
        line = bpy.data.curves.new("caption", "FONT")
        line.body, line.font, line.size, line.align_x = text, font, 0.56, "CENTER"
        ob = bpy.data.objects.new("caption", line)
        ob.location = (0, len(texts) / 2 - row - 0.70, 0)
        ob.data.materials.append(ink)
        bpy.context.scene.collection.objects.link(ob)
        lines.append(ob)
    bpy.context.view_layer.update()
    for ob in lines:                           # a line too long for the strip is set smaller
        ob.data.size *= min(1.0, 0.96 * width / STRIP / max(ob.dimensions.x, 1e-6))
    high = STRIP * len(texts)
    bl.camera_ortho((0, 0, 5), (0, 0, 0), max(high, width) / STRIP, (width, high))
    path = os.path.join(bpy.app.tempdir, "captions.png")
    bl.render(path)
    page = bl.read_image(path)
    return [page[high - STRIP * (row + 1):high - STRIP * row] for row in range(len(texts))]


def tile(path):
    """A picture of whatever the scene holds, from in front and from behind. Returns it, bottom row first."""
    bl.turnaround(path, VIEWS, TARGET, SCALE, SIZE, LIGHTS, 40)
    return bl.read_image(path)


def sheet(path, rows, title):
    """Save the sheet: `rows` of (caption, picture) tiles, the first row uppermost, under a line of `title`."""
    wide = max(len(row) for row in rows)
    strips = iter(captions([caption for row in rows for caption, _ in row], rows[0][0][1].shape[1]))
    bands = []
    for row in rows:
        tiles = [np.concatenate([next(strips), picture]) for _, picture in row]
        tiles += [np.zeros_like(tiles[0])] * (wide - len(tiles))
        bands.append(np.concatenate(tiles, axis=1))
    bands.insert(0, captions([title], bands[0].shape[1])[0])
    bpy.data.images.remove(bl.save_image(path, np.concatenate(bands[::-1])))
    print("SHEET", os.path.abspath(path))

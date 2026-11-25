"""Builds the minion: makes every piece, carves them into one mesh with detail levels and a shadow stand-in,
and exports GLB.

  blender --background --python build_minion.py -- [--out minion.glb] [--works flavour:seed] [--shots dir]
          [--views 0,-40,-90,180] [--zoom figure,upper,chest,back,head,full] [--looks clay,painted,levels]
          [--only chest,head]
  blender --background --python build_minion.py -- --sheet dir [--of flavour:seed,...]

--works builds a variant with his clockwork showing (tools/minion/variants.py) in place of the minion as he is.
--shots renders turnarounds in clay and in Blender's stand-ins for his materials: the full mesh at each zoom, then
every detail level and the shadow stand-in; --looks picks which. A view is a yaw in degrees, or yaw/pitch to look
down on him. The zoom "full" frames him as the knight's preview frames her, so the two sheets show their sizes side
by side. --only keeps the pieces whose names start so. --sheet renders the contact sheet of the variants beside
him as he is, every one numbered and named as --works takes it; --of renders only those.
Rest pose in Blender space: +X is his left, -Y is forward, +Z up. Unrigged.

His materials carry the game's solid grain space instead of textures, and the game dresses them by name
(scripts/minion.gd). tools/minion/import_minion.gd makes the levels and the stand-in work in Godot.
"""
import bpy, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, build, carve, pieces as P
from sculpt.bl import opt
from knight import shadow
from minion import body, spear, variants, sheet

NAME = "minion"
LEVELS = ((12000, 0.0), (6000, 0.012), (3000, 0.025))   # each detail level's triangle ceiling, and the smallest piece it keeps, in metres across
SHADOW = 500                                    # the triangles his shadow stand-in aims for; each part keeps a few
PREVIEWS = {                                    # how Blender shows what the game dresses by name
    "wood": dict(base=(0.66, 0.47, 0.27), rough=0.40),
    "wood_dark": dict(base=(0.030, 0.024, 0.020), rough=0.22),
    "lacquer": dict(base=(0.42, 0.050, 0.040), rough=0.20),
    "navy": dict(base=(0.030, 0.040, 0.105), rough=0.22),
    "brass": dict(base=(0.86, 0.62, 0.26), rough=0.28, metallic=1.0),
    "steel": dict(base=(0.74, 0.76, 0.80), rough=0.22, metallic=1.0),
    "leather": dict(base=(0.16, 0.075, 0.04), rough=0.60),
}
ZOOMS = {"figure": ((0, 0, 0.61), 1.36, (640, 900)), "upper": ((0, 0, 0.93), 0.66, (720, 720)),
         "chest": ((0, 0, 0.86), 0.36, (720, 720)), "back": ((0, 0, 0.84), 0.40, (720, 720)),
         "head": ((0, -0.02, 1.105), 0.30, (720, 720)), "full": ((0, 0, 0.93), 2.02, (520, 1000))}


def turnaround(path, views, zoom):
    (x, y, z), scale, res = ZOOMS[zoom]
    bl.turnaround(path, views, (x, y, z), scale, res, bl.studio((z + 1.6, z + 0.3, z + 1.5), (250, 60, 200)), 40)


def level(name, pieces, ceiling, smallest):
    """The pieces at least `smallest` across as one mesh of at most `ceiling` triangles."""
    whole = carve.carve(name, [pc for pc in pieces if np.ptp(pc["v"], axis=0).max() >= smallest], PREVIEWS)
    if len(whole.data.polygons) <= ceiling:
        return whole
    whole.name = whole.data.name = name + "_whole"
    cut = build.reduce(whole, name, ceiling, creased=True)
    bpy.data.meshes.remove(whole.data)
    cut.data.validate()                         # collapsing a small closed piece can leave two faces on the same corners
    return cut


def figure_and_spear(works):
    """The minion's pieces, or those of the variant called `works`, and his spear's."""
    held = spear.parts()
    return (variants.parts(works, LEVELS[0][0] - P.triangles(held)) if works else body.parts()), held


def contact_sheet(folder, names):
    """Render the variants called `names` beside the minion as he is, tile by tile, a row to a flavour, and the
    sheet of them all. Each is numbered by its place in variants.SHEET."""
    rows, flavour = [], None
    for name in [None] + names:
        bl.reset_scene()
        whole = carve.carve(NAME, sum(figure_and_spear(name), []), PREVIEWS)
        number = variants.SHEET.index(name) + 1 if name in variants.SHEET else 0
        print("TILE %d %s: %d triangles" % (number, name or "as he is", len(whole.data.polygons)))
        assert len(whole.data.polygons) <= LEVELS[0][0], "over the triangle ceiling"
        picture = sheet.tile(os.path.join(folder, "%02d_%s.png" % (number, (name or "now").replace(":", "_"))))
        made = "%s   %s" % (number or "", name or "as he is now"), picture
        if name is None:
            current = made
        elif name.split(":")[0] != flavour:
            flavour = name.split(":")[0]
            rows.append([current, made])
        else:
            rows[-1].append(made)
    sheet.sheet(os.path.join(folder, "sheet.png"), rows, "Name picks by number or by flavour:seed.   Build one: "
                "blender --background --python tools/minion/build_minion.py -- --works flavour:seed")


def main():
    t0 = time.time()
    if opt("--sheet"):
        return contact_sheet(opt("--sheet"), opt("--of").split(",") if opt("--of") else variants.SHEET)
    bl.reset_scene()
    figure, held = figure_and_spear(opt("--works"))
    pieces = [pc for pc in figure + held if pc["name"].startswith(tuple(opt("--only", "").split(",")))]
    print("PIECES " + ", ".join("%s %d" % (pc["name"], P.triangles([pc])) for pc in pieces))
    levels = [level("%s_lod%d" % (NAME, n), pieces, *limits) for n, limits in enumerate(LEVELS)]
    for ob, (ceiling, smallest) in zip(levels, LEVELS):
        print("LOD %s: %d triangles (ceiling %d)" % (ob.name, len(ob.data.polygons), ceiling))
        assert not ob.data.validate(), "a piece collapsed flat"
    caster = shadow.shadow_mesh(levels[-1], SHADOW, min_tris=8, name=NAME + "_shadow")
    print("SHADOW %s: %d triangles" % (caster.name, len(caster.data.polygons)))
    top = max(pc["v"][:, 2].max() for pc in figure)
    print("BUILT pieces=%d  height %.3f m of the knight's %.3f  t=%.1fs" % (len(pieces), top, body.KNIGHT_HEIGHT, time.time() - t0))

    if opt("--shots"):
        shots = opt("--shots")
        views = [tuple(map(float, view.split("/"))) for view in opt("--views", "0,-40,-90,180").split(",")]
        painted = list(levels[0].data.materials)
        clay = [bl.clay("clay", base=(0.62, 0.60, 0.58), rough=0.55, vertex_color=False)] * len(painted)
        models = levels + [caster]
        caster.data.materials.append(clay[0])
        looks = opt("--looks", "clay,painted,levels").split(",")
        for zoom in opt("--zoom", "figure,upper,head,full").split(","):
            for look, mats in (("clay", clay), ("painted", painted)):
                if look in looks:
                    build.show(models, levels[0], mats)
                    turnaround(os.path.join(shots, "%s_%s.png" % (look, zoom)), views, zoom)
        if "levels" in looks:
            for ob in levels[1:]:
                build.show(models, ob, painted)
                turnaround(os.path.join(shots, "painted_%s.png" % ob.name[-4:]), [0, -40], "figure")
            build.show(models, caster, clay[:1])
            turnaround(os.path.join(shots, "clay_shadow.png"), [0, -40], "figure")
        caster.data.materials.clear()
        for ob in models:
            ob.hide_render = False
    if opt("--out"):
        bl.export_glb(opt("--out"), levels + [caster], export_animations=False, export_skins=False, export_tangents=False,
                      export_vertex_color="NONE")
    print("DONE t=%.1fs" % (time.time() - t0))


main()

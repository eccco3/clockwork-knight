"""Builds the head the face maker shows (dev/face_maker.gd), assets/models/head_<sex>.glb, whose face Godot
changes live (scripts/face_head.gd), and the sheets' look as a table, assets/models/filmic.png.

  blender --background --python tools/faces/build_head.py -- [--sex women]

The head is the face model's as the sex's sheets show it (rounds.render): a blend shape for each of a face's
numbers but its brows, and for each candidate feature the dev keeps (candidates.kept); its paint, how much
of it is hair and which way the strands run; and, in long hair, the fall it hangs for its first face, which
maker.py hangs again for each face.

A head is the sum of its numbers' shapes (model.py) but for its hair, which stands off it along its
normals, and for its normals. So each blend shape holds how fast the head and its normals change with its
number at the sex's first face, rest: the base face, each kept candidate at his favourite strength, about
which Randomize draws (rounds.drawn). A face drawn there is shaped to a fifth of a millimetre and shaded
to a degree or two, but in the creases between the lips. Blend shape k at weight w is the face whose number
k is rest's plus w. The brows are painted from their numbers live, as brows.py paints them.

Godot's frame: +X to her left, +Y up, +Z out of her face, the head levelled as the sheets level it and as
high as a standing figure's (build_faces.STAND): its "frame" holds where the head frame's origin and axes
lie in it. The node "head" carries in its extras what Godot and maker.py need: rest, the candidates' keys,
the fall's and the brows', paint's, hair's and studio's constants. Its vertices carry
where they lie on the mean head (UV: x and z; UV2: whether a brow may lie there, and whether it is eye),
the paint and how much of it is hair (CUSTOM0), and the strands' direction and where it lies across them
(CUSTOM1).
"""
import bpy, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl
from sculpt.bl import opt
from faces import brows, build_faces as B, candidates, glb, hair, rounds
from faces.model import normals

STEP = 0.01                                     # each number is moved this far either way to find the rates
MODELS = os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "models")
LUT_SIZE, LUT_STOPS = 65, (-14.0, 4.0)          # the table's cells a side, over log2 of the light
CAMERA = 6.0                                    # bl.turnaround's camera stands this far in front of its target
SKIN_ROUGH, EYE_ROUGH, CROP_ROUGH = 0.5, 0.15, 0.85   # as build_faces.portrait and Crop.coat give them


def gltf(p):
    """Points or directions of Blender's world in glTF's, and so Godot's."""
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


def placed(p):
    """Points of the levelled head frame where Godot shows them."""
    return gltf(B.STAND.w(p))


def turned(d):
    """Directions of the levelled head frame in Godot's."""
    return gltf(B.STAND.dir(d))


class Head:
    """The head of a sex as its sheets show it: its directions, a face's numbers but its brows and then each
    kept candidate (model.directions, then candidates' moves), and how its hair stands off it."""

    def __init__(self, model, sex):
        self.model, self.sex, self.style = model, sex, B.HAIRS[B.style(sex)]
        self.base = rounds.load(rounds.base_path(sex))["numbers"]
        self.kept = candidates.kept(rounds.answers_path(sex))
        self.keys = sorted(self.kept)
        moves = candidates.candidates(model, B.EYE, {k.split("/")[0] for k in self.keys}) if self.keys else {}
        self.directions = np.concatenate([model.directions] + [moves[k][3][None] for k in self.keys])
        self.rest = np.concatenate([self.base[:len(model.directions)], [self.kept[k][1] for k in self.keys]])
        self.stand, self.cover = self.style.scalp(model.mean)

    def at(self, v):
        """The head whose bare vertices are v, its hair standing off it, levelled; and its normals."""
        p = B.level(v + normals(v, self.model.quads) * self.stand[:, None])
        return p, normals(p, self.model.quads)

    def rates(self):
        """The head at rest and, for each direction, how fast it and its normals change there."""
        v = self.model.mean + np.tensordot(self.rest, self.directions, axes=1)
        p, n = self.at(v)
        dp, dn = np.zeros_like(self.directions), np.zeros_like(self.directions)
        for k, d in enumerate(self.directions):
            (pa, na), (pb, nb) = self.at(v + STEP * d), self.at(v - STEP * d)
            dp[k], dn[k] = (pa - pb) / (2 * STEP), (na - nb) / (2 * STEP)
        return p, n, dp, dn

    def paint(self):
        """The paint of every vertex but its brows, and how much of it is hair: the sheets' (rounds.render)."""
        candidates.lashed(B, self.model)
        return np.column_stack([B.paint(self.model.mean, self.model.eyes), self.cover])

    def strands(self):
        """The strands' direction at each vertex (levelled, in Godot's frame) and where it lies across them."""
        if not isinstance(self.style, B.Long):
            return np.zeros((len(self.model.mean), 4))
        across, along = self.style.strands(self.model.mean)
        return np.column_stack([turned(B.level(along)), across])

    def fall(self):
        """What maker.py hangs the fall with (hair.sheet), or None for short hair."""
        s = self.style
        return dict(thick=0.8 * s.thick, flare=s.flare, locks=s.locks, wave=s.wave) if isinstance(s, B.Long) else None

    def extras(self, world):
        long = isinstance(self.style, B.Long)
        target, scale = candidates.FACE
        lamps = [dict(name=name, at=gltf((x, y, z - target[2])).tolist(), watts=watts, size=size, colour=list(colour))
                 for name, (x, y, z), watts, size, colour in bl.studio(*B.LAMPS)]
        return dict(
            sex=self.sex, candidates=self.keys, fall=self.fall(),
            frame=dict(origin=placed(np.zeros(3)).tolist(), axes=turned(np.eye(3)).tolist()),
            rest=dict(numbers=list(self.base), strengths={k: self.kept[k][1] for k in self.keys}),
            brows=dict(curve=brows.CURVE, units=(brows.HIGH, brows.ARCHED, brows.SLANTED, brows.THICK, brows.LONG,
                                                 brows.APART), fade=brows.FADE, density=brows.DENSITY, rise=B.BROW_RISE),
            skin=dict(roughness=SKIN_ROUGH), eyes=dict(roughness=EYE_ROUGH),
            hair=dict(colour=B.HAIR, roughness=B.HAIR_GLOSS if long else CROP_ROUGH, streaked=long,
                      sheen=B.HAIR_SHEEN if long else 0.0, strands=B.STRANDS, clumps=B.CLUMPS),
            studio=dict(target=gltf(target).tolist(), scale=scale, tile=list(B.TILE), views=list(rounds.VIEWS),
                        camera=CAMERA, lamps=lamps, world=world, lut=dict(size=LUT_SIZE, stops=LUT_STOPS)))


def filmic(path):
    """Writes the sheets' view transform (bl.setup_cycles) as a table, LUT_SIZE cells a side over log2 of
    the light in red, green and blue from LUT_STOPS[0] to [1]: the slices from blue's lowest to its highest
    side by side, red across each and green down. Returns the light of the world about the sheets' faces."""
    bl.reset_scene()
    bl.setup_cycles()
    sc = bpy.context.scene
    sc.render.dither_intensity = 0.0
    sc.render.image_settings.file_format, sc.render.image_settings.color_mode = "PNG", "RGB"
    sc.render.image_settings.color_depth = "8"
    n = LUT_SIZE
    light = 2.0 ** np.linspace(*LUT_STOPS, n)
    blue, green, red = np.meshgrid(light, light, light, indexing="ij")
    table = np.stack([red, green, blue], -1).transpose(1, 0, 2, 3).reshape(n, n * n, 3)
    img = bpy.data.images.new("filmic", n * n, n, float_buffer=True)
    img.colorspace_settings.name = "Linear Rec.709"
    img.pixels.foreach_set(np.concatenate([table[::-1], np.ones((n, n * n, 1))], -1).astype(np.float32).ravel())
    img.save_render(path, scene=sc)
    bpy.data.images.remove(img)
    background = sc.world.node_tree.nodes["Background"].inputs
    return [c * background[1].default_value for c in background[0].default_value[:3]]


def main():
    t0 = time.time()
    sex = opt("--sex", "women")
    out = os.path.join(MODELS, "head_%s.glb" % sex)
    world = filmic(os.path.join(MODELS, "filmic.png"))
    head = Head(B.current(), sex)
    p, n, dp, dn = head.rates()
    print("RATES %d directions  t=%.1fs" % (len(dp), time.time() - t0), flush=True)
    mean, paint, strands = head.model.mean, head.paint(), head.strands()
    meshes = [dict(name="head", positions=placed(p), normals=turned(n), indices=glb.triangles(head.model.quads),
                   uvs=[mean[:, [0, 2]], np.column_stack([mean[:, 1] > 0.03, head.model.eyes]).astype(float),
                        paint[:, :2], paint[:, 2:], strands[:, :2], strands[:, 2:]],
                   targets=list(zip(turned(dp), turned(dn))),
                   target_names=rounds.labels(head.model)[:len(head.model.directions)] + head.keys,
                   extras=head.extras(world))]
    if head.fall():
        pts, quads, across = hair.sheet(p, **head.fall())
        meshes.append(dict(name="fall", positions=placed(pts), normals=turned(normals(pts, quads)),
                           indices=glb.triangles(quads), uvs=[np.column_stack([across, np.zeros(len(pts))])]))
    glb.write(out, meshes)
    print("HEAD %s: %d vertices, %d blend shapes, %.0f MB  t=%.1fs" % (out, len(p), len(dp), os.path.getsize(out) / 1e6,
                                                                     time.time() - t0))


if __name__ == "__main__":
    main()

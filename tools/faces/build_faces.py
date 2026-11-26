"""Builds the face model, tools/faces/model.npz, and shows faces drawn from it.

  blender --background --python build_faces.py -- [--fit] [--detail 1.0] [--sex women|men] [--grid a.png]
          [--hair straight] [--seed 1] [--spread 0.65] [--view 0] [--light 1.0] [--labels] [--pool] [--again]
          [--refine] [--best a.png] [--answers a.jsonl]

--fit learns the model from the heads tools/fetch_assets.ps1 downloads, as does a missing model (two
minutes); --detail scales its lattice, as it does a figure's. A model whose features are not the shapes
makehuman.py names now is given those first (twenty seconds). --grid renders 25 random faces, of --sex if
given (see sexes.py), each alone under the same camera and lamps, turned --view degrees, in the hair of
HAIRS --hair names, or else the one the sex's sets wear. --spread is the share of the people's standard
deviation the faces are drawn at. --labels renders the label set the dev labels the sexes on, --pool the
pools taste.py shows him, of --sex or both, each face from the front and turned, keeping those already
rendered, and their refinement rounds. --again renders, from the faces they hold, the sets of --sex, or of
both, that are in another look or hair than they should wear: the pool, its latest refinement round and the
next, and the best faces. A set in another look is rendered beside it first and then put in its place a
picture at a time, so that it is whole however the render ends. --refine renders the next refinement round
of --sex (taste.refine) from his answers, or from --answers, or finishes the one begun; the rating tool
runs it in the background, and once it is rendered shows it in place of the pool or the round before.
--best renders the 25 faces of --sex furthest along the taste learnt from his answers, or from --answers,
as a grid, best first, and writes their numbers beside it: a.json.

Every face is painted the same, with skin, lips, eyes and hair, so that only its shape and its brows
differ. The label set wears short hair, so that no face reads as a sex for its hair, and so do the men.
The women wear it long, so that each reads as a woman from the front: parted, close over the crown, fuller
down the sides and tucked behind the ears, streaked strand by strand and glossy along them, falling behind
the neck past the shoulders, and kept off the forehead, the temples, the cheekbones and the jaw, whose outline he judges. It is the same on every woman, laid on
her head and falling from it, so the taste learnt from it is still the face's. The faces he judges are
symmetric, so that his answers measure his taste and not chance; the grid's and the best faces are each
slightly lopsided, as people are, by weights a.json keeps.
"""
import bpy, json, sys, os, shutil, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl
from sculpt.bl import argv, opt
from sculpt.gen import Frame
from faces import brows, files, fit, ict, makehuman, taste
from faces.files import whole
from faces.model import Model, SPREAD, normals
from faces.sexes import SEXES, LABEL_SPREAD, Sex, label_set

MODEL = os.path.join(HERE, "model.npz")
SIDE = 5                                        # the grid shows SIDE * SIDE faces
STAND = Frame((0, 0, 1.63), (0, 0, 1), (-1, 0, 0))            # a head on a standing figure, facing the camera
TARGET, SCALE, TILE = (0, 0, 1.61), 0.30, (540, 600)
LAMPS = ((2.6, 1.2, 2.4), (135.0, 33.0, 90.0))                # the figures' preview lamps, dimmed for pale clay
VIEWS = (0.0, 35.0)                             # a rendered set shows each face from these
# The model's heads sit chin up: the ear canal lies about this far (degrees) below the line through the eye
# socket's floor that a level head keeps horizontal, which shows the front camera up the nostrils. Every
# face is tipped forward by it.
PITCH = 9.0
LOOK = 7                                        # the renders' look: a set rendered in another is rendered again
SKIN, HAIR = (0.60, 0.40, 0.30), (0.045, 0.032, 0.025)
LIPS, CHEEKS = (0.52, 0.24, 0.21), (0.66, 0.36, 0.29)
WHITE, IRIS, PUPIL = (0.80, 0.77, 0.72), (0.16, 0.10, 0.05), (0.01, 0.01, 0.01)
# The eyes look straight ahead from this centre (on +x); the iris and the pupil reach these angles off
# straight ahead (degrees).
EYE, IRIS_ANGLE, PUPIL_ANGLE = (0.032, 0.0565, 0.0005), 31.0, 11.0
# The lips: the line they meet on is this high on the midline; they reach out to the corners at x and up
# and down from the line by these heights in the middle, rounding off to the corners.
MOUTH_Z, MOUTH_X, UPPER, LOWER = -0.0695, 0.026, 0.013, 0.0135
CHEEK, CHEEK_R = (0.046, 0.06, -0.030), 0.024 # a faint flush, its centre on +x and its reach
# Short hair (Crop): the hairline's height above the eyes round the head, by the angle from the front
# (degrees) about an upright axis at y = AXIS_Y: high on the forehead, short sideburns, above the ears and
# down to the nape.
AXIS_Y = -0.01
HAIRLINE = ((0, 0.071), (30, 0.066), (50, 0.058), (65, 0.045), (74, 0.028), (80, -0.012), (86, -0.012),
            (92, 0.003), (115, 0.003), (128, -0.010), (145, -0.040), (165, -0.065), (180, -0.070))
EARS = (0.080, 0.006, -0.075)                  # no hair further out than x, below z and in front of y
CROP = (0.003, 0.008, 0.010)                   # hair thickness low on the head and at the crown, rising from this z
# Long hair (Long): its line, rounder at the temples than HAIRLINE, over the ears and down behind them,
# distances across the head measured as if it were unrolled from an upright cylinder of radius ROUND. Skin
# turns to hair over SOFT about the line, and the hair rises to its thickness over RISE above it; it thins
# to TUCK of that down at the ears, and its part runs back to y = PART_BACK.
LONG_LINE = ((0, 0.071), (30, 0.066), (50, 0.058), (65, 0.045), (74, 0.030), (82, 0.012), (90, 0.006),
             (115, 0.006), (125, -0.020), (140, -0.060), (180, -0.080))
ROUND, SOFT, RISE, TUCK, PART_BACK = 0.085, 0.007, 0.035, 0.35, -0.02
COMB, COMB_TO, RIDGES = (0.0, -0.01, 0.02), (1.0, -0.25, -1.0), 70   # combed; ridges to a turn
# Long hair is as thick as CROWN of its sides' thickness on top of the head, at TOP, thickening down to the
# full over DROP. Its streaks (streaked) are STRANDS[0] apart and STRANDS[1] deep, and clumps of them
# CLUMPS[0] across are lighter and darker by CLUMPS[1]; it is as glossy as HAIR_GLOSS, a roughness, with a
# sheen along the strands HAIR_SHEEN, an anisotropy. STRAND_ROUND turns a strand's angle about the comb's
# line into metres across, and its right side is SIDES on from its left.
CROWN, TOP, DROP = 0.4, 0.109, 0.06
STRANDS, CLUMPS, HAIR_GLOSS, HAIR_SHEEN = (0.0005, 0.0003), (0.004, 0.25), 0.45, 0.8
STRAND_ROUND, SIDES = 0.08, 1.0
# Long hair falls round the back from FALL_FROM degrees from the front, behind the ears, down to FALL_END
# (fall): from where the head is widest above FALL_WIDEST, sunk FALL_DIVE into the head above that, and
# spreading out below FALL_FLARE. It is reckoned FALL_STEP apart (metres down, degrees round), made of rings
# of FALL_RING points, ridged FALL_LOCKS times round a turn and waved FALL_WAVE apart.
FALL_FROM, FALL_END, FALL_WIDEST, FALL_INSET, FALL_DIVE, FALL_FLARE = 118.0, -0.26, -0.02, 0.0015, 0.008, -0.06
FALL_STEP, FALL_RING, FALL_LOCKS, FALL_WAVE = (0.002, 2.0), 128, 70, 0.045
BROW_RISE = 0.0006                              # the brows (brows.py) stand this far off the skin
# A face that is generated, not judged, is this many times as lopsided as the scanned heads.
LOPSIDED = 1.0


def learn(detail):
    t0 = time.time()
    model = fit.fit(ict.Heads(), detail)
    print("FITTED verts=%d quads=%d components=%d  t=%.1fs" % (len(model.mean), len(model.quads), len(model.components),
                                                              time.time() - t0))
    print("VARIANCE", " ".join("%.1f" % (100 * s) for s in model.share[:12]), "... percent")
    return model


def featured(model):
    """The model with MakeHuman's shapes for its features: saved."""
    t0 = time.time()
    model = Model(model.mean, model.components, model.share, model.quads, model.lat, model.asymmetries,
                  *makehuman.shapes(makehuman.Fit(model)), fitted=model.fitted, eyes=model.eyes)
    model.save(MODEL)
    print("FEATURED features=%d  t=%.1fs" % (len(model.names), time.time() - t0))
    return model


def ramp(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def ears(mean):
    """How much of each vertex of the mean head is ear, which no hair covers, from 0 to 1."""
    x, z = np.abs(mean[:, 0]), mean[:, 2]
    return ramp((x - EARS[0]) / 0.004) * ramp((EARS[1] - z) / 0.004) * (mean[:, 1] > EARS[2])


def beyond(mean, line):
    """How far each vertex of the mean head lies above a hairline like LONG_LINE, across the head and up it as
    though it were unrolled from an upright cylinder of radius ROUND about the axis; below it, negative."""
    x, y, z = np.abs(mean[:, 0]), mean[:, 1] - AXIS_Y, mean[:, 2]
    angle = np.degrees(np.arctan2(x, y))
    knots = np.array(line, float) * (np.radians(1.0) * ROUND, 1.0)
    start, step = knots[:-1], np.diff(knots, axis=0)
    p = np.stack([np.radians(angle) * ROUND, z], 1)[:, None]
    t = np.clip(((p - start) * step).sum(-1) / (step * step).sum(-1), 0.0, 1.0)
    far = np.linalg.norm(p - start - t[..., None] * step, axis=-1).min(1)
    return np.where(z > np.interp(angle, *zip(*line)), far, -far)


def combed(mean):
    """Hair parted at x = 0 and combed down either side toward a point below the ear, as each vertex of the
    mean head carries it: the strand's angle (radians) about the line from COMB toward COMB_TO (on +x), and
    its direction there, down from the part."""
    to = np.array(COMB_TO) / np.linalg.norm(COMB_TO)
    up = np.array((0.0, 0.0, 1.0)) - to[2] * to
    p = np.column_stack([np.abs(mean[:, 0]), mean[:, 1:]]) - COMB
    out = p / np.linalg.norm(p, axis=1, keepdims=True)
    along = to - (out @ to)[:, None] * out
    along = along / np.maximum(np.linalg.norm(along, axis=1, keepdims=True), 1e-9)
    along[:, 0] *= np.where(mean[:, 0] < 0.0, -1.0, 1.0)
    return np.arctan2(p @ np.cross(to, up), p @ up), along


def streaked(name, base, vertex_color=True):
    """Hair's material, `base` or the vertex colours times it: streaked across the strands that the `strand`
    attribute (metres across them) and the `tangent` attribute (their direction) of the mesh lay, finely in
    relief and in clumps lighter and darker, and glossy along them."""
    m = bl.clay(name, base=base, rough=HAIR_GLOSS, vertex_color=vertex_color)
    nodes, links = m.node_tree.nodes, m.node_tree.links
    surface = nodes["Principled BSDF"]
    strand, tangent = nodes.new("ShaderNodeAttribute"), nodes.new("ShaderNodeAttribute")
    strand.attribute_name, tangent.attribute_name = "strand", "tangent"

    def noise(scale, detail):
        n = nodes.new("ShaderNodeTexNoise")
        n.noise_dimensions = "1D"
        n.inputs["Scale"].default_value, n.inputs["Detail"].default_value = scale, detail
        links.new(strand.outputs["Fac"], n.inputs["W"])
        return n.outputs["Fac"]

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Distance"].default_value = STRANDS[1]
    links.new(noise(1.0 / STRANDS[0], 4.0), bump.inputs["Height"])
    links.new(bump.outputs["Normal"], surface.inputs["Normal"])
    shade = nodes.new("ShaderNodeMapRange")                 # a clump's brightness, about 1
    shade.inputs["To Min"].default_value, shade.inputs["To Max"].default_value = 1.0 - CLUMPS[1], 1.0 + CLUMPS[1]
    links.new(noise(1.0 / CLUMPS[0], 2.0), shade.inputs["Value"])
    colour = nodes.new("ShaderNodeVectorMath")
    colour.operation = "SCALE"
    if surface.inputs["Base Color"].is_linked:
        links.new(surface.inputs["Base Color"].links[0].from_socket, colour.inputs["Vector"])
    else:
        colour.inputs["Vector"].default_value = base
    links.new(shade.outputs["Result"], colour.inputs["Scale"])
    links.new(colour.outputs["Vector"], surface.inputs["Base Color"])
    surface.inputs["Anisotropic"].default_value = HAIR_SHEEN
    links.new(tangent.outputs["Vector"], surface.inputs["Tangent"])
    return m


def carry(ob, strand, along):
    """Gives the mesh of `ob` the attributes `streaked` reads, at each vertex."""
    ob.data.attributes.new("strand", "FLOAT", "POINT").data.foreach_set("value", np.asarray(strand, np.float32))
    ob.data.attributes.new("tangent", "FLOAT_VECTOR", "POINT").data.foreach_set(
        "vector", STAND.dir(along).astype(np.float32).ravel())


class Crop:
    """Short hair, as high as HAIRLINE and as thick as CROP."""

    def scalp(self, mean):
        """How far the hair stands off each vertex of the mean head (metres), and how much of the vertex is
        hair, from 0 to 1."""
        x, y, z = np.abs(mean[:, 0]), mean[:, 1] - AXIS_Y, mean[:, 2]
        above = z - np.interp(np.degrees(np.arctan2(x, y)), *zip(*HAIRLINE))
        thick = CROP[0] + (CROP[1] - CROP[0]) * ramp((z - CROP[2]) / 0.08)
        return thick * ramp(above / 0.020) * (1.0 - ears(mean)), ramp(above / 0.003 + 0.5) * (1.0 - ears(mean))

    def coat(self, ob, mean):
        """The material of the hair on the head `ob`, whose vertices lie at `mean` on the mean head."""
        return bl.clay("hair", base=(1.0, 1.0, 1.0), rough=0.85)

    def dress(self, v):
        """Puts in the scene the hair that stands clear of the head v (levelled): none."""


class Long:
    """Long hair, as high as LONG_LINE: parted `part` metres to her right of the middle, `thick` over the
    sides, CROWN of that on top and thinner where it is tucked behind the ears, combed into ridges `locks`
    deep and streaked along its strands (streaked), and falling from behind the ears down her back (fall),
    spread out by `flare` and waved `wave` deep."""

    def __init__(self, part=0.0, thick=0.011, tuck=TUCK, flare=0.018, locks=0.0003, wave=0.0):
        self.part, self.thick, self.tuck, self.flare, self.locks, self.wave = part, thick, tuck, flare, locks, wave

    def scalp(self, mean):
        z, side = mean[:, 2], mean[:, 0] - self.part
        inside = beyond(mean, LONG_LINE)
        part = ramp((mean[:, 1] - PART_BACK) / 0.03) * ramp(inside / 0.01)
        thick = self.thick * (self.tuck + (1.0 - self.tuck) * ramp((z - EARS[1]) / 0.07)) \
            * (CROWN + (1.0 - CROWN) * ramp((TOP - z) / DROP))
        thick = thick * (1.0 - 0.4 * part * np.exp(-(side / 0.008) ** 2)) \
            + self.locks * np.cos(RIDGES * combed(mean - (self.part, 0.0, 0.0))[0]) * ramp(np.abs(side) / 0.025)
        cover = ramp(inside / SOFT + 0.5) * (1.0 - 0.25 * part * np.exp(-(side / 0.001) ** 2))
        return thick * ramp(inside / RISE) * (1.0 - ears(mean)), cover * (1.0 - ears(mean))

    def strands(self, mean):
        """Where each vertex of the mean head lies across the strands (metres, either side apart by SIDES), and
        their direction there."""
        angle, along = combed(mean - (self.part, 0.0, 0.0))
        return STRAND_ROUND * angle + SIDES * (mean[:, 0] < self.part), along

    def coat(self, ob, mean):
        strand, along = self.strands(mean)
        carry(ob, strand, level(along))
        return streaked("hair", (1.0, 1.0, 1.0))

    def dress(self, v):
        fall(v, 0.8 * self.thick, self.flare, self.locks, self.wave)


# The hairs a face may wear, by name: the label set and the men wear "crop" (style), the women WOMEN.
HAIRS = dict(crop=Crop(), straight=Long(), side=Long(part=0.03),
             waves=Long(thick=0.019, tuck=0.5, flare=0.032, locks=0.0007, wave=0.004))
WOMEN = "straight"


def groom(mean, brow, hair="crop"):
    """The hair (HAIRS), the same on every face, and the brows its brow numbers shape, as each vertex of the
    model's lattice carries them: how far the hair stands off the skin (metres), and how much of the vertex
    is hair or brow, from 0 to 1."""
    stand, cover = HAIRS[hair].scalp(mean)
    brow = brows.brow(np.abs(mean[:, 0]), mean[:, 2], brow) * (mean[:, 1] > 0.03)
    return stand + BROW_RISE * brow, np.maximum(cover, brow)


def paint(at, eyes):
    """The colour every face carries at places on the mean head, the lattice's vertices or a figure's texels,
    before hair: skin, flushed cheeks, lips and, where `eyes` says they are, eyes."""
    x, y, z = np.abs(at[:, 0]), at[:, 1], at[:, 2]
    colour = np.tile(np.array(SKIN), (len(at), 1))
    flush = 0.5 * ramp(1.0 - np.linalg.norm(np.stack([x, y, z], 1) - CHEEK, axis=1) / CHEEK_R)
    colour += flush[:, None] * (np.array(CHEEKS) - SKIN)
    across = np.sqrt(np.clip(1.0 - (x / MOUTH_X) ** 2, 0.0, 1.0))
    height = np.where(z > MOUTH_Z, UPPER, LOWER) * across
    lip = ramp((1.0 - np.abs(z - MOUTH_Z) / np.maximum(height, 1e-6)) * 4.0) * (y > 0.06) * (x < MOUTH_X)
    colour += lip[:, None] * (np.array(LIPS) - colour)
    out = np.stack([x, y, z], 1) - EYE
    angle = np.degrees(np.arccos(np.clip(out[:, 1] / np.maximum(np.linalg.norm(out, axis=1), 1e-9), -1.0, 1.0)))
    ball = np.where(angle < PUPIL_ANGLE, 0, np.where(angle < IRIS_ANGLE, 1, 2))
    colour[eyes] = np.array((PUPIL, IRIS, WHITE))[ball[eyes]]
    return colour


def reach(v, top):
    """How far the head v (levelled) reaches out from the upright axis at y = AXIS_Y round the back, at each
    angle from FALL_FROM behind one ear to behind the other and each height from `top` down to FALL_END,
    FALL_STEP apart: the furthest any point does there, give or take a step round. Returns the angles, the
    heights and the reach (angles, heights)."""
    step, turn = FALL_STEP
    angles, heights = np.arange(FALL_FROM, 360.0 - FALL_FROM + 1e-9, turn), np.arange(top, FALL_END, -step)
    x, y, z = v[:, 0], v[:, 1] - AXIS_Y, v[:, 2]
    k = np.rint((np.degrees(np.arctan2(x, y)) % 360.0 - FALL_FROM) / turn).astype(int)
    j = np.minimum(((top - z) / step).astype(int), len(heights) - 1)
    out = np.zeros((len(angles), len(heights)))
    keep = (k >= 0) & (k < len(angles))
    np.maximum.at(out, (k[keep], j[keep]), np.hypot(x, y)[keep])
    wide = out.copy()
    wide[1:], wide[:-1] = np.maximum(wide[1:], out[:-1]), np.maximum(wide[:-1], out[1:])
    return angles, heights, wide


def fall(v, thick, flare, locks, wave):
    """Puts in the scene the long hair that hangs clear of the head v (levelled): a sheet round the back
    from behind one ear to behind the other, at each height FALL_INSET inside the furthest the head reaches
    there or above, so that it falls straight from where the head is widest, sunk into the head above that
    and rounded over the upper back; spreading out by `flare` toward the bottom of the picture and past it,
    `thick` down the middle of the back and rounded at its edges, ridged along its length `locks` deep and
    waved `wave` deep."""
    angles, z, out = reach(v, v[:, 2].max())
    widest = z[np.argmax(np.where(z > FALL_WIDEST, out, 0.0), axis=1)]
    out = np.maximum.accumulate(out, axis=1)
    for _ in range(30):
        out[:, 1:-1] = np.maximum(out[:, 1:-1], 0.25 * (out[:, :-2] + 2.0 * out[:, 1:-1] + out[:, 2:]))
    out = out - FALL_INSET - FALL_DIVE * ramp((z - widest[:, None]) / 0.02) + flare * ramp((FALL_FLARE - z) / 0.12)
    rows = z <= widest.max() + 0.02
    out, z = out[:, rows], z[rows, None]
    phi = np.linspace(0.0, 2.0 * np.pi, FALL_RING, endpoint=False)          # out round the back, and in again
    at = 0.5 * (1.0 - np.cos(phi)) * (len(angles) - 1)
    k = np.minimum(at.astype(int), len(angles) - 2)
    radius = out[k].T * (k + 1 - at) + out[k + 1].T * (at - k)
    a, side = np.radians(FALL_FROM + at * FALL_STEP[1]), np.sin(phi)
    r = (radius + 0.5 * thick * (np.sign(side) * np.abs(side) ** 0.4 - 1.0)
         + locks * np.sin(FALL_LOCKS * a) * np.maximum(side, 0.0)
         + wave * ramp((widest.max() - z) / 0.04) * np.sin(2.0 * np.pi * z / FALL_WAVE + 2.5 * np.sin(5.0 * a)))
    pts = np.stack([r * np.sin(a), AXIS_Y + r * np.cos(a), np.broadcast_to(z, r.shape)], -1).reshape(-1, 3)
    n, row = len(phi), len(phi) * np.arange(len(z) - 1)[:, None]
    ring = np.arange(n)
    quads = np.stack([row + ring, row + (ring + 1) % n, row + n + (ring + 1) % n, row + n + ring], -1).reshape(-1, 4)
    sheet = bl.to_object("fall", STAND.w(pts), quads, STAND.dir(normals(pts, quads)))
    across = np.broadcast_to(STRAND_ROUND * a + 2.0 * SIDES, r.shape).ravel()
    carry(sheet, across, np.tile((0.0, 0.0, 1.0), (len(pts), 1)))
    sheet.data.materials.append(streaked("fall", HAIR, vertex_color=False))


def level(v):
    """The points v of a head turned forward by PITCH about the left-right axis, chin down."""
    a = np.radians(PITCH)
    y, z = v[:, 1], v[:, 2]
    return np.stack([v[:, 0], y * np.cos(a) + z * np.sin(a), z * np.cos(a) - y * np.sin(a)], 1)


def portrait(model, face, path, view, light, style="crop", lopsided=(), frame=None):
    """One face alone in the scene, level, painted, with brows and the hair of HAIRS `style` names. `face` is
    its coefficients and then its brow numbers; `lopsided` weighs the model's asymmetries. The camera turns
    about `frame`'s target and shows its height, (TARGET, SCALE) unless given."""
    target, scale = frame or (TARGET, SCALE)
    bl.reset_scene()
    stand, hair = groom(model.mean, face[len(model.directions):], style)
    skin = paint(model.mean, model.eyes)
    v, quads, n, _ = model.mesh(face, lopsided)
    v = level(v + n * stand[:, None])
    colour = skin + hair[:, None] * (np.array(HAIR) - skin)
    face = bl.to_object("face", STAND.w(v), quads, STAND.dir(normals(v, quads)), colour)
    for material in (bl.clay("skin", base=(1.0, 1.0, 1.0), rough=0.5), HAIRS[style].coat(face, model.mean),
                     bl.clay("eye", base=(1.0, 1.0, 1.0), rough=0.15)):
        face.data.materials.append(material)
    index = np.where(model.eyes[quads].mean(1) > 0.5, 2, (hair[quads].mean(1) > 0.5).astype(np.int32))
    face.data.polygons.foreach_set("material_index", index.astype(np.int32))
    HAIRS[style].dress(v)
    bl.turnaround(path, [view], target, scale, TILE,bl.studio(LAMPS[0], [e * light for e in LAMPS[1]]))
    tile = bl.read_image(path)
    os.remove(path)
    return tile


def style(name):
    """The hair a set of faces wears: the women's pool, refinement rounds and best faces WOMEN, every other set
    short hair."""
    return WOMEN if name.startswith("women") else "crop"


def save(path, pixels):
    with whole(path) as part:
        bpy.data.images.remove(bl.save_image(part, pixels))


def sheet(model, faces, lopsided, path, view, light, hair="crop"):
    """The faces, each as lopsided as its row of `lopsided` says, SIDE to a row, first at the top left."""
    path = os.path.abspath(path)
    tiles = [portrait(model, c, path + ".tile.png", view, light, hair, uneven) for c, uneven in zip(faces, lopsided)]
    rows = [np.concatenate(tiles[k:k + SIDE], axis=1) for k in range(0, len(tiles), SIDE)]
    save(path, np.concatenate(rows[::-1], axis=0))
    print("GRID", path)


def uneven(model, rng, count):
    """How lopsided each of `count` generated faces is: its weights on the model's asymmetries."""
    return rng.normal(0.0, LOPSIDED, (count, len(model.asymmetries)))


def drawn(model, sex, seed, spread=SPREAD):
    """The faces the grid draws with this seed, of the sex if given, and how lopsided each is."""
    rng = np.random.default_rng(seed)
    draw = sex.sample if sex else model.sample
    faces = [draw(rng, spread) for _ in range(SIDE * SIDE)]
    return faces, uneven(model, rng, len(faces))


def grid(model, sex, path, seed, spread, view, light, hair):
    sheet(model, *drawn(model, sex, seed, spread), path, view, light, hair)


def worn(folder):
    """The look and the hair the set rendered in the folder wears, "crop" if it was rendered before the hair
    was kept: every set was short-haired then but the women's, whose bun is no hair now."""
    with np.load(files.index(folder)) as f:
        return int(f["look"]) if "look" in f.files else None, str(f["hair"]) if "hair" in f.files else "crop"


def render_in(model, folder, faces, share, spread, light, set_name, hair, views=VIEWS, frame=None):
    """Renders a set of faces in the folder in that hair, each from every view side by side in the portraits'
    `frame` and symmetric, keeping those
    already rendered, so a render cut short carries on where it stopped; each picture and the set's index
    appear whole or not at all. Other faces, another look or other hair replace the set. Returns whether the
    faces changed."""
    os.makedirs(folder, exist_ok=True)
    changed = looks = True
    if files.exists(folder):
        changed = not np.array_equal(files.rendered(folder)[0], faces)
        looks = changed or worn(folder) != (LOOK, hair)
    if looks:
        for old in os.listdir(folder):
            os.remove(os.path.join(folder, old))
        with whole(files.index(folder)) as part, open(part, "wb") as f:
            np.savez(f, faces=faces, share=share, spread=spread, look=LOOK, hair=hair, set=set_name)
    t0 = time.time()
    for i, c in enumerate(faces):
        path = files.picture(i, folder)
        if not os.path.exists(path):
            tiles = [portrait(model, c, path + ".tile.png", view, light, hair, frame=frame) for view in views]
            save(path, np.concatenate(tiles, axis=1))
            print("%s %d/%d  t=%.0fs" % (os.path.basename(folder).upper(), i + 1, len(faces), time.time() - t0),
                  flush=True)
    return changed


def render_set(model, name, faces, share, spread, light, set_name):
    """Renders a set of faces for the dev to judge (files.py) in the look and the hair (style) it should wear.
    Other faces replace it (render_in); the same faces, rendered whole in another look, are rendered again
    beside the set and then put in its place a picture at a time, so that the set he rates is whole and its
    faces the same however the render ends. `share` and `spread` are what the prior on his taste in them
    needs (taste.prior). Returns whether the faces changed."""
    folder, beside, hair = files.folder(name), files.folder(name + "_again"), style(name)
    if files.complete(folder) and worn(folder) != (LOOK, hair) and np.array_equal(files.rendered(folder)[0], faces):
        render_in(model, beside, faces, share, spread, light, set_name, hair)
        for path in [files.picture(i, folder) for i in range(len(faces))] + [files.index(folder)]:
            with whole(path) as part:
                shutil.copyfile(os.path.join(beside, os.path.basename(path)), part)
    shutil.rmtree(beside, ignore_errors=True)
    return render_in(model, folder, faces, share, spread, light, set_name, hair)


def pool(model, name, light):
    """Renders taste.py's pool of faces of the sex, and its latest refinement round in the same look; the
    rounds drawn when the pool held other faces go with them."""
    refined = taste.refine_folder(name)
    if render_set(model, name, taste.pool(Sex(model, name)), taste.shares(model), taste.spread(model), light, taste.POOL):
        for old in (refined, taste.next_folder(name)):
            shutil.rmtree(old, ignore_errors=True)
    elif files.exists(refined):
        faces, share, spread, set_name = files.rendered(refined)
        render_set(model, os.path.basename(refined), faces, share, spread, light, set_name)


def refine(model, sex, answers, seed, light):
    """Renders the sex's next refinement round from his answers so far beside the latest, or finishes the
    one drawn there before; the rating tool puts it in place of the latest (taste.advance)."""
    where = taste.next_folder(sex.name)
    if files.exists(where):
        faces, share, spread, set_name = files.rendered(where)
        print("REFINE %s %s resumed" % (sex.name, set_name))
    else:
        answers = taste.Answers(answers)
        if not answers.lines:
            sys.exit("No answers on the %s yet: rate the pool first." % sex.name)
        latest = taste.refine_folder(sex.name)
        last = files.rendered(latest)[3] if files.exists(latest) else "refine 0"
        n = max(int(last.split()[1]), answers.rounds()) + 1
        share, spread, set_name = taste.shares(model), taste.spread(model), "refine %d" % n
        faces = taste.refine(answers.posterior(taste.prior(share, spread, sex)), sex, np.random.default_rng((seed, n)))
        print("REFINE %s %s from %d answers" % (sex.name, set_name, len(answers)))
    render_set(model, os.path.basename(where), faces, share, spread, light, set_name)


def numbers(path):
    """Where the numbers of the faces in the grid at `path` are kept: beside it, a .json."""
    return os.path.splitext(path)[0] + ".json"


def note(path, kept):
    """Keeps the numbers of the faces in the grid at `path`, whole (whole)."""
    with whole(numbers(path)) as part, open(part, "w", encoding="utf-8", newline="\n") as f:
        json.dump(kept, f, indent=1)


def best(model, sex, path, answers, seed, view, light):
    """The best faces as a grid at `path`, and then their numbers beside it, with the count of answers
    they were learnt from and the look and the hair they wear: a render cut short leaves the numbers of the
    faces before."""
    answers, rng = taste.Answers(answers), np.random.default_rng(seed)
    posterior = answers.posterior(taste.prior(taste.shares(model), taste.spread(model), sex))
    faces, score = taste.best(posterior, sex, rng, SIDE * SIDE)
    lopsided = uneven(model, rng, len(faces))
    sheet(model, faces, lopsided, path, view, light, style(sex.name))
    note(path, dict(answers=len(answers), look=LOOK, hair=style(sex.name), faces=[
        dict(logit=round(float(s), 3), coefficients=np.round(c, 5).tolist(), lopsided=np.round(u, 5).tolist())
        for c, s, u in zip(faces, score, lopsided)]))
    print("BEST %s from %d answers" % (numbers(path), len(answers)))


def again(model, name, view, light):
    """Renders, from the faces each holds, every set of faces of the sex of that name in the look and the hair
    it should wear (render_set), finishing any cut short: its pool, its latest refinement round and the next,
    and its best faces."""
    for folder in (files.folder(name), taste.refine_folder(name), taste.next_folder(name)):
        if files.exists(folder):
            faces, share, spread, set_name = files.rendered(folder)
            render_set(model, os.path.basename(folder), faces, share, spread, light, set_name)
    path = taste.best_picture(name)
    if os.path.exists(numbers(path)):
        with open(numbers(path), encoding="utf-8") as f:
            kept = json.load(f)
        if (kept.get("look"), kept.get("hair")) != (LOOK, style(name)):
            faces = kept["faces"]
            sheet(model, [np.array(face["coefficients"]) for face in faces],
                  [np.array(face["lopsided"]) for face in faces], path, view, light, style(name))
            note(path, dict(kept, look=LOOK, hair=style(name)))


def current(again=False, detail=1.0):
    """The face model, fitted again (at that detail) if asked or if fit.py fits another way now, and given
    features if makehuman.py names other shapes now."""
    model = Model.load(MODEL) if os.path.exists(MODEL) and not again else None
    if model is None or model.fitted != fit.VERSION:
        model = learn(detail)
    if model.names != list(makehuman.SHAPES):
        model = featured(model)
    return model


def main():
    model = current("--fit" in argv, float(opt("--detail", "1.0")))
    sex = Sex(model, opt("--sex")) if opt("--sex") else None
    light, view = float(opt("--light", "1.0")), float(opt("--view", "0"))
    if (opt("--best") or "--refine" in argv) and not sex:
        sys.exit("--best and --refine need --sex women or men")
    hair = opt("--hair", style(sex.name if sex else ""))
    if hair not in HAIRS:
        sys.exit("--hair is one of " + ", ".join(HAIRS))
    if opt("--grid"):
        grid(model, sex, opt("--grid"), int(opt("--seed", "1")), float(opt("--spread", str(SPREAD))), view, light, hair)
    if "--labels" in argv:
        render_set(model, "labels", label_set(model), model.share, LABEL_SPREAD, light, "labels")
    if "--pool" in argv:
        for name in [sex.name] if sex else SEXES:
            pool(model, name, light)
    if "--again" in argv:
        for name in [sex.name] if sex else SEXES:
            again(model, name, view, light)
    answers = opt("--answers", taste.answers(sex.name)) if sex else None
    if "--refine" in argv:
        refine(model, sex, answers, int(opt("--seed", "1")), light)
    if opt("--best"):
        best(model, sex, opt("--best"), answers, int(opt("--seed", "1")), view, light)


if __name__ == "__main__":
    main()

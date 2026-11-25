"""Builds the face model, tools/faces/model.npz, and shows faces drawn from it.

  blender --background --python build_faces.py -- [--fit] [--detail 1.0] [--sex women|men] [--grid a.png]
          [--seed 1] [--spread 0.65] [--view 0] [--light 1.0] [--labels] [--pool] [--refine] [--best a.png] [--answers a.jsonl]

--fit learns the model from the heads tools/fetch_assets.ps1 downloads, as does a missing model (eight
minutes); --detail scales its lattice, as it does a figure's. A model whose features are not the shapes
makehuman.py names now is given those first (three minutes). --grid renders 25 random faces, of --sex if
given (see sexes.py), each alone under the same camera and lamps, turned --view degrees. --spread is the
share of the people's standard deviation the faces are drawn at. --labels renders the label set the dev
labels the sexes on, --pool the pools taste.py shows him, of --sex or both, each face from the front and
turned, keeping those already rendered, and their refinement rounds. --refine renders the next refinement
round of --sex (taste.refine) from his answers, or from --answers, or finishes the one begun; the rating
tool runs it in the background, and once it is rendered shows it in place of the pool or the round before.
--best renders the 25 faces of --sex furthest along the taste learnt from his answers, or from --answers,
as a grid, best first, and writes their numbers beside it: a.json.

Every face is painted the same, with skin, lips, eyes and hair, so that only its shape and its brows
differ. The label set wears short hair, so that no face reads as a sex for its hair; the women's pool wears
its hair pulled back into a bun, which is the same on every woman, so the taste learnt from it is still
the face's. The faces he judges are symmetric, so that his answers measure his taste and not chance; the
grid's and the best faces are each slightly lopsided, as people are, by weights a.json keeps.
"""
import bpy, json, sys, os, shutil, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl
from sculpt.bl import argv, opt
from sculpt.gen import Frame
from faces import brows, files, fit, ict, makehuman, taste
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
LOOK = 5                                        # the renders' look: a set rendered in another is rendered again
SKIN, HAIR = (0.60, 0.40, 0.30), (0.045, 0.032, 0.025)
LIPS, CHEEKS = (0.52, 0.24, 0.21), (0.66, 0.36, 0.29)
WHITE, IRIS, PUPIL = (0.80, 0.77, 0.72), (0.16, 0.10, 0.05), (0.01, 0.01, 0.01)
# The eyeball's visible surface: a sphere about this centre (on +x), and the angles off straight ahead
# (degrees) the iris and pupil reach.
EYE, EYE_R, IRIS_ANGLE, PUPIL_ANGLE = (0.032, 0.0565, 0.0005), 0.0123, 31.0, 11.0
# The lips: the line they meet on is this high on the midline; they reach out to the corners at x and up
# and down from the line by these heights in the middle, rounding off to the corners.
MOUTH_Z, MOUTH_X, UPPER, LOWER = -0.0695, 0.026, 0.013, 0.0135
CHEEK, CHEEK_R = (0.046, 0.06, -0.030), 0.024 # a faint flush, its centre on +x and its reach
BUN, BUN_STAND, BUN_Z = 0.032, 0.016, (0.05, 0.08)  # the bun's radius, how far its centre stands off the head, and the band it sits in
# The hairline's height above the eyes round the head, by the angle from the front (degrees) about an
# upright axis at y = AXIS_Y: high on the forehead, short sideburns, above the ears and down to the nape.
AXIS_Y = -0.01
HAIRLINE = ((0, 0.071), (30, 0.066), (50, 0.058), (65, 0.045), (74, 0.028), (80, -0.012), (86, -0.012),
            (92, 0.003), (115, 0.003), (128, -0.010), (145, -0.040), (165, -0.065), (180, -0.070))
EARS = (0.080, 0.006, -0.075)                  # no hair further out than x, below z and in front of y
CROP = (0.003, 0.008, 0.010)                   # hair thickness low on the head and at the crown, rising from this z
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
    """The model with MakeHuman's shapes for its features, and with its asymmetries if it was fitted before
    it kept them: saved."""
    t0 = time.time()
    asymmetries = model.asymmetries if len(model.asymmetries) else fit.asymmetries(ict.Heads(), model.mean)
    model = Model(model.mean, model.components, model.share, model.quads, model.lat, asymmetries,
                  *makehuman.shapes(makehuman.Fit(model)))
    model.save(MODEL)
    print("FEATURED features=%d asymmetries=%d  t=%.1fs" % (len(model.names), len(asymmetries), time.time() - t0))
    return model


def ramp(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def groom(mean, brow):
    """The hair, the same on every face, and the brows its brow numbers shape, as each vertex of the model's
    lattice carries them: how far the hair stands off the skin (metres), and how much of the vertex is hair
    or brow, from 0 to 1."""
    x, y, z = np.abs(mean[:, 0]), mean[:, 1] - AXIS_Y, mean[:, 2]
    angle = np.degrees(np.arctan2(x, y))
    above = z - np.interp(angle, *zip(*HAIRLINE))
    bare = ramp((x - EARS[0]) / 0.004) * ramp((EARS[1] - z) / 0.004) * (mean[:, 1] > EARS[2])
    hair = ramp(above / 0.003 + 0.5) * (1.0 - bare)
    thick = CROP[0] + (CROP[1] - CROP[0]) * ramp((z - CROP[2]) / 0.08)
    stand = thick * ramp(above / 0.020) * (1.0 - bare)
    brow = brows.brow(x, z, brow) * (mean[:, 1] > 0.03)
    return stand + BROW_RISE * brow, np.maximum(hair, brow)


def paint(mean):
    """The colour every face carries at each vertex of the lattice, before hair: skin, flushed cheeks, lips
    and eyes; and how much of each vertex is eye, from 0 to 1."""
    x, y, z = np.abs(mean[:, 0]), mean[:, 1], mean[:, 2]
    colour = np.tile(np.array(SKIN), (len(mean), 1))
    flush = 0.5 * ramp(1.0 - np.linalg.norm(np.stack([x, y, z], 1) - CHEEK, axis=1) / CHEEK_R)
    colour += flush[:, None] * (np.array(CHEEKS) - SKIN)
    across = np.sqrt(np.clip(1.0 - (x / MOUTH_X) ** 2, 0.0, 1.0))
    height = np.where(z > MOUTH_Z, UPPER, LOWER) * across
    lip = ramp((1.0 - np.abs(z - MOUTH_Z) / np.maximum(height, 1e-6)) * 4.0) * (y > 0.06) * (x < MOUTH_X)
    colour += lip[:, None] * (np.array(LIPS) - colour)
    out = np.stack([x, y, z], 1) - EYE
    reach = np.linalg.norm(out, axis=1)
    eye = (reach < EYE_R) * (out[:, 1] > 0)
    angle = np.degrees(np.arccos(np.clip(out[:, 1] / np.maximum(reach, 1e-9), -1.0, 1.0)))
    ball = np.where(angle < PUPIL_ANGLE, 0, np.where(angle < IRIS_ANGLE, 1, 2))
    colour[eye] = np.array((PUPIL, IRIS, WHITE))[ball[eye]]
    return colour, eye.astype(np.float64)


def bun(v):
    """A ball of hair high on the back of the head, standing off its back-most point there, up and back."""
    back = v[(np.abs(v[:, 0]) < 0.01) & (v[:, 2] > BUN_Z[0]) & (v[:, 2] < BUN_Z[1])]
    p = back[np.argmin(back[:, 1])]
    bpy.ops.mesh.primitive_uv_sphere_add(radius=BUN, segments=32, ring_count=16,
                                         location=STAND.w((p + (0.0, -BUN_STAND, 0.4 * BUN_STAND))[None])[0])
    ob = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    ob.data.materials.append(bl.clay("bun", base=HAIR, rough=0.85, vertex_color=False))
    return ob


def level(v):
    """The points v of a head turned forward by PITCH about the left-right axis, chin down."""
    a = np.radians(PITCH)
    y, z = v[:, 1], v[:, 2]
    return np.stack([v[:, 0], y * np.cos(a) + z * np.sin(a), z * np.cos(a) - y * np.sin(a)], 1)


def portrait(model, face, path, view, light, style="crop", lopsided=()):
    """One face alone in the scene, level, painted, with hair and brows: style "crop" short, "bun" pulled
    back. `face` is its coefficients and then its brow numbers; `lopsided` weighs the model's asymmetries."""
    bl.reset_scene()
    stand, hair = groom(model.mean, face[len(model.directions):])
    skin, eye = paint(model.mean)
    v, quads, n, _ = model.mesh(face, lopsided)
    v = level(v + n * stand[:, None])
    colour = skin + hair[:, None] * (np.array(HAIR) - skin)
    face = bl.to_object("face", STAND.w(v), quads, STAND.dir(normals(v, quads)), colour)
    for name, rough in (("skin", 0.5), ("hair", 0.85), ("eye", 0.15)):
        face.data.materials.append(bl.clay(name, base=(1.0, 1.0, 1.0), rough=rough))
    index = np.where(eye[quads].mean(1) > 0.5, 2, (hair[quads].mean(1) > 0.5).astype(np.int32))
    face.data.polygons.foreach_set("material_index", index.astype(np.int32))
    if style == "bun":
        bun(v)
    bl.turnaround(path, [view], TARGET, SCALE, TILE, bl.studio(LAMPS[0], [e * light for e in LAMPS[1]]))
    tile = bl.read_image(path)
    os.remove(path)
    return tile


def style(name):
    """The hair a set of faces wears: the women's pool and refinement rounds a bun, every other set short hair."""
    return "bun" if name.startswith("women") else "crop"


def sheet(model, faces, lopsided, path, view, light, hair="crop"):
    """The faces, each as lopsided as its row of `lopsided` says, SIDE to a row, first at the top left."""
    path = os.path.abspath(path)
    tiles = [portrait(model, c, path + ".tile.png", view, light, hair, uneven) for c, uneven in zip(faces, lopsided)]
    rows = [np.concatenate(tiles[k:k + SIDE], axis=1) for k in range(0, len(tiles), SIDE)]
    bl.save_image(path, np.concatenate(rows[::-1], axis=0))
    print("GRID", path)


def uneven(model, rng, count):
    """How lopsided each of `count` generated faces is: its weights on the model's asymmetries."""
    return rng.normal(0.0, LOPSIDED, (count, len(model.asymmetries)))


def grid(model, sex, path, seed, spread, view, light):
    rng = np.random.default_rng(seed)
    draw = sex.sample if sex else model.sample
    faces = [draw(rng, spread) for _ in range(SIDE * SIDE)]
    sheet(model, faces, uneven(model, rng, len(faces)), path, view, light, style(sex.name if sex else ""))


def render_set(model, name, faces, share, spread, light, set_name):
    """Renders a set of faces for the dev to judge (files.py), each from every view and symmetric, keeping
    those already rendered, so a render cut short carries on where it stopped; each picture and the set's
    index appear whole or not at all. Other faces, or another look, replace the set. `share` and `spread` are what
    the prior on his taste in them needs (taste.prior). Returns whether the faces changed."""
    folder = files.folder(name)
    index = os.path.join(folder, "pool.npz")
    os.makedirs(folder, exist_ok=True)
    changed = looks = True
    if os.path.exists(index):
        with np.load(index) as f:
            changed = not np.array_equal(f["faces"], faces)
            looks = changed or not ("look" in f.files and int(f["look"]) == LOOK)
    if looks:
        for old in os.listdir(folder):
            os.remove(os.path.join(folder, old))
        with open(index + ".part", "wb") as f:
            np.savez(f, faces=faces, share=share, spread=spread, look=LOOK, set=set_name)
        os.replace(index + ".part", index)
    t0 = time.time()
    for i, c in enumerate(faces):
        path = files.picture(i, folder)
        if not os.path.exists(path):
            views = [portrait(model, c, path + ".tile.png", view, light, style(name)) for view in VIEWS]
            bpy.data.images.remove(bl.save_image(path + ".part.png", np.concatenate(views, axis=1)))
            os.replace(path + ".part.png", path)
            print("%s %d/%d  t=%.0fs" % (name.upper(), i + 1, len(faces), time.time() - t0), flush=True)
    return changed


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
        faces = taste.refine(answers.posterior(taste.prior(share, spread)), sex, np.random.default_rng((seed, n)))
        print("REFINE %s %s from %d answers" % (sex.name, set_name, len(answers)))
    render_set(model, os.path.basename(where), faces, share, spread, light, set_name)


def best(model, sex, path, answers, seed, view, light):
    """The best faces as a grid at `path`, and then their numbers beside it, with the count of answers
    they were learnt from: a render cut short leaves the numbers of the faces before."""
    answers, rng = taste.Answers(answers), np.random.default_rng(seed)
    posterior = answers.posterior(taste.prior(taste.shares(model), taste.spread(model)))
    faces, score = taste.best(posterior, sex, rng, SIDE * SIDE)
    lopsided = uneven(model, rng, len(faces))
    sheet(model, faces, lopsided, path, view, light, style(sex.name))
    numbers = os.path.splitext(path)[0] + ".json"
    with open(numbers, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(answers=len(answers), faces=[
            dict(logit=round(float(s), 3), coefficients=np.round(c, 5).tolist(), lopsided=np.round(u, 5).tolist())
            for c, s, u in zip(faces, score, lopsided)]), f, indent=1)
    print("BEST %s from %d answers" % (numbers, len(answers)))


def main():
    fitted = "--fit" in argv or not os.path.exists(MODEL)
    model = learn(float(opt("--detail", "1.0"))) if fitted else Model.load(MODEL)
    if fitted or model.names != list(makehuman.SHAPES):
        model = featured(model)
    sex = Sex(model, opt("--sex")) if opt("--sex") else None
    light, view = float(opt("--light", "1.0")), float(opt("--view", "0"))
    if (opt("--best") or "--refine" in argv) and not sex:
        sys.exit("--best and --refine need --sex women or men")
    if opt("--grid"):
        grid(model, sex, opt("--grid"), int(opt("--seed", "1")), float(opt("--spread", str(SPREAD))), view, light)
    if "--labels" in argv:
        render_set(model, "labels", label_set(model), model.share, LABEL_SPREAD, light, "labels")
    if "--pool" in argv:
        for name in [sex.name] if sex else SEXES:
            pool(model, name, light)
    answers = opt("--answers", taste.answers(sex.name)) if sex else None
    if "--refine" in argv:
        refine(model, sex, answers, int(opt("--seed", "1")), light)
    if opt("--best"):
        best(model, sex, opt("--best"), answers, int(opt("--seed", "1")), view, light)


main()

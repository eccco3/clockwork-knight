"""Builds the face model, tools/faces/model.npz, and shows faces drawn from it.

  blender --background --python build_faces.py -- [--fit] [--detail 1.0] [--sex women|men] [--grid a.png]
          [--seed 1] [--spread 0.65] [--view 0] [--light 1.0] [--labels] [--pool] [--best a.png] [--answers a.jsonl]

--fit learns the model from the heads tools/fetch_assets.ps1 downloads, as does a missing model; --detail
scales its lattice, as it does a figure's. --grid renders 25 random faces, of --sex if given (see
sexes.py), each alone under the same camera and lamps, turned --view degrees. --spread is the share of
the people's standard deviation the faces are drawn at. --labels renders the label set the dev labels the
sexes on, --pool the pools taste.py shows him, of --sex or both, each face from the front and turned,
keeping those already rendered. --best renders the 25 faces of --sex furthest along the taste learnt
from his answers to them, or to --answers, as a grid, best first, and writes their coefficients beside
it: a.json.

Every face is clay with the same short hair and brows, so that no face reads as a sex for its hair.
"""
import bpy, json, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl
from sculpt.bl import argv, opt
from sculpt.gen import Frame
from faces import ict, fit, taste, files
from faces.model import Model, SPREAD, normals
from faces.sexes import SEXES, LABEL_SPREAD, Sex, label_set

MODEL = os.path.join(HERE, "model.npz")
SIDE = 5                                        # the grid shows SIDE * SIDE faces
STAND = Frame((0, 0, 1.63), (0, 0, 1), (-1, 0, 0))            # a head on a standing figure, facing the camera
TARGET, SCALE, TILE = (0, 0, 1.61), 0.30, (360, 400)
LAMPS = ((2.6, 1.2, 2.4), (135.0, 33.0, 90.0))                # the figures' preview lamps, dimmed for pale clay
VIEWS = (0.0, 35.0)                             # a rendered set shows each face from these
LOOK = 2                                        # the renders' look: a set rendered in another is rendered again
CLAY, HAIR = (0.62, 0.60, 0.58), (0.045, 0.032, 0.025)
# The hairline's height above the eyes round the head, by the angle from the front (degrees) about an
# upright axis at y = AXIS_Y: high on the forehead, short sideburns, above the ears and down to the nape.
AXIS_Y = -0.01
HAIRLINE = ((0, 0.071), (30, 0.066), (50, 0.058), (65, 0.045), (74, 0.028), (80, -0.012), (86, -0.012),
            (92, 0.003), (115, 0.003), (128, -0.010), (145, -0.040), (165, -0.065), (180, -0.070))
EARS = (0.080, 0.006, -0.075)                  # no hair further out than x, below z and in front of y
CROP = (0.003, 0.008, 0.010)                   # hair thickness low on the head and at the crown, rising from this z
BROW = ((0.013, 0.021, 0.0045), (0.038, 0.027, 0.0038), (0.058, 0.022, 0.0014))   # (x, z, half height) along a brow
BROW_RISE, BROW_DENSITY = 0.0006, 0.9


def learn(detail):
    t0 = time.time()
    model = fit.fit(ict.Heads(), detail)
    model.save(MODEL)
    print("FITTED verts=%d quads=%d components=%d  t=%.1fs" % (len(model.mean), len(model.quads), len(model.components),
                                                              time.time() - t0))
    print("VARIANCE", " ".join("%.1f" % (100 * s) for s in model.share[:12]), "... percent")
    return model


def ramp(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3.0 - 2.0 * x)


def groom(mean):
    """The hair and brows, the same on every face as each vertex of the model's lattice carries them: how far
    the hair stands off the skin (metres), and how much of the vertex is hair or brow, from 0 to 1."""
    x, y, z = np.abs(mean[:, 0]), mean[:, 1] - AXIS_Y, mean[:, 2]
    angle = np.degrees(np.arctan2(x, y))
    above = z - np.interp(angle, *zip(*HAIRLINE))
    bare = ramp((x - EARS[0]) / 0.004) * ramp((EARS[1] - z) / 0.004) * (mean[:, 1] > EARS[2])
    hair = ramp(above / 0.003 + 0.5) * (1.0 - bare)
    thick = CROP[0] + (CROP[1] - CROP[0]) * ramp((z - CROP[2]) / 0.08)
    stand = thick * ramp(above / 0.020) * (1.0 - bare)
    xs, zs, halves = zip(*BROW)
    middle, half = np.polyval(np.polyfit(xs, zs, 2), x), np.interp(x, xs, halves)
    brow = ramp((1.0 - np.abs(z - middle) / half) * 2.0) * ramp((x - xs[0]) / 0.003) * ramp((xs[-1] - x) / 0.003)
    brow *= BROW_DENSITY * (mean[:, 1] > 0.03) * (x >= xs[0]) * (x <= xs[-1])
    return stand + BROW_RISE * brow, np.maximum(hair, brow)


def portrait(model, coefficients, path, view, light):
    """One face alone in the scene, in clay with hair and brows."""
    bl.reset_scene()
    stand, hair = groom(model.mean)
    v, quads, n, _ = model.mesh(coefficients)
    v = v + n * stand[:, None]
    colour = 1.0 + hair[:, None] * (np.array(HAIR) / CLAY - 1.0)
    face = bl.to_object("face", STAND.w(v), quads, STAND.dir(normals(v, quads)), colour)
    for name, rough in (("skin", 0.55), ("hair", 0.85)):
        face.data.materials.append(bl.clay(name, base=CLAY, rough=rough))
    face.data.polygons.foreach_set("material_index", (hair[quads].mean(1) > 0.5).astype(np.int32))
    bl.turnaround(path, [view], TARGET, SCALE, TILE, bl.studio(LAMPS[0], [e * light for e in LAMPS[1]]))
    tile = bl.read_image(path)
    os.remove(path)
    return tile


def sheet(model, faces, path, view, light):
    """The faces, SIDE to a row, first at the top left."""
    path = os.path.abspath(path)
    tiles = [portrait(model, c, path + ".tile.png", view, light) for c in faces]
    rows = [np.concatenate(tiles[k:k + SIDE], axis=1) for k in range(0, len(tiles), SIDE)]
    bl.save_image(path, np.concatenate(rows[::-1], axis=0))
    print("GRID", path)


def grid(model, sex, path, seed, spread, view, light):
    rng = np.random.default_rng(seed)
    draw = sex.sample if sex else model.sample
    sheet(model, [draw(rng, spread) for _ in range(SIDE * SIDE)], path, view, light)


def render_set(model, name, faces, spread, light):
    """Renders a set of faces for the dev to judge (files.py), each from every view, keeping those already
    rendered; other faces, or another look, replace the set. Returns whether they did."""
    folder = files.folder(name)
    index = os.path.join(folder, "pool.npz")
    os.makedirs(folder, exist_ok=True)
    replaced = True
    if os.path.exists(index):
        with np.load(index) as f:
            replaced = not ("look" in f.files and int(f["look"]) == LOOK and np.array_equal(f["faces"], faces))
    if replaced:
        for old in os.listdir(folder):
            os.remove(os.path.join(folder, old))
        np.savez(index, faces=faces, share=model.share, spread=spread, look=LOOK)
    t0 = time.time()
    for i, c in enumerate(faces):
        path = files.picture(i, folder)
        if not os.path.exists(path):
            views = [portrait(model, c, path + ".tile.png", view, light) for view in VIEWS]
            bpy.data.images.remove(bl.save_image(path, np.concatenate(views, axis=1)))
            print("%s %d/%d  t=%.0fs" % (name.upper(), i + 1, len(faces), time.time() - t0), flush=True)
    return replaced


def pool(model, name, light):
    """Renders taste.py's pool of faces of the sex; answers given on an earlier pool go with it."""
    answers = taste.answers(name)
    if render_set(model, name, taste.pool(Sex(model, name)), SPREAD, light) and os.path.exists(answers):
        os.remove(answers)
        print("DISCARDED", answers, "given on the earlier pool")


def best(model, sex, path, answers, seed, view, light):
    answers = taste.Answers(answers)
    posterior = answers.posterior(taste.prior(model.share, SPREAD))
    faces, score = taste.best(posterior, sex, np.random.default_rng(seed), SIDE * SIDE)
    coefficients = os.path.splitext(path)[0] + ".json"
    with open(coefficients, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(answers=len(answers), faces=[dict(logit=round(float(s), 3), coefficients=np.round(c, 5).tolist())
                                                    for c, s in zip(faces, score)]), f, indent=1)
    print("BEST %s from %d answers" % (coefficients, len(answers)))
    sheet(model, faces, path, view, light)


def main():
    model = learn(float(opt("--detail", "1.0"))) if "--fit" in argv or not os.path.exists(MODEL) else Model.load(MODEL)
    sex = Sex(model, opt("--sex")) if opt("--sex") else None
    light, view = float(opt("--light", "1.0")), float(opt("--view", "0"))
    if opt("--best") and not sex:
        sys.exit("--best needs --sex women or men")
    if opt("--grid"):
        grid(model, sex, opt("--grid"), int(opt("--seed", "1")), float(opt("--spread", str(SPREAD))), view, light)
    if "--labels" in argv:
        render_set(model, "labels", label_set(model), LABEL_SPREAD, light)
    if "--pool" in argv:
        for name in [sex.name] if sex else SEXES:
            pool(model, name, light)
    if opt("--best"):
        best(model, sex, opt("--best"), opt("--answers", taste.answers(sex.name)), int(opt("--seed", "1")), view, light)


main()

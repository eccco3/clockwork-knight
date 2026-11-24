"""Builds the face model, tools/faces/model.npz, and shows faces drawn from it.

  blender --background --python build_faces.py -- [--fit] [--detail 1.0] [--grid a.png] [--seed 1] [--spread 0.65]
          [--view 0] [--light 1.0] [--pool] [--best a.png] [--answers taste.jsonl]

--fit learns the model from the heads tools/fetch_assets.ps1 downloads, as does a missing model; --detail
scales its lattice, as it does a figure's. --grid renders 25 random faces in clay, each alone under the
same camera and lamps, turned --view degrees. --spread is the share of the people's standard deviation
the faces are drawn at. --pool renders the faces taste.py shows the dev, each from the front and turned,
keeping those already rendered. --best renders the 25 faces furthest along the taste learnt from his
--answers as a grid, best first, and writes their coefficients beside it: a.json.
"""
import bpy, json, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, build
from sculpt.bl import argv, opt
from sculpt.gen import Frame
from faces import ict, fit, taste
from faces.model import Model, SPREAD

MODEL = os.path.join(HERE, "model.npz")
SIDE = 5                                        # the grid shows SIDE * SIDE faces
STAND = Frame((0, 0, 1.63), (0, 0, 1), (-1, 0, 0))            # a head on a standing figure, facing the camera
TARGET, SCALE, TILE = (0, 0, 1.61), 0.30, (360, 400)
LAMPS = ((2.6, 1.2, 2.4), (135.0, 33.0, 90.0))                # the figures' preview lamps, dimmed for pale clay
POOL_VIEWS = (0.0, 35.0)


def learn(detail):
    t0 = time.time()
    model = fit.fit(ict.Heads(), detail)
    model.save(MODEL)
    print("FITTED verts=%d quads=%d components=%d  t=%.1fs" % (len(model.mean), len(model.quads), len(model.components),
                                                              time.time() - t0))
    print("VARIANCE", " ".join("%.1f" % (100 * s) for s in model.share[:12]), "... percent")
    return model


def portrait(model, coefficients, path, view, light):
    """One face alone in the scene, in clay."""
    bl.reset_scene()
    v, quads, n, _ = model.mesh(coefficients)
    build.clay_objects([dict(name="face", v=STAND.w(v), q=quads, n=STAND.dir(n), mirror=False)])
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


def grid(model, path, seed, spread, view, light):
    rng = np.random.default_rng(seed)
    sheet(model, [model.sample(rng, spread) for _ in range(SIDE * SIDE)], path, view, light)


def pool(model, light):
    """Renders taste.py's pool of faces, all under the same camera and lamps; a new pool replaces the old."""
    faces = taste.pool(model)
    index = os.path.join(taste.POOL, "pool.npz")
    os.makedirs(taste.POOL, exist_ok=True)
    if not os.path.exists(index) or not np.array_equal(taste.load_pool()[0], faces):
        for name in os.listdir(taste.POOL):
            os.remove(os.path.join(taste.POOL, name))
        np.savez(index, faces=faces, share=model.share, spread=SPREAD)
    t0 = time.time()
    for i, c in enumerate(faces):
        path = taste.picture(i)
        if not os.path.exists(path):
            views = [portrait(model, c, path + ".tile.png", view, light) for view in POOL_VIEWS]
            bpy.data.images.remove(bl.save_image(path, np.concatenate(views, axis=1)))
            print("POOL %d/%d  t=%.0fs" % (i + 1, len(faces), time.time() - t0), flush=True)


def best(model, path, answers, seed, view, light):
    answers = taste.Answers(answers)
    posterior = answers.posterior(taste.prior(model.share, SPREAD))
    faces, score = taste.best(posterior, model, np.random.default_rng(seed), SIDE * SIDE)
    coefficients = os.path.splitext(path)[0] + ".json"
    with open(coefficients, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(answers=len(answers), faces=[dict(logit=round(float(s), 3), coefficients=np.round(c, 5).tolist())
                                                    for c, s in zip(faces, score)]), f, indent=1)
    print("BEST %s from %d answers" % (coefficients, len(answers)))
    sheet(model, faces, path, view, light)


def main():
    model = learn(float(opt("--detail", "1.0"))) if "--fit" in argv or not os.path.exists(MODEL) else Model.load(MODEL)
    if opt("--grid"):
        grid(model, opt("--grid"), int(opt("--seed", "1")), float(opt("--spread", str(SPREAD))), float(opt("--view", "0")),
             float(opt("--light", "1.0")))
    if "--pool" in argv:
        pool(model, float(opt("--light", "1.0")))
    if opt("--best"):
        best(model, opt("--best"), opt("--answers", taste.ANSWERS), int(opt("--seed", "1")), float(opt("--view", "0")), float(opt("--light", "1.0")))


main()

"""Builds the face model, tools/faces/model.npz, and shows faces drawn from it.

  blender --background --python build_faces.py -- [--fit] [--detail 1.0] [--grid a.png] [--seed 1] [--spread 0.65]
          [--view 0] [--light 1.0]

--fit learns the model from the heads tools/fetch_assets.ps1 downloads, as does a missing model; --detail
scales its lattice, as it does a figure's. --grid renders 25 random faces in clay, each alone under the
same camera and lamps, turned --view degrees. --spread is the share of the people's standard deviation
the faces are drawn at.
"""
import bpy, sys, os, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sculpt import bl, build
from sculpt.bl import argv, opt
from sculpt.gen import Frame
from faces import ict, fit
from faces.model import Model, SPREAD

MODEL = os.path.join(HERE, "model.npz")
SIDE = 5                                        # the grid shows SIDE * SIDE faces
STAND = Frame((0, 0, 1.63), (0, 0, 1), (-1, 0, 0))            # a head on a standing figure, facing the camera
TARGET, SCALE, TILE = (0, 0, 1.61), 0.30, (360, 400)
LAMPS = ((2.6, 1.2, 2.4), (135.0, 33.0, 90.0))                # the figures' preview lamps, dimmed for pale clay


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


def grid(model, path, seed, spread, view, light):
    rng = np.random.default_rng(seed)
    path = os.path.abspath(path)
    tiles = [portrait(model, model.sample(rng, spread), path + ".tile.png", view, light) for _ in range(SIDE * SIDE)]
    rows = [np.concatenate(tiles[k:k + SIDE], axis=1) for k in range(0, len(tiles), SIDE)]
    bl.save_image(path, np.concatenate(rows[::-1], axis=0))
    print("GRID", path)


def main():
    model = learn(float(opt("--detail", "1.0"))) if "--fit" in argv or not os.path.exists(MODEL) else Model.load(MODEL)
    if opt("--grid"):
        grid(model, opt("--grid"), int(opt("--seed", "1")), float(opt("--spread", str(SPREAD))), float(opt("--view", "0")),
             float(opt("--light", "1.0")))


main()

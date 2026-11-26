"""Features a face may gain beyond the 22 MakeHuman ones (makehuman.SHAPES), for the dev to judge: each alone
on the women's base face (women_base.json) at nine strengths, from the front and in profile, which
dev/features_women.tscn shows him so that he picks the strengths worth keeping and his favourite.

  blender --background --python tools/faces/candidates.py -- [--only mouth,nose,eyes]

renders, for each feature of the categories --only names, or of all, a picture into tools/faces/candidates/:
the nine strengths STEPS left to right, the front above the profile; and index.json, which lists them. His
answers are kept in tools/faces/features_women.json.

A MakeHuman feature's strength is a share of its full slider, carried onto the model as the 22 are
(makehuman.Fit). MakeHuman's eye targets barely move the lids (at most 1.7 mm at full slider), so the eyes'
features are made here instead: the whole eye, lids and eyeball together, moved rigidly and faded out
around it, so the lids never leave the eyeball, one UNITS step per unit of strength.

The faces wear the paint the dev liked on the base face: a lash line along the lids and darker lips."""
import sys, os, json, re, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from faces import makehuman

FOLDER = os.path.join(HERE, "candidates")
BASE = os.path.join(HERE, "women_base.json")
STEPS = (-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0)

# MakeHuman's, by category: the name the dev sees, the target's folder and stem, and its two ends (the
# first growing the feature; None for a one-way target, whose strengths below 0 are left blank).
MAKEHUMAN = {
    "mouth": [("cupid's bow deeper", "mouth", "mouth-cupidsbow", "incr", "decr"),
              ("cupid's bow wider", "mouth", "mouth-cupidsbow-width", "incr", "decr"),
              ("upper lip centre up", "mouth", "mouth-upperlip-middle", "up", "down"),
              ("lower lip centre up", "mouth", "mouth-lowerlip-middle", "up", "down"),
              ("upper lip ends up", "mouth", "mouth-upperlip-ext", "up", "down"),
              ("lower lip ends up", "mouth", "mouth-lowerlip-ext", "up", "down"),
              ("philtrum fuller", "mouth", "mouth-philtrum-volume", "incr", "decr"),
              ("dimples", "mouth", "mouth-dimples", "in", "out"),
              ("laugh lines", "mouth", "mouth-laugh-lines", "in", "out"),
              ("upper lip wider", "mouth", "mouth-upperlip-width", "incr", "decr"),
              ("lower lip wider", "mouth", "mouth-lowerlip-width", "incr", "decr")],
    "nose": [("hump", "nose", "nose-hump", "incr", "decr"),
             ("nostrils angled up", "nose", "nose-nostrils-angle", "up", "down"),
             ("nose base up", "nose", "nose-base", "up", "down"),
             ("lower bridge wider", "nose", "nose-width3", "incr", "decr"),
             ("nose compressed", "nose", "nose-compression", "compress", "uncompress")],
    "chin": [("chin prominent", "chin", "chin-prominent", "incr", "decr"),
             ("jaw forward", "chin", "chin-prognathism", "incr", "decr"),
             ("chin cleft", "chin", "chin-cleft", "incr", "decr"),
             ("chin pointed", "chin", "chin", "triangle", None)],
    "upper": [("cheeks fuller", "cheek", "cheek-volume", "incr", "decr"),
              ("cheeks higher", "cheek", "cheek-trans", "up", "down"),
              ("forehead taller", "forehead", "forehead-scale-vert", "incr", "decr"),
              ("forehead forward", "forehead", "forehead-trans", "forward", "backward"),
              ("brow ridge up", "eyebrows", "eyebrows-trans", "up", "down"),
              ("brow ridge forward", "eyebrows", "eyebrows-trans", "forward", "backward")],
}
EYES = ["eyes larger", "outer corners up", "eyes apart", "eyes higher", "eyes prominent"]
UNITS = dict(size=0.05, tilt=4.0, apart=0.0015, higher=0.0015, prominent=0.0015)   # scale, degrees, metres
EYE_FADE = (0.018, 0.034)                         # the eye moves wholly within the first radius, not past the second
# Where each category's pictures look (the face looks down -y), and how tall: the eyes close, the rest the
# whole face; forward of the head's middle, so that the profile is of the face.
FACE = ((0, -0.035, 1.605), 0.21)
FRAMES = dict(eyes=((0, -0.04, 1.625), 0.11), mouth=FACE, nose=FACE, chin=FACE, upper=FACE)
LASH, LASH_COLOUR, LIPS = (0.0018, 0.0009), (0.035, 0.025, 0.022), (0.42, 0.17, 0.15)


def key(category, name):
    return "%s/%s" % (category, re.sub(r"[^a-z]+", "-", name.lower()).strip("-"))


def _makehuman(fit, group, stem, way):
    if way is None:
        return 0.0
    if os.path.exists(os.path.join(makehuman.FOLDER, "targets", group, "%s-%s.target" % (stem, way))):
        return fit.carry(makehuman.target("%s/%s-%s" % (group, stem, way)))
    return sum(fit.carry(makehuman.target("%s/%s-%s-%s" % (group, s, stem, way))) for s in "lr")


def eye_moves(model, eye):
    """The eyes' features as movements of the model's vertices at strength 1: each eye, about its centre
    `eye` (on the +x side, mirrored onto the other), moved rigidly and faded out around it."""
    v = model.mean
    side = np.where(v[:, 0] < 0, -1.0, 1.0)
    f = np.column_stack([np.abs(v[:, 0]), v[:, 1:]])
    c = np.asarray(eye)
    t = np.clip((EYE_FADE[1] - np.linalg.norm(f - c, axis=1)) / (EYE_FADE[1] - EYE_FADE[0]), 0, 1)
    w = t * t * (3 - 2 * t)

    def moved(p):
        d = w[:, None] * (p - f)
        d[:, 0] *= side
        return d

    a = np.radians(UNITS["tilt"])
    x, z = f[:, 0] - c[0], f[:, 2] - c[2]
    tilted = np.column_stack([c[0] + x * np.cos(a) - z * np.sin(a), f[:, 1], c[2] + x * np.sin(a) + z * np.cos(a)])
    return dict(zip(EYES, [moved(c + (1 + UNITS["size"]) * (f - c)), moved(tilted),
                           moved(f + (UNITS["apart"], 0, 0)), moved(f + (0, 0, UNITS["higher"])),
                           moved(f + (0, UNITS["prominent"], 0))]))


def candidates(model, eye, categories=None):
    """{key: (category, name, one_way, movement (N, 3) of the model's vertices at strength 1)} for the
    categories named, or all."""
    fit, out = makehuman.Fit(model), {}
    for category in ["eyes"] + list(MAKEHUMAN):
        if categories and category not in categories:
            continue
        if category == "eyes":
            for name, d in eye_moves(model, eye).items():
                out[key(category, name)] = (category, name, False, d)
            continue
        for name, group, stem, more, less in MAKEHUMAN[category]:
            d = _makehuman(fit, group, stem, more)
            if less:
                d = 0.5 * (d - _makehuman(fit, group, stem, less))
            out[key(category, name)] = (category, name, less is None, d)
    return out


def render(categories):
    from faces import build_faces as bf
    model = bf.current()
    her = np.array(json.load(open(BASE))["numbers"])
    D = len(model.directions)
    lashed(bf, model)
    os.makedirs(FOLDER, exist_ok=True)
    index_path = os.path.join(FOLDER, "index.json")
    index = json.load(open(index_path)) if os.path.exists(index_path) else {}
    listed = {f["key"]: f for f in index.get("features", [])}
    base = model.directions
    for k, (category, name, one_way, d) in candidates(model, bf.EYE, categories).items():
        bf.TARGET, bf.SCALE = FRAMES[category]
        model.directions = np.concatenate([base, d[None].astype(base.dtype)])
        rows = []
        for view in (0.0, 90.0):
            tiles = []
            for s in STEPS:
                if one_way and s < 0:
                    tiles.append(np.zeros((bf.TILE[1], bf.TILE[0], 4), np.float32))
                    continue
                face = np.concatenate([her[:D], [s], her[D:]])
                tiles.append(bf.portrait(model, face, os.path.join(FOLDER, "tile.png"), view, 1.0, bf.WOMEN))
            rows.append(np.concatenate(tiles, axis=1))
        picture = k.replace("/", "_") + ".png"
        bf.save(os.path.join(FOLDER, picture), np.concatenate(rows[::-1], axis=0))
        listed[k] = dict(key=k, category=category, name=name, one_way=one_way, picture=picture,
                         largest_mm=round(1000 * float(np.linalg.norm(d, axis=1).max()), 2))
        print("CANDIDATE", k, flush=True)
    model.directions = base
    order = [key("eyes", n) for n in EYES] + [key(c, r[0]) for c, rows in MAKEHUMAN.items() for r in rows]
    with bf.whole(index_path) as part, open(part, "w", encoding="utf-8", newline="\n") as f:
        json.dump(dict(steps=STEPS, tile=list(bf.TILE), views=["front", "profile"],
                       features=sorted(listed.values(), key=lambda f: order.index(f["key"]))), f, indent=1)


def lashed(bf, model):
    """Gives build_faces' paint the lash line and the darker lips the dev liked on the base face."""
    plain, v = bf.paint, model.mean
    eyes = np.asarray(model.eyes) > 0.5
    folded = np.column_stack([np.abs(v[:, 0]), v[:, 1:]])
    near = np.where((~eyes) & (np.linalg.norm(folded - folded[eyes].mean(0), axis=1) < 0.025))[0]
    dist = np.full(len(v), np.inf)
    dist[near] = np.min(np.linalg.norm(v[near, None] - v[eyes][None], axis=-1), axis=1)
    above = v[:, 2] > bf.EYE[2] - 0.001
    lash = np.where(above, 0.9 * bf.ramp(1.0 - dist / LASH[0]), 0.45 * bf.ramp(1.0 - dist / LASH[1]))

    def paint(at, e):
        colour = plain(at, e)
        if len(at) == len(v):
            colour += lash[:, None] * (np.array(LASH_COLOUR) - colour)
        return colour
    bf.paint, bf.LIPS = paint, LIPS


if __name__ == "__main__":
    from sculpt.bl import opt
    only = opt("--only", "")
    render(only.split(",") if only else None)

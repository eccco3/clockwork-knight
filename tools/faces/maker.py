"""The face maker's session (dev/face_maker.gd): it reads the dev's requests on stdin and answers each with
one JSON line. It hangs the long hair's fall from each face he makes as the sheets hang it (hair.py), from
the head Godot shows (build_head.py); and it draws faces and saves them.

  python -I maker.py --sex women [--face a.json] [--saves assets/faces]

In, a JSON object a line: {"face": face} hangs the fall from that face; {"randomize": seed, or null}
draws a face as the first sheet of picks draws its faces about the base face (rounds.drawn), but at their
full spread; {"base": true} gives the base face, each kept candidate at his favourite; {"save": face} saves
a face. A face is its "numbers", 62 scan numbers, 22 features and 6 brow numbers, and the "strengths" of
the candidate features he keeps. Out, for each line in: the "face" if it is new and the "fall" hung from
it, as Godot's packed arrays (var_to_bytes, in base64): its "points", "normals", where each lies "across"
the strands (UV.x) and its triangles' "indices"; or the file the face was "saved" in. The first line out, before
any in, is the face to show, --face or the base face, its fall, and the "dials" in groups: each a "title"
and its "dials", each a "name", the "number" or "candidate" it moves and its "low" and "high".

A face is saved in the next free <sex>_<nnn>.json of --saves, assets/faces unless given: the face, its
"sex" and when it was "saved", for game characters to wear (scripts/face_head.gd).
"""
import argparse, base64, json, os, struct, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces import candidates, glb, hair, rounds
from faces.files import HERE, whole
from faces.model import Model, normals
from faces.sexes import SEXES, Sex

PROJECT = os.path.dirname(os.path.dirname(HERE))
SCANS = 8                                       # dials for the largest of the scan numbers
REACH = (4.0, 3.0)                              # how far the scan dials go either way of 0, and the others
# The dials' groups: each its title and the names of the numbers and candidates it holds, in order. A kept
# candidate none names shows in the last group.
GROUPS = (("Head", ["scan %d" % k for k in range(SCANS)] + ["forehead rounded", "temples full", "forehead taller"]),
          ("Brows", ["brows high", "brows arched", "brows slanted up", "brows thick", "brows long", "brows apart",
                     "brow ridge slanted up", "brow ridge up"]),
          ("Eyes", candidates.EYES),
          ("Nose", ["nose tip up", "septum low", "nostrils flared", "nostrils wide", "bridge wide", "nose tip wide",
                    "nose convex", "nose root full", "hump", "lower bridge wider", "nose base up", "nose compressed",
                    "nostrils angled up"]),
          ("Mouth", ["upper lip full", "lower lip full", "upper lip tall", "lower lip tall", "mouth wide",
                     "mouth corners up", "upper lip centre up", "upper lip ends up", "upper lip wider",
                     "lower lip centre up", "lower lip ends up", "lower lip wider", "dimples", "laugh lines"]),
          ("Cheeks and jaw", ["cheekbones", "cheeks full", "cheeks higher", "chin wide", "jaw wide", "jaw corners low"]))
PACKED = dict(int32=30, vector2=35, vector3=36)   # the Variant types of Godot's packed arrays


def packed(array, kind):
    """An array as Godot's var_to_bytes writes a packed array of `kind`, in base64."""
    data = np.ascontiguousarray(array, np.int32 if kind == "int32" else np.float32)
    count = data.size if kind == "int32" else len(data)
    return base64.b64encode(struct.pack("<II", PACKED[kind], count) + data.tobytes()).decode("ascii")


class Head:
    """The head Godot shows a sex's faces on (build_head.py): where its vertices lie at rest and how fast its
    blend shapes move them, in Godot's frame, and its extras."""

    def __init__(self, path):
        gltf, accessor = glb.read(path)
        node = next(n for n in gltf["nodes"] if n["name"] == "head")
        primitive = gltf["meshes"][node["mesh"]]["primitives"][0]
        self.extras = node["extras"]
        self.rest = accessor(primitive["attributes"]["POSITION"]).astype(float)
        self.rates = np.stack([accessor(t["POSITION"]) for t in primitive["targets"]])
        self.origin, self.axes = (np.array(self.extras["frame"][k]) for k in ("origin", "axes"))

    def weights(self, face):
        """The blend shapes' weights that show a face: how far each number is from rest."""
        rest, keys = self.extras["rest"], self.extras["candidates"]
        shapes = len(self.rates) - len(keys)
        return np.concatenate([np.subtract(face["numbers"][:shapes], rest["numbers"][:shapes]),
                               [face["strengths"][k] - rest["strengths"][k] for k in keys]])

    def fall(self, face):
        """The fall hung from a face, in Godot's frame, wound as Godot winds a front: None in short hair."""
        if not self.extras["fall"]:
            return None
        v = (self.rest + np.tensordot(self.weights(face), self.rates, axes=1) - self.origin) @ self.axes.T
        pts, quads, across = hair.sheet(v, **self.extras["fall"])
        return dict(points=packed(self.origin + pts @ self.axes, "vector3"),
                    normals=packed(normals(pts, quads) @ self.axes, "vector3"),
                    across=packed(np.column_stack([across, np.zeros(len(across))]), "vector2"),
                    indices=packed(glb.triangles(quads)[:, ::-1], "int32"))


class Maker:
    """A sex's faces: the head Godot shows them on, the base face and the candidate features he keeps."""

    def __init__(self, sex, saves):
        self.model = Model.load(os.path.join(HERE, "model.npz"))
        self.sex, self.saves = Sex(self.model, sex), saves
        self.head = Head(os.path.join(PROJECT, "assets", "models", "head_%s.glb" % sex))
        self.kept = candidates.kept(rounds.answers_path(sex))
        if sorted(self.kept) != self.head.extras["candidates"]:
            sys.exit("head_%s.glb carries other candidate features than he keeps: build it again (build_head.py)" % sex)
        self.base = dict(numbers=rounds.load(rounds.base_path(sex))["numbers"],
                         strengths={k: favourite for k, (_, favourite, _) in self.kept.items()})

    def opened(self, path):
        """The face saved at `path`: numbers it was saved without are zero, candidates at his favourites."""
        face = rounds.load(path)
        numbers = np.pad(np.asarray(face["numbers"], float), (0, len(self.base["numbers"]) - len(face["numbers"])))
        return dict(numbers=numbers.tolist(), strengths=self.base["strengths"] | {
            k: v for k, v in face.get("strengths", {}).items() if k in self.kept})

    def drawn(self, seed):
        """A face drawn about the base face at the full spread of the picks' sheets (r = 1)."""
        rng = np.random.default_rng(seed)
        numbers = rounds.drawn(self.sex, np.asarray(self.base["numbers"]), rounds.scales(self.model), rng, 1)[0]
        return dict(numbers=np.round(numbers, 5).tolist(), strengths={
            k: round(rounds.strength(low, favourite, high, rng), 5) for k, (low, favourite, high) in self.kept.items()})

    def dials(self):
        scans, names = len(self.model.share), candidates.names()
        dials = {name: dict(name=name, number=i, low=-REACH[i >= scans], high=REACH[i >= scans])
                 for i, name in enumerate(rounds.labels(self.model))}
        dials |= {names[k]: dict(name=names[k], candidate=k, low=low, high=high) for k, (low, _, high) in self.kept.items()}
        groups = [dict(title=title, dials=[dials.pop(name) for name in members if name in dials])
                  for title, members in GROUPS]
        groups[-1]["dials"] += [d for d in dials.values() if "candidate" in d]
        return groups

    def save(self, face):
        """Saves a face in the next free file, which it returns, from the project if it is in it."""
        os.makedirs(self.saves, exist_ok=True)
        k = 1
        while os.path.exists(os.path.join(self.saves, "%s_%03d.json" % (self.sex.name, k))):
            k += 1
        path = os.path.join(self.saves, "%s_%03d.json" % (self.sex.name, k))
        with whole(path) as part, open(part, "w", encoding="utf-8", newline="\n") as f:
            json.dump(dict(sex=self.sex.name, numbers=face["numbers"], strengths=face["strengths"],
                           saved=time.strftime("%Y-%m-%dT%H:%M:%S")), f, indent=1)
        inside = os.path.relpath(path, PROJECT)
        return (path if inside.startswith("..") else inside).replace(os.sep, "/")

    def answer(self, said):
        if "save" in said:
            return dict(saved=self.save(said["save"]))
        face = said.get("face") or (self.drawn(said["randomize"]) if "randomize" in said else self.base)
        return dict(fall=self.head.fall(face)) | ({} if "face" in said else dict(face=face))


def say(reply):
    print(json.dumps(reply), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sex", choices=SEXES, required=True)
    ap.add_argument("--face")
    ap.add_argument("--saves", default=os.path.join(PROJECT, "assets", "faces"))
    a = ap.parse_args()
    maker = Maker(a.sex, os.path.abspath(a.saves))
    face = maker.opened(a.face) if a.face else maker.base
    say(dict(face=face, fall=maker.head.fall(face), dials=maker.dials()))
    for line in sys.stdin:
        if line.strip():
            say(maker.answer(json.loads(line)))


if __name__ == "__main__":
    main()

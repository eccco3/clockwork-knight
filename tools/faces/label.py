"""The labelling session dev/labels.tscn shows: it reads the dev's labels on stdin and writes the next face.

  python -I label.py [--labels a.jsonl]

In: a label for the face shown, one of sexes.KINDS, or "undo". Out: {"face"}, the picture of the next face
to label, "" once the whole label set is labelled; how many are "labelled" of the "target" and of the
"faces" there are; and how many have each label. Every label is saved before the next face is sent, and a
session starts at the first face not labelled yet.
"""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from faces.files import folder, picture, rendered
from faces.sexes import KINDS, LABELS, Labels

TARGET = 100


def unlabelled(labels, count):
    done = {line["face"] for line in labels.lines}
    return next((i for i in range(count) if i not in done), None)


def show(labels, face, faces):
    print(json.dumps(dict(face="" if face is None else picture(face, folder("labels")), labelled=len(labels),
                          target=TARGET, faces=len(faces), **labels.counts())), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", default=LABELS)
    a = ap.parse_args()
    faces = rendered(folder("labels"))[0]
    labels = Labels(a.labels)
    face = unlabelled(labels, len(faces))
    show(labels, face, faces)
    shown = time.monotonic()
    for line in sys.stdin:
        said = line.strip()
        if said in KINDS:
            if face is not None:
                labels.label(face, faces[face], said, time.monotonic() - shown)
                face = unlabelled(labels, len(faces))
        elif said == "undo":
            taken = labels.undo()
            face = taken["face"] if taken else face
        else:
            continue
        show(labels, face, faces)
        shown = time.monotonic()


main()

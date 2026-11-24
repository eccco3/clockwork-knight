"""What the face tools and the dev exchange: sets of faces rendered for him to judge, and his answers on
them, one JSON line each, written the moment he gives it."""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def folder(name):
    """Where build_faces.py renders the set of faces of that name: a sex's pool, or the faces to label."""
    return os.path.join(HERE, "pool", name)


def picture(i, folder):
    return os.path.join(folder, "%03d.png" % i)


def rendered(folder):
    """The rendered set's coefficients (F, K), the model's share of the variance per component, and the
    spread the faces were drawn at."""
    with np.load(os.path.join(folder, "pool.npz")) as f:
        return f["faces"], f["share"], float(f["spread"])


class Log:
    def __init__(self, path):
        self.path = path
        self.lines = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                self.lines = [json.loads(line) for line in f if line.strip()]

    def __len__(self):
        return len(self.lines)

    def add(self, line):
        self.lines.append(line)
        with open(self.path, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(line, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def undo(self):
        """Takes back the last answer and returns it, or None."""
        if not self.lines:
            return None
        line = self.lines.pop()
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(json.dumps(line, separators=(",", ":")) + "\n" for line in self.lines)
        return line

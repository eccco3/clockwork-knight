"""How broad a face is where breadth reads as a man's: across the jaw's corners, the cheekbones, the cheeks
below them and the head above the ears, each the widest the face is within a box of the mean head, and the
jaw's width for the cheekbones'. A face's vertices are linear in its numbers, so measuring takes only the
few vertices that could be widest, without building the face.
"""
import numpy as np

# Each box's heights (z) and depths (y) on the mean head, in metres, in the head frame (model.py).
BOXES = dict(jaw=((-0.115, -0.095), (0.0, 0.05)), cheekbones=((-0.035, 0.0), (0.02, 0.06)),
             cheeks=((-0.07, -0.05), (0.03, 0.065)), head=((0.04, 0.08), (-0.08, 0.04)))
NAMES = list(BOXES) + ["jaw for cheekbones"]
NEAR = 0.006                                   # only vertices this close to a box's widest on the mean can be widest


class Widths:
    def __init__(self, model):
        v, self.rows = model.mean, []
        for (z0, z1), (y0, y1) in BOXES.values():
            inside = (v[:, 0] > 0) & (z0 <= v[:, 2]) & (v[:, 2] <= z1) & (y0 <= v[:, 1]) & (v[:, 1] <= y1)
            near = np.flatnonzero(inside & (v[:, 0] >= v[inside, 0].max() - NEAR))
            self.rows.append((v[near, 0], model.directions[:, near, 0]))

    def __call__(self, faces):
        """The widths (F, len(NAMES)) of faces' numbers (F, n), in metres but for the last, a ratio."""
        w = [2 * (x + np.asarray(faces)[:, :len(d)] @ d).max(1) for x, d in self.rows]
        return np.stack(w + [w[0] / w[1]], 1)

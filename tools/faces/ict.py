"""The registered heads the face model is learnt from: ICT-FaceKit's light model (MIT licence).

It is a generic head and 100 identity modes, the principal components of light stage scans registered to
one topology, each scaled to one standard deviation. tools/fetch_assets.ps1 downloads it. Of its geometry
this keeps the skin and the eyeballs, closed into shells, in the head frame the figures sculpt in: origin
on the midline at the height of the eyes, +y out of the face, +z up, metres.
"""
import os
import numpy as np
from sculpt import scan

FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads", "ict_facekit")
MODES = 100
SKIN = (0, 11248)                              # vertex ranges of the kit's geometry: face, head and neck
EYEBALLS = ((21451, 23021), (23021, 24591))
SCLERA = 770                                   # the first vertices of an eyeball: its white, a sphere
NOSE_TIP = 4857                                # the kit's landmarks: the nose, and along the inner edges of the lips
LIPS = ((5702, 5702), (5711, 5966), (5533, 5517), (6216, 6470), (6207, 6207))  # upper and lower, corner to corner
METRE = 0.01
EYE_Y = 0.0515                                 # the centres of the eyeballs stand this far before the origin
AXES = np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, 1.0, 0.0]]) * METRE


def _read(name):
    """An OBJ's vertices and, as lists of vertex indices, its polygons."""
    v, faces = [], []
    with open(os.path.join(FOLDER, name + ".obj")) as f:
        for line in f:
            if line.startswith("v "):
                v.append(line.split()[1:4])
            elif line.startswith("f "):
                faces.append([int(corner.split("/")[0]) - 1 for corner in line.split()[1:]])
    return np.array(v, dtype=np.float64), faces


def _sphere(p):
    """Centre of the sphere through points, by least squares."""
    A = np.concatenate([2.0 * p, np.ones((len(p), 1))], axis=1)
    return np.linalg.lstsq(A, (p * p).sum(1), rcond=None)[0][:3]


class Heads:
    """mean (N, 3) and modes (MODES, N, 3): a head is the mean plus the modes weighted by unit normal numbers.
    skin and eyeballs: the closed shells of triangles over those vertices. On the mean, eye is the centre of
    the eyeball on +x, nose the tip of the nose and parting the line the lips meet on, from corner to corner."""

    def __init__(self):
        raw, faces = _read("generic_neutral_mesh")
        keep = np.concatenate([np.arange(*r) for r in (SKIN,) + EYEBALLS])
        index = np.full(len(raw), -1)
        index[keep] = np.arange(len(keep))
        kept = [index[f].tolist() for f in faces if (index[f] >= 0).all()]
        skin = SKIN[1] - SKIN[0]
        self.skin, loops = scan.closed([f for f in kept if f[0] < skin], len(keep))
        self.eyeballs, more = scan.closed([f for f in kept if f[0] >= skin], len(keep) + len(loops))
        loops += more

        eye = _sphere(raw[EYEBALLS[0][0]:EYEBALLS[0][0] + SCLERA])
        origin = np.array([0.0, eye[1], eye[2] - EYE_Y / METRE])
        self.mean = scan.centred((raw[keep] - origin) @ AXES.T, loops)
        self.modes = np.stack([scan.centred((_read("identity%03d" % k)[0][keep] - raw[keep]) @ AXES.T, loops)
                               for k in range(MODES)])
        self.eye = (eye - origin) @ AXES.T * np.array([-1.0, 1.0, 1.0])
        self.nose = self.mean[index[NOSE_TIP]]
        self.parting = self.mean[index[np.array(LIPS)]].mean(1)

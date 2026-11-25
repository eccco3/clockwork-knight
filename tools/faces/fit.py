"""Fits registered heads onto the sculpt toolkit's head topology and learns the face model there.

The mean head, cut off at the neck and its lips sealed, is wrapped by the mesher as a figure's head is,
with edge loops where the eyeballs show between the lids. Each vertex of that lattice is bound to the place
on the mean's surface it landed on, so it follows that place through every mode. The modes, made symmetric
and so carried over, give the model's components by PCA.
"""
import numpy as np
from sculpt import sdf as S, mesher, scan
from sculpt.sdf import V
from .model import Model, mirrored, components, twins

AXIS = (V(0, -0.012, 0.045), V(0, -0.012, -0.105))
EXTENT = (0.085, 0.105, 0.150)
RES = (96, 76, 120)                            # lattice at full detail: across the face, front to back, up
NECK = -0.150                                  # the head is cut off level, this far below the eyes
NECK_ROUND = 0.004
BROW, CHIN = 0.045, -0.125                     # the face, which gets the finer quads, lies between these heights
REACH = 0.170                                  # no part of the head is further from the axis
FORWARD = 0.6                                  # the lattice starts out drawn this far toward the face, to be finer there
SEAL = 0.0012                                  # radius of the bead that closes the lips along their parting
SEAL_Y = -0.0005                               # and how far before the parting its middle runs
LID_NORMAL = 5e-4                              # the edge loop on a lid is shaded as the lid this far from its edge


def dims(detail):
    return tuple(2 * max(4, round(r * detail / 2)) for r in RES)


def density(heads):
    """Mesh density weight: finer quads over the face, finest over the eyes, the nose and the mouth."""
    def weight(p):
        x, z = np.abs(p[:, 0]), p[:, 2]
        face = np.clip((p[:, 1] - 0.030) / 0.030, 0, 1) * np.clip((BROW - z) / 0.015, 0, 1) * np.clip((z - CHIN) / 0.015, 0, 1)
        eye = np.exp(-((x - heads.eye[0]) ** 2 + (z - heads.eye[2]) ** 2) / (2 * 0.019 ** 2))
        mouth = np.exp(-((x / 0.034) ** 2 + ((z - heads.parting[:, 2].mean()) / 0.013) ** 2))
        nose = np.exp(-(x ** 2 + (z - heads.nose[2]) ** 2) / (2 * 0.013 ** 2))
        return 1.0 + face * (5.0 + 14.0 * eye + 12.0 * mouth + 14.0 * nose)
    return weight



def fit(heads, detail=1.0):
    """The face model of `heads` (see ict.Heads) on a lattice of the given detail."""
    n = dims(detail)
    solid = scan.Solid(heads.mean, heads.skin + heads.eyeballs)
    skin, eyeballs = scan.Solid(heads.mean, heads.skin), scan.Solid(heads.mean, heads.eyeballs)
    bead = heads.parting + V(0, SEAL_Y, 0)

    def field(p):
        return S.smax(np.minimum(solid.field(p), S.tube(p, bead, SEAL)), NECK - p[:, 2], NECK_ROUND)

    def lids(p):
        return np.abs(eyeballs.field(p)) - np.abs(skin.field(p))

    def onto_eyeballs(p):
        return p - S.gradient(eyeballs.field, p) * eyeballs.field(p)[:, None]

    def forward(unit):
        return S.normalize(unit + V(0, FORWARD, 0))
    v, quads, _ = mesher.wrap(field, *AXIS, EXTENT, n, relax=14, tmax=REACH, density=density(heads),
                              snap=[(lids, onto_eyeballs, LID_NORMAL)], warp=forward)
    lat = np.rint((mesher.cube_lattice(*n)[0] + 1.0) / 2.0 * np.array(n)).astype(np.int64)
    corners, weights = solid.bind(v)
    modes, share = components(scan.carry(mirrored(heads.modes, twins(heads.mean)), corners, weights))
    return Model(v, modes, share, quads, lat)

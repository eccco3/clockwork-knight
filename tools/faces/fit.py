"""Fits registered heads onto the sculpt toolkit's head topology and learns the face model there.

The mean head, cut off at the neck and its lips sealed a little behind their parting, is wrapped by the
mesher as a figure's head is: rings held along the lips as Rosalyn's are, edge loops where the eyeballs show
between the lids, closed a little short of the corners where the lids meet, and round the neck's cut, and the
undercuts its rays cannot see, behind the ears' rims and in the nostrils, bridged. The vertices between the
lids are the model's eyes. Each vertex of that lattice is bound to the place on the mean's surface it landed
on, so it follows that place through every mode, but for the cap closing the neck's cut: that is no part of
the heads, and follows the edge loop round it. The modes, made symmetric and so carried over, give the
model's components; what making them symmetric left out gives its asymmetries.

How the components and the asymmetries mix the modes is kept in basis.json: PCA found the mixes on the
first lattice, and every lattice since carries the same mixes over, so that a face's coefficients keep
their meaning and the dev's answers stay valid. Without the file PCA finds them again, on this lattice.
"""
import json, os
import numpy as np
from sculpt import sdf as S, lattice, mesher, scan
from sculpt.mesher import Rail
from sculpt.num import smoothstep
from sculpt.sdf import V
from .model import Model, mirrored, principal, twins

VERSION = 2                                    # a model fitted by another version of this is fitted again
BASIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "basis.json")
AXIS = (V(0, -0.012, 0.045), V(0, -0.012, -0.105))
EXTENT = (0.085, 0.105, 0.150)
RES = (96, 76, 120)                            # lattice at full detail: across the face, front to back, up
NECK = -0.150                                  # the head is cut off level, this far below the eyes
NECK_ROUND = 0.004
BROW, CHIN = 0.045, -0.125                     # the face, which gets the finer quads, lies between these heights
REACH = 0.170                                  # no part of the head is further from the axis
FORWARD = 0.6                                  # the lattice starts out drawn this far toward the face, to be finer there
SLOPE = 2.5                                    # the steepest an undercut the rays cannot see is bridged at,
NOSTRILS = (0.012, -0.022, -0.010), 0.005, 5.0 # but steeper about these places from the nose's tip (on +x), so they stay open
LID_CLOSE, LID_CORNER = 0.0006, 0.0025         # the eye's opening is closed by up to this much this near its corners,
                                               # so that its edge loops end before it narrows to a crack
SEAL = (0.0012, 0.004)                         # half height and depth of the slab that closes the lips behind their parting,
SEAL_BACK = 0.0003                             # its front this far behind it: the bottom of the groove between them
LIP_RING = 0.21                                # the parting's ring, as a share of the lattice's height
LIP_STAND = 0.00015                            # how far each lip's edge loop stands beyond the gap between the lips
LIP_GAP = 0.0022                               # spacing the three loops open to beyond the corners,
LIP_BACK = -0.128                              # and the height they come round to at the back of the head
LID_NORMAL = 5e-4                              # the edge loop on a lid is shaded as the lid this far from its edge
ASYMMETRIES = 12                               # the model keeps this many of the ways the faces' halves differ,
FACE_FROM, FACE_ABOVE = (-0.02, 0.03), (-0.135, -0.105)   # none behind the first y or below the first z, all past the second


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


def slope(heads):
    """The steepest an undercut is bridged at: SLOPE, and steeper in the nostrils."""
    at, reach, steep = NOSTRILS

    def steepest(p):
        near = np.exp(-((S.mirror_x(p) - heads.nose - V(*at)) ** 2).sum(-1) / (2 * reach ** 2))
        return SLOPE + (steep - SLOPE) * near
    return steepest


def corners(heads, opening, onto_eyeballs):
    """The inner and outer corners of the eye's opening on +x: where the eyeball shows nearest to the midline and
    furthest from it."""
    up, across = np.meshgrid(np.linspace(-0.6, 0.6, 121), np.linspace(-1.4, 1.4, 281))
    look = np.stack([np.cos(up) * np.sin(across), np.cos(up) * np.cos(across), np.sin(up)], -1).reshape(-1, 3)
    p = onto_eyeballs(heads.eye + 0.013 * look)
    p = p[opening(p) < 0.0]
    return p[[np.argmin(p[:, 0]), np.argmax(p[:, 0])]]


def _round(p):
    """Angle round the meshing axis from straight ahead, on either side."""
    return np.arctan2(np.abs(p[:, 0]), p[:, 1] - AXIS[0][1])


def rails(heads, n):
    """Three neighbouring rings held along the lips, as Rosalyn's are: the lower lip's edge, the groove
    between the lips and the upper lip's edge. Past the corners they open out and run on round the head."""
    half = heads.lips[len(heads.lips) // 2:]                   # from the middle out to a corner
    th, z = _round(half.mean(1)), half.mean(1)[:, 2]
    gap = 0.5 * (half[:, 0, 2] - half[:, 1, 2])

    def line(p):
        a = _round(p)
        return np.where(a < th[-1], np.interp(a, th, z), z[-1] + (LIP_BACK - z[-1]) * smoothstep(th[-1], np.pi, a))

    def edge(side):
        def g(p):
            a = _round(p)
            stand = np.interp(a, th, gap) + LIP_STAND + LIP_GAP * smoothstep(th[-1], th[-1] + 0.09, a)
            return side * (p[:, 2] - line(p)) - stand
        return g
    ring = round(LIP_RING * n[2])
    return [Rail(ring - 1, edge(-1.0)), Rail(ring, lambda p: p[:, 2] - line(p)), Rail(ring + 1, edge(1.0))]


def fit(heads, detail=1.0):
    """The face model of `heads` (see ict.Heads) on a lattice of the given detail."""
    n = dims(detail)
    solid = scan.Solid(heads.mean, heads.skin + heads.eyeballs)
    skin, eyeballs = scan.Solid(heads.mean, heads.skin), scan.Solid(heads.mean, heads.eyeballs)
    squash = V(1.0, SEAL[0] / SEAL[1], 1.0)
    seal = (heads.parting - V(0, SEAL_BACK + SEAL[1], 0)) * squash

    def field(p):
        return S.smax(np.minimum(solid.field(p), S.tube(p * squash, seal, SEAL[0])), NECK - p[:, 2], NECK_ROUND)

    def opening(p):
        return np.abs(eyeballs.field(p)) - np.abs(skin.field(p))

    def onto_eyeballs(p):
        return p - S.gradient(eyeballs.field, p) * eyeballs.field(p)[:, None]
    ends = corners(heads, opening, onto_eyeballs)

    def lids(p):
        near = np.linalg.norm(S.mirror_x(p)[:, None] - ends[None], axis=-1)
        return opening(p) + LID_CLOSE * (np.clip(1.0 - near / LID_CORNER, 0.0, 1.0) ** 2).sum(1)

    def rim(p):
        """Height above the neck's cut, which near the surface grows only along it, so that the loop slides
        down the neck onto it however steeply the rays meet the neck there."""
        return p[:, 2] - (NECK + NECK_ROUND) - S.gradient(field, p)[:, 2] * field(p)

    def forward(unit):
        return S.normalize(unit + V(0, FORWARD, 0))
    v, quads, _ = mesher.wrap(field, *AXIS, EXTENT, n, relax=14, tmax=REACH, density=density(heads),
                              snap=[(lids, onto_eyeballs, LID_NORMAL), (rim, None, LID_NORMAL)],
                              rails=rails(heads, n), warp=forward, slope=slope(heads))
    lat = np.rint((mesher.cube_lattice(*n)[0] + 1.0) / 2.0 * np.array(n)).astype(np.int64)
    even, odd = halves(heads, solid, v, quads)
    odd = fair(odd, v)
    share, mix, lop = basis(even, odd)
    return Model(v, np.tensordot(mix, even, axes=1), share, quads, lat, np.tensordot(lop, odd, axes=1), fitted=VERSION,
                 eyes=lids(v) < 0.0)


def cap(mean):
    """Which vertices of the lattice, on the mean, lie on the cap closing the neck's cut, below the edge loop
    round it."""
    return mean[:, 2] < NECK + NECK_ROUND


def halves(heads, solid, mean, quads):
    """The heads' modes as movements of the model's vertices: their symmetric parts, and what those leave out."""
    even = mirrored(heads.modes, twins(heads.mean))
    corners, weights = solid.bind(mean)
    return [stretched(scan.carry(modes, corners, weights), mean, quads) for modes in (even, heads.modes - even)]


def stretched(moves, mean, quads):
    """Movements (M, N, 3) of the lattice's vertices with the cap's, which the heads do not hold, taken from
    the edge loop round it: each an average of the loop's, weighted by the inverse square of how far."""
    under = cap(mean)
    a, b = lattice.edges_of(quads).T
    loop = np.unique(np.where(under[a], b, a)[under[a] != under[b]])
    weight = 1.0 / ((mean[under][:, None] - mean[loop][None]) ** 2).sum(-1)
    moves = moves.copy()
    moves[:, under] = np.einsum("cl,mlk->mck", weight / weight.sum(1, keepdims=True), moves[:, loop])
    return moves


def fair(odd, mean):
    """The modes' asymmetric parts (M, N, 3) without the shift and turn of the whole head each holds, which is
    the sitter's pose, and faded out toward the back of the head and the neck, where a figure's body meets it."""
    face = smoothstep(*FACE_FROM, mean[:, 1]) * smoothstep(*FACE_ABOVE, mean[:, 2])
    rigid = np.stack([np.tile(V(1, 0, 0), (len(mean), 1)), np.cross(V(0, 1, 0), mean), np.cross(V(0, 0, 1), mean)])
    held = np.linalg.lstsq((rigid * face[:, None]).reshape(3, -1).T, (odd * face[:, None]).reshape(len(odd), -1).T, rcond=None)[0]
    return (odd - np.tensordot(held.T, rigid, axes=1)) * face[:, None]


def basis(even, odd):
    """The share of the variance each component explains, and how the components and the asymmetries mix the
    modes: from basis.json, or found by PCA on the modes' symmetric and fair asymmetric parts and kept there."""
    if not os.path.exists(BASIS):
        mix, share = principal(even)
        keep(share, mix, principal(odd)[0][:ASYMMETRIES])
    with open(BASIS, encoding="utf-8") as f:
        kept = json.load(f)
    return np.array(kept["share"]), np.array(kept["components"]), np.array(kept["asymmetries"])


def keep(share, mix, lop):
    """Writes basis.json: the shares exactly, so that what depends on them is unchanged, and a mix to a row."""
    def rows(m):
        return ",\n".join("  [%s]" % ", ".join("%.10g" % x for x in r) for r in m)
    with open(BASIS, "w", encoding="utf-8", newline="\n") as f:
        f.write('{"share": [%s],\n"components": [\n%s],\n"asymmetries": [\n%s]}\n'
                % (", ".join(repr(float(s)) for s in share), rows(mix), rows(lop)))

"""Lacquered lip pieces, set on the face without carved lips (head.py's inlaid face) over the dark socket cut where
her mouth opens.

SHAPES are five mouths, closed to round. Each is carved whole as an upper and a lower lip, for the game to swap
in turn as a stop-motion puppet's replacement mouths are swapped. The same shapes are struck by four pieces on
pivots: the lips as they rest, each turning about a line just behind the corners of her mouth, so that they part
most in the middle (the lower's line runs at the height of its middle, so that it tips rather than sinking into
her chin), and a plug in each end of the socket that turns in round the face to narrow the opening.
`poses` gives each piece's move in each shape.

Head frame, as head.py's. The lips are head.lips as they rest, each filled out to an outline that runs along the
parting to the end of the socket, and cut apart on the parting, so that closed they hide the socket.
"""
import numpy as np
from sculpt import sdf as S, lattice
from sculpt.sdf import V
from . import head

SHAPES = {                                     # metres: the lower lip's middle down, the upper's up, how far out from the
    "rest": dict(drop=0.0, rise=0.0, reach=0.020, ahead=0.0, jaw=0.0),          # middle the lips part, how far
    "ee": dict(drop=0.0014, rise=0.0004, reach=0.019, ahead=-0.0002, jaw=1.0),  # forward they come; and how many
    "ah": dict(drop=0.0046, rise=0.0012, reach=0.017, ahead=0.0, jaw=3.5),      # degrees a jaw opens for the shape
    "oh": dict(drop=0.0034, rise=0.0016, reach=0.0095, ahead=0.0016, jaw=2.5),  # in the face that keeps its lips
    "oo": dict(drop=0.0016, rise=0.0009, reach=0.0055, ahead=0.0026, jaw=1.2),
}
OUTLINES = {                                   # each lip's height off the parting in the middle; how far across it keeps
    "upper": (0.0100, 0.0168, 3.4, 0.0200),    # most of it, and how sharply it falls beyond; and where it ends, at the
    "lower": (0.0142, 0.0152, 6.7, 0.0195),    # end of the socket. Metres
}
STAND = 0.0004                                 # within its outline a lip stands at least this far out of the face
SUNK = 0.0032                                  # and is cut off this far inside it
GAP = 0.00025                                  # each lip stands this far off the parting
PLUG = V(0.0070, 0.0024, 0.0030)               # half sizes of a corner's plug: along the mouth, deep, high
PLUG_AT = 0.0200                               # where its middle rests across (her right), at the socket's end
PLUG_SET = 0.0016                              # how far its front stands back from the face
CELLS = (36, 8, 6)                             # a lip's lattice at full detail: along it, up, deep
MIRROR = np.diag([-1.0, 1.0, 1.0, 1.0])


def _front_map():
    """How far forward the bare face stands at each (x, z) of the mouth, x mirrored: a grid, and its axes."""
    xs, zs, ys = np.linspace(0.0, 0.032, 65), np.linspace(-0.088, -0.042, 93), np.linspace(0.100, 0.060, 401)
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    out = np.empty(X.shape)
    for i in range(len(xs)):
        p = np.stack([np.repeat(X[i], len(ys)), np.tile(ys, len(zs)), np.repeat(Z[i], len(ys))], axis=1)
        d = head.bare(p).reshape(len(zs), len(ys))
        k = np.maximum(np.argmax(d < 0, axis=1), 1)
        a, b = d[np.arange(len(zs)), k - 1], d[np.arange(len(zs)), k]
        out[i] = ys[k - 1] + (ys[k] - ys[k - 1]) * a / (a - b)
    return out, xs, zs


_FRONT = _front_map()


def front(x, z):
    """How far forward the bare face stands at (x, z)."""
    grid, xs, zs = _FRONT
    u = np.clip((np.abs(x) - xs[0]) / (xs[1] - xs[0]), 0, len(xs) - 1.001)
    v = np.clip((z - zs[0]) / (zs[1] - zs[0]), 0, len(zs) - 1.001)
    i, j = u.astype(int), v.astype(int)
    u, v = u - i, v - j
    return (grid[i, j] * (1 - u) * (1 - v) + grid[i + 1, j] * u * (1 - v) + grid[i, j + 1] * (1 - u) * v
            + grid[i + 1, j + 1] * u * v)


def line(p):
    """Height of the parting at each point's place across the mouth."""
    return head._lip_line(head._round(S.mirror_x(p))[0])


def _outline(p, side):
    """A lip's outline as seen from the front, on the parting's `side` (1 above): < 0 within it, roughly metres."""
    high, keep, sharp, end = OUTLINES["upper" if side > 0 else "lower"]
    x = np.abs(p[:, 0])
    h = high * np.exp(-(x / keep) ** sharp) * np.clip(1.0 - (x / end) ** 4, 0.0, 1.0)
    off = side * (p[:, 2] - line(p))
    return np.maximum(GAP - off, off - h)


def resting(p):
    """The two lips as they rest, cut apart on the parting: upper and lower. Each is head.lips where that stands
    out of the face, and elsewhere in its outline a sheet standing STAND out of it, all cut off SUNK inside it."""
    surface = front(p[:, 0], p[:, 2])
    within = surface - SUNK - p[:, 1]
    sheet = np.maximum(p[:, 1] - surface - STAND, within)
    return tuple(S.smax(S.smax(S.smin(lip, sheet, 0.0010), within, 0.0004), _outline(p, side), 0.0004)
                 for lip, side in zip(head.lips(p), (1.0, -1.0)))


def _parted(x, reach):
    """How far each point across the mouth parts, from 1 in the middle to 0 at `reach`, rounding off."""
    u = np.clip(x / reach, -1.0, 1.0)
    return (1.0 - u * u) ** 2


def carved(shape):
    """The shape's two lips carved whole, as fields: upper and lower. The rest lips are bent apart in the middle and
    brought forward, the middle most."""
    k = SHAPES[shape]

    def back(p, by):
        part = _parted(p[:, 0], k["reach"])
        ahead = k["ahead"] * (1.0 - 0.5 * np.minimum((p[:, 0] / 0.024) ** 2, 1.0))
        return np.stack([p[:, 0], p[:, 1] - ahead, p[:, 2] - by * part], axis=1)

    return (lambda p: resting(back(p, k["rise"]))[0]), (lambda p: resting(back(p, -k["drop"]))[1])


def _corner():
    """Where the corners of her mouth are: on the face where the parting meets the end of the socket, her right."""
    y = 0.080
    for _ in range(4):
        x = np.tan(head.SOCKET[2]) * (y - head.AXIS_Y)
        z = line(np.array([[x, y, head.MZ]]))[0]
        y = front(np.array([x]), np.array([z]))[0]
    return V(x, y, z)


def _middle():
    """The front of the lower lip's edge, in the middle of the parting."""
    ys = np.linspace(0.100, 0.070, 601)
    d = resting(np.stack([np.zeros(len(ys)), ys, np.full(len(ys), head.MZ - head.BOW - 2 * GAP)], axis=1))[1]
    return V(0.0, ys[np.argmax(d < 0)], head.MZ - head.BOW)


CORNER = _corner()
HINGES = {                                     # each lip turns about x through here, just behind the corners, so that
    "upper": V(0.0, CORNER[1] - 0.006, CORNER[2]),   # it parts most in the middle without turning far; the lower
    "lower": V(0.0, CORNER[1] - 0.006, -0.0670),     # at the height of its own middle, so its face stays out of the chin
}
MIDDLE = _middle()


def _seat(x):
    """Where a plug's middle lies when it is across at `x` on her right, and its angle round the axis."""
    z = line(np.array([[x, 0.08, head.MZ]]))[0]
    y = front(np.array([x]), np.array([z]))[0]
    th = np.arctan2(x, y - head.AXIS_Y)
    r = np.hypot(x, y - head.AXIS_Y) - PLUG_SET - PLUG[1]
    return V(r * np.sin(th), head.AXIS_Y + r * np.cos(th), z), th


_PLUG_AT, _PLUG_TH = _seat(PLUG_AT)


def plug(p):
    """Her right corner's plug as it rests: a lozenge along the parting in the end of the socket, behind the lips."""
    return S.ellipsoid(p, _PLUG_AT, PLUG, S.rot_z(-_PLUG_TH))


def _turn(at, degrees):
    """A turn about the head's x through `at`, as a 4x4: positive lifts what lies before it."""
    m = np.eye(4)
    m[:3, :3] = S.rot_x(np.radians(degrees))
    m[:3, 3] = at - m[:3, :3] @ at
    return m


def _shift(d):
    m = np.eye(4)
    m[:3, 3] = d
    return m


def _lowering(hinge, by):
    """How many degrees to turn about `hinge` to lower the middle of the parting `by` (to raise it, if negative)."""
    dy, dz = (MIDDLE - hinge)[1:]
    r, start = np.hypot(dy, dz), np.arctan2(dz, dy)
    return np.degrees(np.arcsin(np.clip((dz - by) / r, -1.0, 1.0)) - start)


def poses():
    """Each shape as the pivots strike it: shape -> piece -> 4x4 move from rest, in the head frame. The lips turn on
    their hinges to part as far in the middle as the carved shape, and come as far forward; the plugs turn in round
    the face along the parting, behind it, so that the opening ends about where the carved shape's does."""
    out = {}
    for shape, k in SHAPES.items():
        ahead = _shift(V(0, k["ahead"], 0))
        move = {"upper": ahead @ _turn(HINGES["upper"], _lowering(HINGES["upper"], -k["rise"])),
                "lower": ahead @ _turn(HINGES["lower"], _lowering(HINGES["lower"], k["drop"]))}
        at, th = _seat(min(PLUG_AT, 0.75 * k["reach"] + PLUG[0] * np.cos(_PLUG_TH)))
        right = np.eye(4)
        right[:3, :3] = S.rot_z(_PLUG_TH - th)
        right[:3, 3] = at - right[:3, :3] @ _PLUG_AT
        move["corner_r"], move["corner_l"] = right, MIRROR @ right @ MIRROR
        out[shape] = move
    return out


def _sections(f, ends, n=17):
    """Sections across a piece from one end to the other: the middle of each, and its half height and depth."""
    ys, zs = np.linspace(0.060, 0.096, 145), np.linspace(-0.088, -0.044, 177)
    Y, Z = np.meshgrid(ys, zs)
    Y, Z = Y.ravel(), Z.ravel()
    mids, high, deep = [], [], []
    for x in np.linspace(ends[0], ends[1], n):
        inside = f(np.stack([np.full(Y.size, x), Y, Z], axis=1)) < 0
        if inside.sum() < 2:
            continue
        y, z = Y[inside], Z[inside]
        mids.append(V(x, 0.5 * (y.min() + y.max()), 0.5 * (z.min() + z.max())))
        high.append(0.5 * (z.max() - z.min()))
        deep.append(0.5 * (y.max() - y.min()))
    return np.array(mids), np.array(high), np.array(deep)


def mesh(f, ends, detail=1.0):
    """A piece's quad mesh, a box of lattice laid along it, as high and deep as each section, and shrunk onto `f`:
    verts, quads and normals."""
    n = [max(2, round(c * detail)) for c in CELLS]
    path, high, deep = _sections(f, ends)
    box = lattice.Box((0, 0, 0), tuple(n), 0, path, high, deep, V(0, 0, 1), V(0, 1, 0), cap=(0.6, 0.6))
    v, q, nrm, _ = lattice.fit(f, [box], relax=20)
    return v, q, nrm


def _reach(f, side):
    """How far across a field reaches, to `side` (1 her right, -1 her left in the head frame)."""
    ys, zs = np.linspace(0.060, 0.096, 37), np.linspace(-0.088, -0.044, 45)
    Y, Z = np.meshgrid(ys, zs)
    last = 0.0
    for x in np.linspace(0.0, side * 0.032, 161):
        if (f(np.stack([np.full(Y.size, x), Y.ravel(), Z.ravel()], axis=1)) < 0).any():
            last = x
    return last


def pieces(detail=1.0):
    """Every lip piece, in the head frame: name -> (verts, quads, normals). `<shape>_upper` and `<shape>_lower` are
    the carved shapes; `upper`, `lower`, `corner_l` and `corner_r` the pivots' pieces, as they rest."""
    out = {}
    for shape in SHAPES:
        for name, f in zip(("upper", "lower"), carved(shape)):
            out["%s_%s" % (shape, name)] = mesh(f, (_reach(f, -1.0) * 0.985, _reach(f, 1.0) * 0.985), detail)
    out["upper"], out["lower"] = out["rest_upper"], out["rest_lower"]
    along = PLUG[0] * 0.92 * np.cos(_PLUG_TH)
    v, q, nrm = mesh(plug, (_PLUG_AT[0] - along, _PLUG_AT[0] + along), detail * 0.4)
    out["corner_r"] = (v, q, nrm)
    out["corner_l"] = (v * V(-1, 1, 1), q[:, ::-1], nrm * V(-1, 1, 1))
    return out

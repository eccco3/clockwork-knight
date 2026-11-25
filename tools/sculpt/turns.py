"""Rotations for posing a figure, as 3x3 matrices in its axes: +X its left, -Y forward, +Z up. Angles are degrees."""
import numpy as np
from . import sdf as S
from .sdf import V

MIRROR = V(-1, 1, 1)
FLIP = np.diag(MIRROR)
X, Y, Z, SAME = V(1, 0, 0), V(0, 1, 0), V(0, 0, 1), np.eye(3)


def turn(axis, degrees):
    x, y, z = S.normalize(np.asarray(axis, dtype=np.float64))
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    a = np.radians(degrees)
    return SAME + np.sin(a) * k + (1.0 - np.cos(a)) * (k @ k)


def lean(pitch, roll, yaw):
    """Bowed forward, leant left and turned left, in degrees."""
    return turn(Z, yaw) @ turn(Y, roll) @ turn(X, pitch)


def part(r, share):
    """The rotation `r` carried only `share` of the way from rest."""
    angle = np.arccos(np.clip((np.trace(r) - 1.0) / 2.0, -1.0, 1.0))
    if angle < 1e-9:
        return SAME
    axis = V(r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1])
    return turn(axis, np.degrees(angle) * share)


def between(a, b):
    """The shortest turn that takes direction `a` to direction `b`."""
    a, b = S.normalize(a), S.normalize(b)
    axis = np.cross(a, b)
    if np.linalg.norm(axis) < 1e-9:
        return SAME
    return turn(axis, np.degrees(np.arctan2(np.linalg.norm(axis), a @ b)))


def twist(r, axis):
    """The degrees `r` turns about `axis`, once what tips the axis over is taken out."""
    axis = S.normalize(axis)
    spin = between(r @ axis, axis) @ r
    side = S.normalize(np.cross(axis, X if abs(axis @ X) < 0.9 else Y))
    return np.degrees(np.arctan2(np.cross(side, spin @ side) @ axis, side @ spin @ side))


def shared(first, last, axis, n):
    """`n` rotations that share out, in like steps, the twist about `axis` by which `last` differs from `first`:
    the first is `first`, and the last has turned as far round the axis as `last`."""
    whole = twist(first.T @ last, axis)
    return [first @ turn(axis, whole * k / (n - 1)) for k in range(n)]


def hinged(along, hinge):
    """The frame of a bone that points `along` and bends about `hinge`."""
    return np.stack([hinge, np.cross(along, hinge), along], axis=1)


def reach(root, target, a, b, pole):
    """A limb of two bones, `a` and `b` long, from `root` toward `target`, its middle joint bent toward `pole`:
    the way each bone points, the hinge between them, and how far the target lies beyond its reach."""
    span = np.linalg.norm(target - root)
    d = np.clip(span, abs(a - b) + 1e-4, a + b - 1e-4)
    u = (target - root) / span
    v = S.normalize(pole - u * (pole @ u))
    bend = (a * a + d * d - b * b) / (2 * a * d)
    middle = a * (bend * u + np.sqrt(1.0 - bend * bend) * v)
    upper, lower = S.normalize(middle), S.normalize(d * u - middle)
    return upper, lower, S.normalize(np.cross(upper, lower)), span - d

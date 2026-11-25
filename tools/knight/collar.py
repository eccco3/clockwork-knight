"""How far the knight's collar bones carry her shoulders.

The clips swing a collar bone as much as 29 degrees. Forward, out and up, that brings her shoulder round her
chest as her arm reaches across her body, and the clips keep it. Back, in and down, it draws the shoulder as much
as 6 cm into her chest: a living shoulder slides there under its muscle, but hers is a wooden arm in a wooden
socket and would sink in. `settle` holds each shoulder within about SINK of its socket those ways. Where her upper
arm would still pass through her body, it carries the shoulder on forward and out, as a reaching shoulder goes,
just far enough to clear it, coming and going over EASE frames. Either way it bends the arm at the shoulder and
elbow so that the wrist stays where the clip put it and the hand turns as it did; only a wrist the arm can no
longer reach falls short, along the line it would have reached.

Lengths are metres and angles radians."""
import math

import numpy as np
from mathutils import Matrix, Quaternion, Vector

from knight.clips import Channel, Posed, eased

SINK = 0.004                       # how far a shoulder is drawn back, in and down at most; a little way is barely held
FURTHEST, STEP = math.radians(24), math.radians(1)     # the most a shoulder is carried on to clear her, and the steps tried
SLACK = 0.001                      # how much deeper than the clearest a shoulder that cannot clear her may stay, carried less
EASE = 4.0                         # frames over which that comes and goes
STRAIGHTEST = 0.999                # of the arm's full length, the furthest a wrist is reached for
ARM = ("clavicle", "upperarm", "lowerarm", "hand")


def _rotation(m):
    return m.to_3x3().normalized().to_quaternion()


class _Side:
    """One side's arm, as its bones lie at rest, and the points of its upper arm that must keep out of her body."""

    def __init__(self, arm, side, points):
        self.side = side
        self.bones = [arm.pose.bones[n + "_" + side] for n in ARM]
        rest = [pb.bone.matrix_local for pb in self.bones]
        seen = rest[0].inverted()
        self.shoulder = seen @ rest[1].translation                 # as the collar bone sees it at rest
        self.outward = math.copysign(1.0, rest[1].translation.x)
        self.ways = [seen.to_3x3() @ Vector(way) for way in ((self.outward, 0, 0), (0, 0, 1), (0, -1, 0))]
        self.offsets = [_rotation(a.inverted() @ b) for a, b in zip(rest, rest[1:])]
        self.points = np.c_[points, np.ones(len(points))] @ np.array(rest[1].inverted()).T     # as the upper arm sees them
        self.spread = np.linalg.norm(self.points[:, :3] - self.points[:, :3].mean(axis=0), axis=1).max()

    def held(self, turn):
        """The collar bone's turn, with the shoulder kept from going far back, in or down."""
        moved = turn @ self.shoulder - self.shoulder
        sunk = sum((way * min(moved.dot(way), 0.0) for way in self.ways), Vector())
        if sunk.length < 1e-7:
            return turn
        kept = moved - sunk + sunk * (SINK * math.tanh(sunk.length / SINK) / sunk.length)
        there = (self.shoulder + kept).normalized() * self.shoulder.length
        swing = self.shoulder.rotation_difference(turn @ self.shoulder)
        return self.shoulder.rotation_difference(there) @ swing.inverted() @ turn

    def settled(self, turn, swing):
        """The four bones' turns, and the upper arm's matrix, in the pose now set, once the collar bone's `turn` is
        held and then swung on forward and out by `swing`."""
        turn = turn if turn.w >= 0.0 else -turn
        collar, upper, lower, hand = (pb.matrix.copy() for pb in self.bones)
        now = collar @ (turn.inverted() @ self.held(turn)).to_matrix().to_4x4()
        if swing:
            body = self.bones[0].parent
            up = body.matrix.to_3x3() @ body.bone.matrix_local.to_3x3().inverted() @ Vector((0.0, 0.0, 1.0))
            pivot = now.translation.copy()
            now = Matrix.Translation(pivot) @ Matrix.Rotation(-self.outward * swing, 4, up) @ Matrix.Translation(-pivot) @ now
        shoulder, elbow, wrist = upper.translation, lower.translation, hand.translation
        start = (now @ collar.inverted() @ upper).translation
        l1, l2 = (elbow - shoulder).length, (wrist - elbow).length
        to = wrist - start
        reach = min(max(to.length, abs(l1 - l2) + 1e-3), (l1 + l2) * STRAIGHTEST)
        back, out = shoulder - elbow, wrist - elbow
        hinge = back.cross(out)
        opened = math.acos(max(-1.0, min(1.0, (l1 * l1 + l2 * l2 - reach * reach) / (2.0 * l1 * l2))))
        bend = Quaternion() if hinge.length < 1e-9 else Quaternion(hinge.normalized(), opened - back.angle(out))
        aim = ((elbow - shoulder) + bend @ out).rotation_difference(to)
        upper_turn = aim @ _rotation(upper)
        lower_turn = aim @ bend @ _rotation(lower)
        cu, ul, lh = self.offsets
        turns = (turn @ _rotation(collar.inverted() @ now), (_rotation(now) @ cu).inverted() @ upper_turn,
                 (upper_turn @ ul).inverted() @ lower_turn, (lower_turn @ lh).inverted() @ _rotation(hand))
        return turns, Matrix.Translation(start) @ upper_turn.to_matrix().to_4x4()

    def depth(self, upper, seen):
        """How deep the upper arm, posed at `upper`, goes into the bodies: `seen` holds each body's sculpt and the
        matrix that takes the pose now set back to its rest."""
        reach, deepest = np.array(upper), -math.inf
        for field, back in seen:
            p = self.points @ (back @ reach)[:3].T
            if field(p.mean(axis=0)[None])[0] < 1.25 * self.spread:       # else all of it is well clear
                deepest = max(deepest, -field(p).min())
        return deepest

    def swing(self, turn, seen):
        """The least swing on, a STEP at a time, that clears the bodies, or else comes within SLACK of the clearest."""
        swings, deep = np.arange(0.0, FURTHEST + 1e-9, STEP), []
        for swing in swings:
            deep.append(self.depth(self.settled(turn, swing)[1], seen))
            if deep[-1] <= 0.0:
                return swing
        return swings[np.argmax(np.array(deep) <= min(deep) + SLACK)]


def settle(arm, action, points, bodies):
    """Holds and carries both shoulders in every key of an action, keeping the wrists. `points` are each side's
    upper arm's vertices at rest, those its socket does not hold, and `bodies` the sculpts at rest they keep out of,
    by the bone that carries each."""
    sides = [_Side(arm, side, points[side]) for side in "lr"]
    keys = {(n, s.side): Channel(action, n + "_" + s.side, "rotation_quaternion") for n in ARM for s in sides}
    first = keys["clavicle", "l"]
    frames = np.array([first.frame(k) for k in range(first.count())])
    rests = {bone: np.array(arm.data.bones[bone].matrix_local) for bone in bodies}
    needed = np.zeros((len(sides), len(frames)))
    with Posed(arm, action) as posed:
        for k, frame in enumerate(frames):
            posed.at(frame)
            seen = [(field, rests[bone] @ np.linalg.inv(np.array(arm.pose.bones[bone].matrix))) for bone, field in bodies.items()]
            for i, s in enumerate(sides):
                needed[i, k] = s.swing(Quaternion(keys["clavicle", s.side].get(k)), seen)
        swings = [eased(frames, need, EASE) for need in needed]
        found = {}
        for k, frame in enumerate(frames):
            posed.at(frame)
            for i, s in enumerate(sides):
                found[s.side, k] = s.settled(Quaternion(keys["clavicle", s.side].get(k)), swings[i][k])[0]
    for (side, k), turns in sorted(found.items(), key=lambda item: item[0][1]):
        for n, turn in zip(ARM, turns):
            channel = keys[n, side]
            if k > 0 and turn.dot(Quaternion(channel.get(k - 1))) < 0.0:
                turn.negate()
            channel.set(k, turn)
    for curve in action.fcurves:
        curve.update()

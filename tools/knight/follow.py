"""How a guard floats over a joint: the knight's pauldron over her shoulder.

A guard's bone lies on its limb's at rest and has the same parent, so both turn about the joint. The guard turns
the way the limb has turned from rest: half as far, or further where the limb would otherwise come within CLEAR
of it. `bake` keys that into the clips, so the game works nothing out.

Lengths are metres and angles radians."""
import numpy as np

STEP = np.radians(1.5)             # between the angles tried
CLEAR = 0.003                      # air kept between a guard and its limb


class Guard:
    def __init__(self, bone, limb, solid, points):
        """`solid` is a sculpt of the `limb` bone's pieces and `points` are the vertices of the guard's, both at rest."""
        self.bone, self.limb, self.solid, self.points = bone, limb, solid, points


def _about(axis, angles):
    """Turns about a unit axis: matrices (n, 3, 3)."""
    x, y, z = axis
    cross = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angles)[:, None, None] * cross + (1.0 - np.cos(angles))[:, None, None] * (cross @ cross)


def _lag(guard, rest, axis, turn):
    """How far behind its limb the guard stays, when the limb has turned by `turn` about `axis` as its own bone
    sees it: half the turn, or as much of that as keeps the limb clear all the way there."""
    angles = np.linspace(0.0, 0.5 * turn, 2 + int(0.5 * turn / STEP))
    spun = _about(rest[:3, :3] @ axis, -angles)                # the guard as the limb sees it, the limb back at rest
    seen = (guard.points - rest[:3, 3]) @ spun.transpose(0, 2, 1) + rest[:3, 3]
    met = guard.solid(seen.reshape(-1, 3)).reshape(len(angles), -1).min(axis=1) < CLEAR
    return angles[max(np.argmax(met) - 1, 0)] if met.any() else angles[-1]


def bake(arm, clips, guards, pose):
    """Keys every guard's turn into each of the `clips`, actions by name. `pose(arm, clip, frame)` puts the rig in a frame."""
    rests = {g.bone: np.array(arm.data.bones[g.limb].matrix_local) for g in guards}
    for name, action in clips.items():
        first, last = (int(f) for f in action.frame_range)
        frames = list(range(first, last + 1))
        keys = {g.bone: [] for g in guards}
        for frame in frames:
            pose(arm, name, frame)
            for g in guards:
                q = np.array(arm.pose.bones[g.limb].rotation_quaternion)
                q = q if q[0] >= 0.0 else -q
                sine = np.linalg.norm(q[1:])
                turn = 2.0 * np.arctan2(sine, q[0])
                axis = q[1:] / sine if sine > 1e-9 else np.array([1.0, 0.0, 0.0])
                half = 0.5 * (turn - _lag(g, rests[g.bone], axis, turn))
                keys[g.bone].append(np.concatenate([[np.cos(half)], np.sin(half) * axis]))
        for g in guards:
            path = 'pose.bones["%s"].rotation_quaternion' % g.bone
            for index, values in enumerate(np.array(keys[g.bone]).T):
                curve = action.fcurves.new(path, index=index, action_group=g.bone)
                curve.keyframe_points.add(len(frames))
                curve.keyframe_points.foreach_set("co", np.stack([frames, values], axis=1).ravel())
                for point in curve.keyframe_points:
                    point.interpolation = "LINEAR"
                curve.update()

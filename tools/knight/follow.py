"""How a guard floats over a joint: the knight's pauldron over her shoulder.

A guard's bone lies on its limb's at rest and has the same parent, so both turn about the joint. The guard turns
the way the limb has turned from rest, half as far, or further where the limb would otherwise come within CLEAR
of it. Where it would then come within CLEAR of the body under it, or closer than it rests, it rides up off it
as far as it must, short of meeting the limb, its lift coming and going over EASE frames. Where it cannot clear
both, it rides to where it goes least far into either. `bake` keys that into the clips, so the game works
nothing out.

Lengths are metres and angles radians."""
import numpy as np

from knight.clips import add, eased

STEP = np.radians(1.5)             # between the angles tried
CLEAR = 0.003                      # air kept between a guard and its limb, or the body under it
RISE, HIGHEST = 0.001, 0.040       # between the lifts tried, and the most a guard rides up
EASE = 3.0                         # frames


class Guard:
    def __init__(self, bone, limb, solid, points, body, onto, lift):
        """`solid` is a sculpt of the `limb` bone's pieces and `points` are the vertices of the guard's; `body` is a
        sculpt of what the `onto` bone carries under the guard, and `lift` the way the guard rides up off it, all at rest."""
        self.bone, self.limb, self.solid, self.points = bone, limb, solid, points
        self.body, self.onto, self.lift = body, onto, np.asarray(lift) / np.linalg.norm(lift)
        self.air = min(CLEAR, body(points).min())        # what it keeps from the body: as at rest, where it lies closer


def _about(axis, angles):
    """Turns about a unit axis: matrices (n, 3, 3)."""
    x, y, z = axis
    cross = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angles)[:, None, None] * cross + (1.0 - np.cos(angles))[:, None, None] * (cross @ cross)


def _lag(guard, rest, axis, turn):
    """How far behind its limb the guard stays, when the limb has turned by `turn` about `axis` as its own bone
    sees it: half the turn, or as much of that as keeps the limb clear all the way there. Also the guard's
    vertices as the limb sees them then, the limb back at rest."""
    angles = np.linspace(0.0, 0.5 * turn, 2 + int(0.5 * turn / STEP))
    spun = _about(rest[:3, :3] @ axis, -angles)
    seen = (guard.points - rest[:3, 3]) @ spun.transpose(0, 2, 1) + rest[:3, 3]
    met = guard.solid(seen.reshape(-1, 3)).reshape(len(angles), -1).min(axis=1) < CLEAR
    k = max(np.argmax(met) - 1, 0) if met.any() else len(angles) - 1
    return angles[k], seen[k]


def _rise(guard, held, seen, way):
    """How far the guard rides up `way`, as the body sees it. `held` are its vertices as its limb sees them, and
    `seen` takes what the limb sees to what the body sees."""
    on = held @ seen[:3, :3].T + seen[:3, 3]
    if guard.body(on).min() >= guard.air:
        return 0.0
    rises = np.arange(RISE, HIGHEST + 1e-9, RISE)[:, None, None]
    body = guard.body((on + rises * way).reshape(-1, 3)).reshape(len(rises), -1).min(axis=1) - guard.air
    limb = guard.solid((held + rises * (way @ seen[:3, :3])).reshape(-1, 3)).reshape(len(rises), -1).min(axis=1) - CLEAR
    short = np.minimum(body, limb)
    clear = np.flatnonzero(short >= 0.0)
    return rises[clear[0] if len(clear) else np.argmax(short), 0, 0]


def bake(arm, clips, guards, pose):
    """Keys every guard's turn and lift into each of the `clips`, actions by name. `pose(arm, clip, frame)` puts the
    rig in a frame."""
    bones = arm.data.bones
    rest = lambda name: np.array(bones[name].matrix_local)
    for name, action in clips.items():
        first, last = (int(f) for f in action.frame_range)
        frames = np.arange(first, last + 1)
        turns, rises = {g.bone: [] for g in guards}, {g.bone: [] for g in guards}
        for frame in frames:
            pose(arm, name, frame)
            for g in guards:
                q = np.array(arm.pose.bones[g.limb].rotation_quaternion)
                q = q if q[0] >= 0.0 else -q
                sine = np.linalg.norm(q[1:])
                turn = 2.0 * np.arctan2(sine, q[0])
                axis = q[1:] / sine if sine > 1e-9 else np.array([1.0, 0.0, 0.0])
                lag, held = _lag(g, rest(g.limb), axis, turn)
                half = 0.5 * (turn - lag)
                turns[g.bone].append(np.concatenate([[np.cos(half)], np.sin(half) * axis]))
                under = rest(g.onto) @ np.linalg.inv(np.array(arm.pose.bones[g.onto].matrix))   # the pose now set, as the body rests
                seen = under @ np.array(arm.pose.bones[g.limb].matrix) @ np.linalg.inv(rest(g.limb))
                parent = bones[g.bone].parent.name
                way = under[:3, :3] @ np.array(arm.pose.bones[parent].matrix)[:3, :3] @ rest(parent)[:3, :3].T @ g.lift
                rises[g.bone].append(_rise(g, held, seen, way))
        for g in guards:
            lifted = eased(frames, rises[g.bone], EASE)[:, None] * (rest(g.bone)[:3, :3].T @ g.lift)
            add(action, g.bone, "rotation_quaternion", frames, turns[g.bone])
            add(action, g.bone, "location", frames, lifted)

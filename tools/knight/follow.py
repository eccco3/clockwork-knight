"""How a guard floats over a joint: the knight's pauldron over her shoulder.

A guard's bone lies on its limb's at rest. It hangs from a riser, a bone far from it whose parent is the limb's,
so both turn about the joint. The guard turns the way the limb has turned from rest, half as far, or further where
the limb would otherwise come within CLEAR of it. Where it would then come within CLEAR of the body under it, or
closer than it rests, the riser turns about its x and carries it up off the body as far as it must, short of
meeting the limb, coming and going over EASE frames; where it cannot clear both, as far as leaves it least far
into either. Only turns move it, as they move the rest of her, and `bake` keys them into the clips, so the game
works nothing out.

Lengths are metres and angles radians."""
import numpy as np

from knight.clips import add, eased

STEP = np.radians(1.5)             # between the angles tried
CLEAR = 0.003                      # air kept between a guard and its limb, or the body under it
RISE, HIGHEST = 0.001, 0.040       # how far up its joint is carried between the lifts tried, and at most
EASE = 3.0                         # frames


class Guard:
    def __init__(self, bone, limb, solid, points, body, onto):
        """`solid` is a sculpt of the `limb` bone's pieces and `points` are the vertices of the guard's; `body` is a
        sculpt of what the `onto` bone carries under the guard, all at rest."""
        self.bone, self.limb, self.solid, self.points, self.body, self.onto = bone, limb, solid, points, body, onto
        self.air = min(CLEAR, body(points).min())        # what it keeps from the body: as at rest, where it lies closer


def _about(axis, angles):
    """Turns about a unit axis: matrices (n, 3, 3)."""
    x, y, z = axis
    cross = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    return np.eye(3) + np.sin(angles)[:, None, None] * cross + (1.0 - np.cos(angles))[:, None, None] * (cross @ cross)


def _spun(points, pivot, turns):
    """`points` turned about `pivot` by each of `turns`, all of them in a row: (n * len(points), 3)."""
    return ((points - pivot) @ turns.transpose(0, 2, 1) + pivot).reshape(-1, 3)


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


def _rise(guard, held, seen, riser, angles):
    """How far the riser turns, of `angles`. `held` are the guard's vertices as its limb sees them, `seen` takes
    what the limb sees to what the body sees, and `riser` is the riser's matrix, unturned, as the body sees it."""
    on = held @ seen[:3, :3].T + seen[:3, 3]
    if guard.body(on).min() >= guard.air:
        return 0.0
    axis = riser[:3, 0] / np.linalg.norm(riser[:3, 0])
    body = guard.body(_spun(on, riser[:3, 3], _about(axis, angles))).reshape(len(angles), -1).min(axis=1) - guard.air
    back = np.linalg.inv(seen)
    pivot = back[:3, :3] @ riser[:3, 3] + back[:3, 3]
    limb = guard.solid(_spun(held, pivot, _about(back[:3, :3] @ axis, angles))).reshape(len(angles), -1).min(axis=1)
    short = np.minimum(body, limb - CLEAR)
    clear = np.flatnonzero(short >= 0.0)
    return angles[clear[0] if len(clear) else np.argmax(short)]


def bake(arm, clips, guards, pose):
    """Keys every guard's turn, and its riser's, into each of the `clips`, actions by name. `pose(arm, clip, frame)`
    puts the rig in a frame."""
    bones = arm.data.bones
    rest = lambda name: np.array(bones[name].matrix_local)
    posed = lambda name: np.array(arm.pose.bones[name].matrix)
    risers = {g.bone: bones[g.bone].parent.name for g in guards}
    lifts = {g.bone: np.arange(RISE, HIGHEST + 1e-9, RISE) / np.linalg.norm(bones[g.bone].head_local - bones[risers[g.bone]].head_local)
             for g in guards}
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
                under = rest(g.onto) @ np.linalg.inv(posed(g.onto))         # the pose now set, as the body rests
                seen = under @ posed(g.limb) @ np.linalg.inv(rest(g.limb))
                rises[g.bone].append(_rise(g, held, seen, under @ posed(risers[g.bone]), lifts[g.bone]))
        for g in guards:
            half = 0.5 * eased(frames, rises[g.bone], EASE)
            add(action, g.bone, "rotation_quaternion", frames, turns[g.bone])
            add(action, risers[g.bone], "rotation_quaternion", frames, np.stack([np.cos(half), np.sin(half), 0.0 * half, 0.0 * half], axis=1))

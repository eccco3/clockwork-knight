"""How what hangs from the knight's belt moves: skirt plates and the panels of a tabard.

Each is a `Hinge`, a bone that turns about its own x, which lies along the thing's top edge; its y runs down
the thing and its z faces out of it. A hinge is sprung in against her legs: in every frame of every clip it
turns in from fully out until it meets a leg or her body, or its swing ends. It is pushed out at once, kicked
on by a leg that leaves it, and falls back as a damped spring. `bake` keys that into the clips, so nothing is
simulated in the game. Gravity is left out: what hangs keeps to her pelvis, upside down too.

Lengths are metres and angles radians, positive out. Everything is worked out as the pelvis sees it."""
import bpy
import numpy as np
from mathutils import Matrix
from sculpt.num import smoothstep

STEP = np.radians(1.5)             # between the angles tried
CLEAR = 0.006                      # air kept between a hinge and what it rests on
TUCKS = np.radians((60, 125))      # a thigh swung this far forward starts to draw a hinge in under her, and draws it fully
STIFF, DAMP = 18.0, 0.6            # the spring's rate in radians a second, and its damping ratio
KICK = 0.5                         # how much of a leg's speed a hinge keeps as the leg leaves it
SUBSTEPS = 4
STRIPS = 8                         # a hinge's inner face is taken strip by strip across it


class Hinge:
    def __init__(self, bone, points, swing, parent=None, tuck=0.0, thighs="lr"):
        """`points` are the vertices at rest of what the bone carries. `swing` (in, out) is measured from its
        parent hinge, or from rest. Its angle from rest, summed down the chain, never goes below zero, less
        `tuck` once the rearmost of `thighs` (sides) has swung forward."""
        self.bone, self.points, self.swing = bone, points, swing
        self.parent, self.tuck, self.thighs = parent, tuck, thighs


def spheres(verts, cell=0.04):
    """Spheres that together hold `verts`, one round each cell of a grid `cell` across that has any: centres (n, 3) and radii."""
    _, cells = np.unique(np.floor(verts / cell).astype(int), axis=0, return_inverse=True)
    parts = [verts[cells.ravel() == k] for k in range(cells.max() + 1)]
    centres = np.array([0.5 * (part.min(0) + part.max(0)) for part in parts])
    return centres, np.array([np.linalg.norm(part - c, axis=1).max() for part, c in zip(parts, centres)])


def _turn(angle):
    return np.array(Matrix.Rotation(angle, 4, "X"))


def _place(points, matrix):
    return points @ matrix[:3, :3].T + matrix[:3, 3]


class _Flat:
    """What a hinge carries, as its bone sees it at rest: how far it reaches down and across, how far in its inner
    face lies in each strip across it, and a few of its points below its top quarter."""

    def __init__(self, points):
        x, y, z = points.T
        self.reach, self.across = y.max(), (x.min(), x.max())
        strip = self.strip(x)
        self.inner = np.array([z[strip == k].min() if (strip == k).any() else z.min() for k in range(STRIPS)])
        lower = points[y > 0.25 * self.reach]
        self.some = lower[::max(len(lower) // 60, 1)]

    def strip(self, x):
        return np.clip(((x - self.across[0]) / (self.across[1] - self.across[0]) * STRIPS).astype(int), 0, STRIPS - 1)


class _Solver:
    def __init__(self, arm, hinges, legs, body):
        self.arm, self.hinges, self.legs, self.body = arm, hinges, legs, body
        rest = {b.name: np.array(b.matrix_local) for b in arm.data.bones}
        self.unrest = {name: np.linalg.inv(m) for name, m in rest.items()}
        self.offset = {h.bone: (self.unrest[h.parent.bone] if h.parent else np.eye(4)) @ rest[h.bone] for h in hinges}
        self.flats = {h.bone: _Flat(_place(h.points, self.unrest[h.bone])) for h in hinges}
        self.thighs = {s: rest["calf_" + s][:3, 3] - rest["thigh_" + s][:3, 3] for s in "lr"}

    def pose(self):
        """Her legs as the pelvis sees them now: every sphere's centre and radius, and how far each thigh is swung forward."""
        seen = np.linalg.inv(np.array(self.arm.pose.bones["pelvis"].matrix) @ self.unrest["pelvis"])
        moved = {bone: seen @ np.array(self.arm.pose.bones[bone].matrix) @ self.unrest[bone] for bone in self.legs}
        centres = np.concatenate([_place(c, moved[bone]) for bone, (c, _) in self.legs.items()])
        radii = np.concatenate([r for _, r in self.legs.values()])
        flex = {}
        for s, thigh in self.thighs.items():
            now = moved["thigh_" + s][:3, :3] @ thigh
            flex[s] = np.arctan2(-now[1], -now[2])
        return centres, radii, flex

    def rest_angle(self, h, frame, lo, summed, centres, radii):
        """The furthest in that hinge `h` turns from fully out before it meets anything. Unturned, its bone is at
        `frame` and has turned `summed` from rest. A sphere is met while any of it is outside the hinge's inner
        face, within the hinge's reach."""
        flat = self.flats[h.bone]
        angles = np.linspace(h.swing[1], lo, 2 + int((h.swing[1] - lo) / STEP))
        q = (centres - frame[:3, 3]) @ frame[:3, :3]
        near = np.linalg.norm(q, axis=1) < flat.reach + 2.0 * radii
        q, r = q[near], radii[near]
        cos, sin = np.cos(angles)[:, None], np.sin(angles)[:, None]
        down = q[:, 1] * cos + q[:, 2] * sin
        out = -q[:, 1] * sin + q[:, 2] * cos - flat.inner[flat.strip(q[:, 0])]
        beside = (q[:, 0] > flat.across[0] - 0.7 * r) & (q[:, 0] < flat.across[1] + 0.7 * r)
        met = ((out > -r - CLEAR) & (down > -0.5 * r) & (down < flat.reach + 0.5 * r) & beside).any(axis=1)
        for k in np.flatnonzero(~met & (summed + angles < 0.0)):       # her body is only in the way of what turns in
            met[k] = (self.body(_place(flat.some, frame @ _turn(angles[k]))) < CLEAR).any()
        stopped = np.flatnonzero(met)
        return angles[max(stopped[0] - 1, 0)] if len(stopped) else angles[-1]

    def step(self, state, dt):
        """Moves every hinge on by `dt` seconds in the rig's present pose. `state` holds each bone's angle, speed and rest."""
        centres, radii, flex = self.pose()
        frames, total = {}, {}
        for h in self.hinges:
            above = frames[h.parent.bone] if h.parent else np.eye(4)
            summed = total[h.parent.bone] if h.parent else 0.0
            frame = above @ self.offset[h.bone]
            floor = -h.tuck * smoothstep(*TUCKS, min(flex[s] for s in h.thighs))
            lo = min(max(h.swing[0], floor - summed), h.swing[1])
            rest = self.rest_angle(h, frame, lo, summed, centres, radii)
            angle, speed, was = state.get(h.bone, (rest, 0.0, rest))
            for _ in range(SUBSTEPS):
                speed += (STIFF * STIFF * (rest - angle) - 2.0 * DAMP * STIFF * speed) * dt / SUBSTEPS
                angle += speed * dt / SUBSTEPS
            if angle <= rest:
                angle, speed = rest, max(speed, KICK * (rest - was) / dt) if dt else 0.0
            if angle >= h.swing[1]:
                angle, speed = h.swing[1], 0.0
            state[h.bone] = (angle, speed, rest)
            frames[h.bone] = frame @ _turn(angle)
            total[h.bone] = summed + angle


def bake(arm, clips, hinges, legs, pose, body):
    """Keys every hinge's turn into each of the `clips`, actions by name. `hinges` lists parents before their
    children. `legs` maps a leg bone to the (centres, radii) of the spheres on it at rest; `body` is a sculpt of
    what else a hinge must not turn in through. `pose(arm, clip, frame)` puts the rig in a frame."""
    solver = _Solver(arm, hinges, legs, body)
    fps = bpy.context.scene.render.fps
    for name, action in clips.items():
        first, last = (int(f) for f in action.frame_range)
        frames = list(range(first, last + 1))
        loops = name.endswith("_Loop")
        state, keys = {}, {}
        for lap in range(2 if loops else 1):
            for frame in frames[:-1] if loops and lap == 0 else frames:
                pose(arm, name, frame)
                solver.step(state, 1.0 / fps if state else 0.0)
                keys[frame] = {bone: s[0] for bone, s in state.items()}
        if loops:
            keys[last] = keys[first]
        for h in hinges:
            path = 'pose.bones["%s"].rotation_quaternion' % h.bone
            half = 0.5 * np.array([keys[f][h.bone] for f in frames])
            for index, values in enumerate((np.cos(half), np.sin(half), 0.0 * half, 0.0 * half)):
                curve = action.fcurves.new(path, index=index, action_group=h.bone)
                curve.keyframe_points.add(len(frames))
                curve.keyframe_points.foreach_set("co", np.stack([frames, values], axis=1).ravel())
                for point in curve.keyframe_points:
                    point.interpolation = "LINEAR"
                curve.update()

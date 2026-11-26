"""The keys of the knight's clips, a bone's channel at a time: `Channel` reads and changes the keys a clip
came with, `add` keys a channel the clip left alone, and `Posed` plays a clip while its keys are measured."""
import bpy
import numpy as np


class Channel:
    """One bone's rotation or location keys in an action."""

    def __init__(self, action, bone, prop):
        path = 'pose.bones["%s"].%s' % (bone, prop)
        self.curves = sorted((fc for fc in action.fcurves if fc.data_path == path), key=lambda fc: fc.array_index)

    def get(self, k):
        return [fc.keyframe_points[k].co.y for fc in self.curves]

    def set(self, k, value):
        for fc, v in zip(self.curves, value):
            p = fc.keyframe_points[k]
            p.handle_left.y += v - p.co.y
            p.handle_right.y += v - p.co.y
            p.co.y = v

    def frame(self, k):
        return self.curves[0].keyframe_points[k].co.x

    def count(self):
        return len(self.curves[0].keyframe_points)


def add(action, bone, prop, frames, values):
    """Keys a bone's `prop` in an action that had none for it: values (n, 4) for a quaternion, w first, or (n, 3)
    for a location, one for each of `frames`."""
    path = 'pose.bones["%s"].%s' % (bone, prop)
    for index, column in enumerate(np.asarray(values).T):
        curve = action.fcurves.new(path, index=index, action_group=bone)
        curve.keyframe_points.add(len(frames))
        curve.keyframe_points.foreach_set("co", np.stack([frames, column], axis=1).ravel())
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
        curve.update()


def eased(frames, needs, over):
    """Each of `needs` (one per frame) held over the frames about it, rising and falling over `over` frames: a frame
    takes the need, its own or a nearby one's, that weighs most there, whichever way it points."""
    near = np.clip(1.0 - np.abs(np.subtract.outer(frames, frames)) / over, 0.0, 1.0)
    weighed = np.asarray(needs, dtype=np.float64)[None, :] * (near * near * (3.0 - 2.0 * near))
    return weighed[np.arange(len(frames)), np.argmax(np.abs(weighed), axis=1)]


class Posed:
    """Plays `action` on the rig while keys are measured, then puts back what it played before."""

    def __init__(self, arm, action):
        self.arm, self.action = arm, action

    def __enter__(self):
        data = self.arm.animation_data
        self.held = (data.action, data.action_slot) if data else None
        self.arm.animation_data_create()
        self.arm.animation_data.action = self.action
        if self.action.slots:
            self.arm.animation_data.action_slot = self.action.slots[0]
        return self

    def __exit__(self, *_):
        if self.held:
            self.arm.animation_data.action, self.arm.animation_data.action_slot = self.held
        else:
            self.arm.animation_data_clear()

    def at(self, frame):
        bpy.context.scene.frame_set(int(frame), subframe=frame - int(frame))

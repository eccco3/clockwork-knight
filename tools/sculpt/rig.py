"""Skeletons for sculpted figures: bones stood on the sculpt's landmarks, skins that are fields over the rest
pose, and poses struck and recorded on them.

Bones are (name, parent, head, tail). Paired bones are described on the left and end in _l; their twins end
in _r. A pose is every bone's rotation from rest about its own head, as name -> 3x3 in the figure's axes
(see `turns`), and how far the bones that leave their place have moved.
"""
import bpy
import numpy as np
from mathutils import Matrix
from . import sdf as S
from .num import smoothstep
from .turns import MIRROR, SAME

MOST = 4                                       # bones that may hold one vertex


# ---------------------------------------------------------------- bones

def twin(name):
    return name[:-1] + "r" if name and name.endswith("_l") else name


def both_sides(bones):
    for name, parent, head, tail in bones:
        yield name, parent, head, tail
        if name.endswith("_l"):
            yield twin(name), twin(parent), head * MIRROR, tail * MIRROR


def armature(name, bones):
    ob = bpy.data.objects.new(name, bpy.data.armatures.new(name))
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for bone, parent, head, tail in bones:
        b = ob.data.edit_bones.new(bone)
        b.head, b.tail = head, tail
        if parent:
            b.parent = ob.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


# ---------------------------------------------------------------- skins

def points(ob):
    co = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def weigh(ob, names, w):
    """Give a mesh its vertex groups from an (N, bones) array of shares, keeping the MOST largest of each point."""
    w = np.array(w, dtype=np.float64)
    if w.shape[1] > MOST:
        w[w < np.sort(w, axis=1)[:, -MOST, None]] = 0.0
    w /= w.sum(1, keepdims=True)
    for k, name in enumerate(names):
        held = np.nonzero(w[:, k])[0]
        if len(held):
            group = ob.vertex_groups.new(name=name)
            for i in held:
                group.add([int(i)], float(w[i, k]), "REPLACE")


def attach(ob, skeleton):
    ob.parent = skeleton
    ob.modifiers.new("rig", "ARMATURE").object = skeleton


def beyond(p, joint, way, before, after):
    """0 short of a joint and 1 past it along `way`, easing from `before` metres short to `after` past."""
    return smoothstep(-before, after, (p - joint) @ S.normalize(way))


def twisted(hold, share, n):
    """The holds of `n` bones that share out a limb's twist, from the limb's own `hold` and how far along it
    each point lies, 0..1: the first carries the whole limb, and each one after it the points further along."""
    return [hold] + [hold * np.clip(share * (n - 1) - k, 0.0, 1.0) for k in range(n - 1)]


def chain(*holds):
    """Weights down a chain of bones from (name, hold) pairs, where a hold is the share of each point carried
    by that bone and all below it: no bone holds more than the one above it."""
    names, held = zip(*holds)
    held = tuple(np.minimum.accumulate(held))
    return {name: h - below for name, h, below in zip(names, held, held[1:] + (0.0,))}


# ---------------------------------------------------------------- poses and clips

def strike(ob, turned, moves):
    """Put the rig in a pose."""
    for pb in ob.pose.bones:
        rest = np.array(pb.bone.matrix_local)[:3, :3]
        above = turned[pb.parent.name] if pb.parent else SAME
        pb.rotation_quaternion = Matrix((rest.T @ above.T @ turned[pb.name] @ rest).tolist()).to_quaternion()
        if pb.name in moves:
            pb.location = rest.T @ above.T @ moves[pb.name]


def use(ob, action):
    ob.animation_data_create().action = action
    if action and action.slots:
        ob.animation_data.action_slot = action.slots[0]


def shelve(ob, actions):
    """Lay each clip on a track of its own, which is how the GLB exporter tells clips apart."""
    use(ob, None)
    for action in actions:
        track = ob.animation_data.nla_tracks.new()
        track.name = action.name
        track.strips.new(action.name, 0, action).action_slot = action.slots[0]


def record(ob, name, frames, pose, moved):
    """Key a clip on every bone at every frame, and the places of the bones named in `moved`: pose(phase in
    0..1) puts the rig in its pose and returns how far any limb's target lies beyond its reach. The last
    frame of a loop repeats the first."""
    action = bpy.data.actions.new(name)
    use(ob, action)
    before, strain = {}, 0.0
    for frame in range(frames + 1):
        strain = max(strain, pose(frame / frames))
        for pb in ob.pose.bones:
            q = pb.rotation_quaternion.copy()
            if pb.name in before and before[pb.name].dot(q) < 0:
                q.negate()
            pb.rotation_quaternion = before[pb.name] = q
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            if pb.name in moved:
                pb.keyframe_insert("location", frame=frame)
    print("CLIP %-7s %d frames  %.2f s%s" % (name, frames, frames / bpy.context.scene.render.fps,
                                             "  %.0f mm OUT OF REACH" % (strain * 1e3) if strain > 1e-4 else ""))
    return action

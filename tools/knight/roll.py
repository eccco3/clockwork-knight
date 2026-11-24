"""The knight's roll. The downloaded clip opens with a dive: she springs up and flies flat, a metre
off the ground, before her hands come down. `tuck_opening` makes that stretch a low tuck: her spine
and arms fold toward the clip's own balled pose, her pelvis comes down as far as her hands and head
allow, and her feet push off where they stood and then draw in under her hips. Her root motion,
her pelvis's turn and every key's time are untouched, so the roll travels and ends as before.

Keys are counted from the clip's first; it has 30 a second. Lengths are metres on the rig."""
import math

import bpy
from mathutils import Quaternion, Vector

TUCK_KEY = 20                      # the key at which the clip has her balled up
# Each group folds toward the tuck by `weight`, easing in over the keys rise..full and out over hold..gone.
FOLDS = [
    dict(bones=["spine_01", "spine_02", "spine_03", "neck_01", "Head"], weight=1.0, rise=1, full=8, hold=13, gone=18),
    dict(bones=["clavicle_l", "upperarm_l", "lowerarm_l", "hand_l", "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r"],
         weight=0.6, rise=2, full=9, hold=12, gone=17),
]
LOW = 0.50                         # pelvis height of the tuck
LOWERS = (1, 7)                    # keys over which she sinks to it
REACH = dict(rise=1, full=3, hold=16, gone=21)   # keys through which her legs are placed
DRAWS_IN = (3, 8)                 # keys over which her feet leave the ground and come in under her
PLANT_HEIGHT = 0.20                # ankle height of a foot pushing off
ANKLE_CLEAR = 0.09
TUCK_AHEAD, TUCK_BELOW = 0.30, 0.15   # a tucked ankle from its hip, toward her front and toward her feet
STRAIGHTEST = 0.985                # of the leg's length
# Where her upper body can touch the ground: a bone's head, or its tail with "/", and her radius there.
UPPER = {"pelvis": 0.11, "spine_02": 0.11, "spine_03": 0.12, "neck_01": 0.07, "Head/": 0.10,
         "upperarm_l": 0.06, "upperarm_r": 0.06, "lowerarm_l": 0.045, "lowerarm_r": 0.045,
         "hand_l": 0.035, "hand_r": 0.035, "middle_01_l": 0.02, "middle_01_r": 0.02}

def _smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def _window(k, rise, full, hold, gone, **_):
    return _smooth((k - rise) / (full - rise)) * (1.0 - _smooth((k - hold) / (gone - hold)))


class _Channel:
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


def _fold(action):
    for g in FOLDS:
        for name in g["bones"]:
            ch = _Channel(action, name, "rotation_quaternion")
            tuck = Quaternion(ch.get(TUCK_KEY))
            for k in range(1, g["gone"]):
                q = Quaternion(ch.get(k)).slerp(tuck, g["weight"] * _window(k, **g))
                if q.dot(Quaternion(ch.get(k - 1))) < 0.0:
                    q.negate()
                ch.set(k, q)


def _clearance(arm, contacts):
    """Height of the lowest of `contacts` above the ground, in the pose now set."""
    low = math.inf
    for spec, radius in contacts.items():
        pb = arm.pose.bones[spec.rstrip("/")]
        low = min(low, (pb.tail if spec.endswith("/") else pb.head).z - radius)
    return low

class _Posed:
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


def _lower(arm, action, pelvis_keys):
    """Brings her pelvis down to LOW, or as near as her hands, head and back allow."""
    pelvis = arm.pose.bones["pelvis"]
    with _Posed(arm, action) as posed:
        drop = []
        for k in range(pelvis_keys.count()):
            posed.at(pelvis_keys.frame(k))
            want = max(pelvis.head.z - LOW, 0.0) * _smooth((k - LOWERS[0]) / (LOWERS[1] - LOWERS[0]))
            drop.append(min(want, max(_clearance(arm, UPPER), 0.0)))
        for _ in range(2):
            drop = [drop[0]] + [min(drop[k], 0.25 * drop[k - 1] + 0.5 * drop[k] + 0.25 * drop[k + 1])
                                for k in range(1, len(drop) - 1)] + [drop[-1]]
        for k, d in enumerate(drop):
            posed.at(pelvis_keys.frame(k))
            # the pelvis's location keys are in its rest frame under the root
            frame = pelvis.parent.matrix.to_3x3() @ (pelvis.parent.bone.matrix_local.inverted() @ pelvis.bone.matrix_local).to_3x3()
            pelvis_keys.set(k, Vector(pelvis_keys.get(k)) + frame.inverted() @ Vector((0.0, 0.0, -d)))


def _place(pb, turn, head):
    """Sets a pose bone's rotation and head in the rig's space, and returns its rotation key."""
    m = turn.to_matrix().to_4x4()
    m.translation = head
    pb.matrix = m
    bpy.context.view_layer.update()
    return pb.rotation_quaternion.copy()


def _reach(thigh, calf, foot, target, foot_turn, hold):
    """Two-bone reach from the pose now set: bends the knee in its own plane, then swings the leg, until
    the ankle is at `target`. The foot keeps `foot_turn`, its rotation in the rig's space, by `hold`."""
    hip, knee, ankle = thigh.head.copy(), calf.head.copy(), foot.head.copy()
    was = [pb.matrix.to_quaternion() for pb in (thigh, calf, foot)]
    l1, l2 = (knee - hip).length, (ankle - knee).length
    to = target - hip
    d = min(max(to.length, abs(l1 - l2) + 1e-3), (l1 + l2) * STRAIGHTEST)
    u, v = hip - knee, ankle - knee
    axis = u.cross(v)
    bend = Quaternion() if axis.length < 1e-6 else Quaternion(
        axis.normalized(), math.acos((l1 * l1 + l2 * l2 - d * d) / (2.0 * l1 * l2)) - u.angle(v))
    swing = (knee + bend @ v - hip).rotation_difference(to)
    knee = hip + swing @ (knee - hip)
    return [_place(thigh, swing @ was[0], hip), _place(calf, swing @ bend @ was[1], knee),
            _place(foot, (swing @ bend @ was[2]).slerp(foot_turn, hold), knee + swing @ bend @ v)]

def _legs(arm, action, planted):
    """Her feet push off where the clip planted them, then draw in under her hips instead of trailing out behind."""
    pelvis = arm.pose.bones["pelvis"]
    rest = pelvis.bone.matrix_local.to_3x3().inverted()
    solved = {}
    with _Posed(arm, action) as posed:
        for side in "lr":
            bones = [arm.pose.bones[n + "_" + side] for n in ("thigh", "calf", "foot")]
            keys = [_Channel(action, b.name, "rotation_quaternion") for b in bones]
            for k in range(REACH["gone"]):
                posed.at(keys[0].frame(k))
                body = pelvis.matrix.to_3x3() @ rest          # her rest directions, as her pelvis turns them
                drawn = _smooth((k - DRAWS_IN[0]) / (DRAWS_IN[1] - DRAWS_IN[0]))
                ankle, turn = planted[side][k]
                tucked = bones[0].head + body @ Vector((0.0, -TUCK_AHEAD, -TUCK_BELOW))
                target = Vector((ankle.x, ankle.y, min(ankle.z, PLANT_HEIGHT))).lerp(tucked, drawn)
                target.z = max(target.z, ANKLE_CLEAR)
                found = _reach(*bones, target, turn, 1.0 - drawn)
                w = _window(k, **REACH)
                solved[side, k] = [Quaternion(ch.get(k)).slerp(q, w) for ch, q in zip(keys, found)]
        for (side, k), found in solved.items():
            for n, q in zip(("thigh", "calf", "foot"), found):
                ch = _Channel(action, n + "_" + side, "rotation_quaternion")
                if k > 0 and q.dot(Quaternion(ch.get(k - 1))) < 0.0:
                    q.negate()
                ch.set(k, q)


def _planted(arm, action, keys):
    """Each ankle's place and each foot's rotation, in the rig's space, at the clip's first `keys` keys."""
    out = {"l": [], "r": []}
    with _Posed(arm, action) as posed:
        frames = _Channel(action, "pelvis", "location")
        for k in range(keys):
            posed.at(frames.frame(k))
            for side in "lr":
                foot = arm.pose.bones["foot_" + side]
                out[side].append((foot.head.copy(), foot.matrix.to_quaternion()))
    return out


def tuck_opening(arm, action):
    planted = _planted(arm, action, REACH["gone"])
    _fold(action)
    _lower(arm, action, _Channel(action, "pelvis", "location"))
    _legs(arm, action, planted)
    for fc in action.fcurves:
        fc.update()
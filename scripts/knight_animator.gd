class_name KnightAnimator
extends RefCounted
## Pose sampler / blender for the knight's skeleton.
##
## Clips are sampled by hand rather than through AnimationTree so that gaits can be blended on a
## shared normalised stride phase (no foot ghosting), root motion can be read per clip, and every
## change of state is smoothed by inertialisation: the new pose source takes over immediately and
## the difference to the previous output decays away, instead of two animations cross-fading.

class Clip:
	var anim: Animation
	var length := 0.0
	var rot := PackedInt32Array()
	var pelvis_pos := -1
	var root_pos := -1

var skel: Skeleton3D
var clips := {}
var bones := PackedInt32Array()          ## bones driven by animation
var pelvis := -1
var root := -1
var out_rot: Array[Quaternion] = []
var out_pos := Vector3.ZERO

var _rest_rot: Array[Quaternion] = []
var _rest_pelvis := Vector3.ZERO
var _off_rot: Array[Quaternion] = []
var _off_pos := Vector3.ZERO
var _off_t := 1e9
var _off_dur := 0.2
var _pending := -1.0
var _has_out := false


func setup(skeleton: Skeleton3D, player: AnimationPlayer) -> void:
	skel = skeleton
	var n := skel.get_bone_count()
	pelvis = skel.find_bone("pelvis")
	root = skel.find_bone("root")
	_rest_pelvis = skel.get_bone_rest(pelvis).origin
	out_rot.resize(n)
	_off_rot.resize(n)
	_rest_rot.resize(n)
	for b in n:
		_rest_rot[b] = skel.get_bone_rest(b).basis.get_rotation_quaternion()
		out_rot[b] = _rest_rot[b]
		_off_rot[b] = Quaternion.IDENTITY
	var driven := {}
	for anim_name in player.get_animation_list():
		var a := player.get_animation(anim_name)
		var c := Clip.new()
		c.anim = a
		c.length = a.length
		c.rot.resize(n)
		c.rot.fill(-1)
		for t in a.get_track_count():
			var path := a.track_get_path(t)
			if path.get_subname_count() == 0:
				continue
			var b := skel.find_bone(path.get_subname(0))
			if b < 0:
				continue
			match a.track_get_type(t):
				Animation.TYPE_ROTATION_3D:
					c.rot[b] = t
					driven[b] = true
				Animation.TYPE_POSITION_3D:
					if b == pelvis:
						c.pelvis_pos = t
					elif b == root:
						c.root_pos = t
		clips[String(anim_name)] = c
	driven.erase(root)
	for b in n:
		if driven.has(b):
			bones.append(b)


func new_pose() -> Array[Quaternion]:
	var p: Array[Quaternion] = []
	p.resize(skel.get_bone_count())
	for b in p.size():
		p[b] = _rest_rot[b]
	return p


func length(clip: String) -> float:
	return clips[clip].length


## Fills `into` with the clip's pose at `time`; returns the pelvis position.
func sample(clip: String, time: float, into: Array[Quaternion]) -> Vector3:
	var c: Clip = clips[clip]
	var t := clampf(time, 0.0, c.length)
	var a := c.anim
	for b in bones:
		var tr := c.rot[b]
		into[b] = a.rotation_track_interpolate(tr, t) if tr >= 0 else _rest_rot[b]
	return a.position_track_interpolate(c.pelvis_pos, t) if c.pelvis_pos >= 0 else _rest_pelvis


## Root-bone travel (skeleton space) between two times of a clip.
func root_delta(clip: String, t0: float, t1: float) -> Vector3:
	var c: Clip = clips[clip]
	if c.root_pos < 0:
		return Vector3.ZERO
	return c.anim.position_track_interpolate(c.root_pos, clampf(t1, 0.0, c.length)) \
		- c.anim.position_track_interpolate(c.root_pos, clampf(t0, 0.0, c.length))


## a <- slerp(a, b, w), optionally per-bone weighted.
func blend(a: Array[Quaternion], b: Array[Quaternion], w: float, mask: PackedFloat32Array = PackedFloat32Array()) -> void:
	if w <= 0.0:
		return
	if mask.is_empty():
		for i in bones:
			a[i] = a[i].slerp(b[i], w)
	else:
		for i in bones:
			var ww := w * mask[i]
			if ww > 0.0:
				a[i] = a[i].slerp(b[i], ww)


## Call before switching pose source: the jump is absorbed over `duration` seconds.
func inertialize(duration: float) -> void:
	_pending = maxf(duration, 0.01)


func apply(target: Array[Quaternion], target_pos: Vector3, dt: float) -> void:
	if _pending > 0.0 and _has_out:
		for b in bones:
			_off_rot[b] = (out_rot[b] * target[b].inverse()).normalized()
		_off_pos = out_pos - target_pos
		_off_t = 0.0
		_off_dur = _pending
	_pending = -1.0
	_off_t += dt
	if _off_t < _off_dur * 2.2:
		# critically damped ease: offset * (1 + wt) * exp(-wt)
		var w := 4.6 / _off_dur
		var k := (1.0 + w * _off_t) * exp(-w * _off_t)
		for b in bones:
			out_rot[b] = (Quaternion.IDENTITY.slerp(_off_rot[b], k) * target[b]).normalized()
		out_pos = target_pos + _off_pos * k
	else:
		for b in bones:
			out_rot[b] = target[b]
		out_pos = target_pos
	for b in bones:
		skel.set_bone_pose_rotation(b, out_rot[b])
	skel.set_bone_pose_position(pelvis, out_pos)
	_has_out = true

class_name KnightCollapse
## The knight's death, keyed here because her build's clips have none. It carries on from the last frame of
## Hit_Chest: her knees give and she drops onto them, toes tucked under, bows over them as her arms go slack and
## her sword sinks until its tip finds the ground, and runs down in three last ticks of her clockwork.
##
## TURNS turn bones, with all they carry, about axes through their joints that lie as her body stood at the start,
## as their parents have carried them since: x across to her left, y up, z ahead, in degrees (about x, a bone that
## points up bows forward and one that hangs swings back). AIMS point bones, from a moment on, along directions in
## her upright body, as slack limbs hang whatever the body does: Vector2(degrees from straight down, + back; the
## share leaning to her left). A bone is aimed by itself, or by a bone it holds, as her hand by her sword; her
## shins rise as far as they must to keep the balls of her feet BALL off the ground. PELVIS lowers her by shares of
## the drop that rests her knees KNEE off the ground, and moves her ahead in metres. Every channel eases through
## its keys without overshooting them, as the grinners' do (tools/grinner/keys.py). FOLLOWS turn her guards with
## the joints under them, as her build keys them: each pauldron as its upper arm turns, each couter and poleyn half
## as far as its elbow or knee.

const NAME := "Collapse"
const FROM := "Hit_Chest"
const FPS := 30.0
const LENGTH := 2.4
const KNEE := 0.085
const BALL := 0.02

const PELVIS := [[0.12, Vector2(0.04, 0.0)], [0.4, Vector2(0.6, 0.05)], [0.54, Vector2(1.03, 0.08)],
	[0.62, Vector2(0.98, 0.09)], [0.76, Vector2(1.0, 0.1)]]
const TURNS := {
	"pelvis": [[0.5, Vector3(6, 0, 0)], [1.0, Vector3(8, 0, 0)]],
	"spine_01": [[0.6, Vector3(3, 0, 0)], [0.9, Vector3(6, 0, 0)]],
	"spine_02": [[0.62, Vector3(3, 0, 0)], [0.95, Vector3(7, 0, 0)], [1.36, Vector3(7, 0, 0)], [1.42, Vector3(8.5, 0, 0)],
		[1.56, Vector3(8.5, 0, 0)], [1.62, Vector3(10, 0, 0)]],
	"spine_03": [[0.65, Vector3(3, 0, 0)], [1.0, Vector3(6, 0, 0)]],
	"neck_01": [[0.6, Vector3(6, 0, 0)], [1.0, Vector3(10, 0, 0)], [1.76, Vector3(10, 0, 0)], [1.82, Vector3(13, 0, 0)]],
	"Head": [[0.58, Vector3(10, 0, 4)], [0.72, Vector3(20, 0, 6)], [1.0, Vector3(17, 0, 8)], [1.36, Vector3(17, 0, 8)],
		[1.42, Vector3(21, 0, 9)], [1.56, Vector3(21, 0, 9)], [1.62, Vector3(24, 0, 10)], [1.76, Vector3(24, 0, 10)],
		[1.82, Vector3(27, 0, 11)]],
	"clavicle_r": [[0.6, Vector3(0, 6, 8)], [1.0, Vector3(0, 8, 10)]],
	"clavicle_l": [[0.6, Vector3(0, -6, -8)], [1.0, Vector3(0, -8, -10)]],
}
const AIMS := {
	"thigh_l": [0.08, [[0.38, Vector2(-45, 0.16)], [0.54, Vector2(-32, 0.17)], [0.7, Vector2(-30, 0.17)]]],
	"thigh_r": [0.1, [[0.4, Vector2(-36, -0.18)], [0.58, Vector2(-31, -0.17)], [0.75, Vector2(-30, -0.17)]]],
	"calf_l": [0.08, [[0.38, Vector2(55, 0.12)], [0.54, Vector2(95, 0.1)], [0.66, Vector2(98, 0.1)]]],
	"calf_r": [0.1, [[0.4, Vector2(60, -0.05)], [0.58, Vector2(95, -0.1)], [0.7, Vector2(98, -0.1)]]],
	"foot_l": [0.08, [[0.38, Vector2(-42, -0.05)], [0.54, Vector2(-30, 0.0)], [0.66, Vector2(-28, 0.0)]]],
	"foot_r": [0.1, [[0.4, Vector2(-40, -0.3)], [0.58, Vector2(-30, -0.1)], [0.7, Vector2(-28, -0.08)]]],
	"ball_l": [0.3, [[0.55, Vector2(-88, 0.0)], [0.7, Vector2(-90, 0.0)]]],
	"ball_r": [0.3, [[0.6, Vector2(-88, -0.05)], [0.75, Vector2(-90, -0.05)]]],
	"upperarm_r": [0.3, [[0.6, Vector2(12, -0.16)], [1.0, Vector2(-4, -0.14)], [1.3, Vector2(-6, -0.14)]]],
	"lowerarm_r": [0.3, [[0.6, Vector2(-30, -0.2)], [1.0, Vector2(-38, -0.12)]]],
	"hand_r": [0.35, [[0.65, Vector2(-100, 0.0)], [1.0, Vector2(-68, -0.2)], [1.25, Vector2(-56, -0.24)]], "weapon_r"],
	"upperarm_l": [0.3, [[0.6, Vector2(8, 0.25)], [1.0, Vector2(-4, 0.2)]]],
	"lowerarm_l": [0.3, [[0.7, Vector2(-20, 0.14)], [1.1, Vector2(-12, 0.12)]]],
	"hand_l": [0.4, [[1.1, Vector2(-20, 0.05)]]],
}
const SHINS := {"calf_l": "foot_l", "calf_r": "foot_r"}
const FOLLOWS := {"pauldron_l": ["upperarm_l", 1.0], "pauldron_r": ["upperarm_r", 1.0], "couter_l": ["lowerarm_l", 0.5],
	"couter_r": ["lowerarm_r", 0.5], "poleyn_l": ["calf_l", 0.5], "poleyn_r": ["calf_r", 0.5]}


## Adds the clip to her AnimationPlayer's clips.
static func add_to(player: AnimationPlayer, skel: Skeleton3D) -> void:
	var from := player.get_animation(FROM)
	var start := Start.new(skel, from)
	var clip := Animation.new()
	clip.length = LENGTH
	var frames := roundi(LENGTH * FPS)
	var poses: Array = []
	for f in frames + 1:
		poses.append(start.pose(f / FPS))
	for t in from.get_track_count():
		var path := from.track_get_path(t)
		var b := skel.find_bone(path.get_subname(0))
		var type := from.track_get_type(t)
		if b < 0 or (type != Animation.TYPE_ROTATION_3D and type != Animation.TYPE_POSITION_3D):
			continue
		var track := clip.add_track(type)
		clip.track_set_path(track, path)
		var name := skel.get_bone_name(b)
		if type == Animation.TYPE_POSITION_3D and b == start.pelvis:
			for f in frames + 1:
				clip.position_track_insert_key(track, f / FPS, start.hips(f / FPS))
		elif type == Animation.TYPE_POSITION_3D:
			clip.position_track_insert_key(track, 0.0, start.at[b])
		elif TURNS.has(name) or AIMS.has(name) or FOLLOWS.has(name):
			for f in frames + 1:
				clip.rotation_track_insert_key(track, f / FPS, poses[f][b])
		else:
			clip.rotation_track_insert_key(track, 0.0, start.local[b])
	player.get_animation_library(&"").add_animation(NAME, clip)


## Her pose as FROM leaves her, with the root held at rest, and the collapse's pose at any moment from it.
class Start:
	var skel: Skeleton3D
	var pelvis := -1
	## Each bone's rotation and position in its parent.
	var local: Array[Quaternion] = []
	var at := PackedVector3Array()
	## Each bone's orientation in her body.
	var held: Array[Quaternion] = []
	## How far her pelvis drops for her knees to rest KNEE off the ground, aimed as AIMS leaves her thighs.
	var drop := INF
	## How high the balls of her feet may sink, by foot: BALL, or lower where they start lower.
	var _floor := {}
	var _into_root: Basis

	func _init(of: Skeleton3D, clip: Animation) -> void:
		skel = of
		pelvis = skel.find_bone("pelvis")
		var root := skel.find_bone("root")
		_into_root = skel.get_bone_rest(root).basis.inverse()
		for b in skel.get_bone_count():
			local.append(skel.get_bone_rest(b).basis.get_rotation_quaternion())
			at.append(skel.get_bone_rest(b).origin)
		for t in clip.get_track_count():
			var b := skel.find_bone(clip.track_get_path(t).get_subname(0))
			if b < 0 or b == root:
				continue
			if clip.track_get_type(t) == Animation.TYPE_ROTATION_3D:
				local[b] = clip.rotation_track_interpolate(t, clip.length)
			elif clip.track_get_type(t) == Animation.TYPE_POSITION_3D:
				at[b] = clip.position_track_interpolate(t, clip.length)
		var where := PackedVector3Array()
		for b in skel.get_bone_count():
			var parent := skel.get_bone_parent(b)
			held.append(local[b] if parent < 0 else held[parent] * local[b])
			where.append(at[b] if parent < 0 else where[parent] + held[parent] * at[b])
		for thigh in ["thigh_l", "thigh_r"]:
			var b := skel.find_bone(thigh)
			var knee := where[b] + aim(b, LENGTH) * at[skel.get_bone_children(b)[0]].length()
			drop = minf(drop, knee.y - KNEE)
		for calf in SHINS:
			var foot := skel.find_bone(SHINS[calf])
			_floor[foot] = minf(BALL, where[skel.get_bone_children(foot)[0]].y)

	## The pelvis's position in the root at `t`.
	func hips(t: float) -> Vector3:
		var move := KnightCollapse._eased(PELVIS, t)
		return at[pelvis] + _into_root * Vector3(0.0, -drop * move.x, move.y)

	## Every bone's rotation in its parent at `t`, turned and aimed from the start, parents first.
	func pose(t: float) -> Array[Quaternion]:
		var now: Array[Quaternion] = []
		var out: Array[Quaternion] = []
		var where := PackedVector3Array()
		for b in skel.get_bone_count():
			var parent := skel.get_bone_parent(b)
			var above := now[parent] if parent >= 0 else Quaternion.IDENTITY
			var name := skel.get_bone_name(b)
			where.append(at[b] if parent < 0 else where[parent] + above * (hips(t) if b == pelvis else at[b]))
			var own := local[b]
			if TURNS.has(name):
				var frame := held[parent]
				own = frame.inverse() * Quaternion.from_euler(KnightCollapse._eased(TURNS[name], t) * (PI / 180.0)) \
					* frame * local[b]
			var mine := above * own
			if AIMS.has(name):
				var goal := aim(b, t)
				if SHINS.has(name):
					goal = _clear(goal, where[b], skel.find_bone(SHINS[name]), t)
				mine = Quaternion(mine * _holds(b) * Vector3.UP, goal) * mine
			now.append(mine)
			out.append((above.inverse() * mine).normalized())
		for name in FOLLOWS:
			var guard := skel.find_bone(name)
			var under := skel.find_bone(FOLLOWS[name][0])
			if guard >= 0 and under >= 0:
				var turned := _rest(under).inverse() * out[under]
				out[guard] = _rest(guard) * Quaternion.IDENTITY.slerp(turned, FOLLOWS[name][1])
		return out

	func _rest(b: int) -> Quaternion:
		return skel.get_bone_rest(b).basis.get_rotation_quaternion()

	## Where AIMS points bone `b`, or the bone it is aimed by, at `t`.
	func aim(b: int, t: float) -> Vector3:
		var spec: Array = AIMS[skel.get_bone_name(b)]
		var d := held[b] * _holds(b) * Vector3.UP
		var start := Vector3(rad_to_deg(atan2(-d.z, -d.y)), d.x, 0.0)
		var angles := KnightCollapse._eased(spec[1], t, start, spec[0])
		var level := sqrt(maxf(1.0 - angles.y * angles.y, 0.0))
		return Vector3(angles.y, -cos(deg_to_rad(angles.x)) * level, -sin(deg_to_rad(angles.x)) * level)

	func _holds(b: int) -> Quaternion:
		var spec: Array = AIMS[skel.get_bone_name(b)]
		return local[skel.find_bone(spec[2])] if spec.size() > 2 else Quaternion.IDENTITY

	## The shin from `knee` swung back up, if it must be, until the ball of the aimed foot below it is off the ground.
	func _clear(shin: Vector3, knee: Vector3, foot: int, t: float) -> Vector3:
		var sole := aim(foot, t) * at[skel.get_bone_children(foot)[0]].length()
		var length := at[foot].length()
		var ground: float = _floor[foot]
		if knee.y + shin.y * length + sole.y >= ground:
			return shin
		var level := sqrt(maxf(1.0 - shin.x * shin.x, 0.0))
		var pitch := acos(clampf((knee.y - ground + sole.y) / (length * level), -1.0, 1.0))
		return Vector3(shin.x, -cos(pitch) * level, -sin(pitch) * level)


## The channel at `t`: holding `start` until `from`, then eased through its keys, holding the last beyond them.
static func _eased(keys: Array, t: float, start := Vector3.ZERO, from := 0.0) -> Vector3:
	var times := PackedFloat32Array([from])
	var values: Array[Vector3] = [start]
	for key in keys:
		var v: Variant = key[1]
		times.append(key[0])
		values.append(v if v is Vector3 else Vector3(v.x, v.y, 0.0))
	var out := Vector3.ZERO
	for axis in 3:
		var v := PackedFloat32Array()
		for value in values:
			v.append(value[axis])
		out[axis] = _monotone(times, v, t)
	return out


## A curve through (times, values) easing from key to key without overshooting, so a held value stays held: cubic
## Hermite segments with Fritsch-Carlson slopes, flat at the ends.
static func _monotone(times: PackedFloat32Array, values: PackedFloat32Array, t: float) -> float:
	var n := times.size()
	if t <= times[0] or n == 1:
		return values[0]
	if t >= times[n - 1]:
		return values[n - 1]
	var slopes := PackedFloat32Array()
	slopes.resize(n)
	for i in range(1, n - 1):
		var h0 := times[i] - times[i - 1]
		var h1 := times[i + 1] - times[i]
		var r0 := (values[i] - values[i - 1]) / h0
		var r1 := (values[i + 1] - values[i]) / h1
		if r0 * r1 > 0.0:
			slopes[i] = 3.0 * (h0 + h1) / ((2.0 * h1 + h0) / r0 + (h1 + 2.0 * h0) / r1)
	var i := 0
	while times[i + 1] < t:
		i += 1
	var h := times[i + 1] - times[i]
	var s := (t - times[i]) / h
	return (2.0 * s * s * s - 3.0 * s * s + 1.0) * values[i] + (s * s * s - 2.0 * s * s + s) * h * slopes[i] \
		+ (-2.0 * s * s * s + 3.0 * s * s) * values[i + 1] + (s * s * s - s * s) * h * slopes[i + 1]

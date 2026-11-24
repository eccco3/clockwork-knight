class_name Knight
extends Node3D
## The clockwork knight's body: her colours, animation state, and the little mechanical motions
## (turning chest gears, the winding key, glancing eyes). The controller drives it through
## `speed`, `play()` / `stop()` and `tick()`.

const MODEL := preload("res://assets/models/knight.glb")
const FACE_PAINT := preload("res://assets/textures/knight/face_paint.png")
const FACE_PAINT_PLACEMENT := preload("res://assets/textures/knight/face_paint.json")

## Natural ground speed and cycle length of the gait clips (measured from their root motion).
const WALK_NATURAL := 0.975
const WALK_STRIDE := 1.300
const JOG_STRIDE := 5.000
const WALK_FULL_AT := 0.9          ## speed at which idle has fully given way to the walk
const JOG_FROM := 1.5
const JOG_FULL_AT := 3.8
## The jog bounds: each foot is down only from JOG_LANDS to JOG_PUSHES_OFF of its half of the cycle,
## and the pelvis climbs 24 cm in between. Stance plays at her ground speed so the planted foot
## holds; flight plays JOG_FLIGHT_RATE times faster and keeps JOG_FLIGHT_RISE of its climb, about
## the arc gravity allows in the shorter flight.
const JOG_LANDS := 0.025
const JOG_PUSHES_OFF := 0.185
const JOG_FLIGHT_RATE := 2.3
const JOG_FLIGHT_RISE := 0.22

var model: Node3D
var skel: Skeleton3D
var mesh: MeshInstance3D
var anim := KnightAnimator.new()

## Horizontal speed in m/s, set by the controller.
var speed := 0.0:
	set(value):
		speed = value
		_walk = clampf(speed / WALK_FULL_AT, 0.0, 1.0)
		_jog = smoothstep(JOG_FROM, JOG_FULL_AT, speed)
var action := ""
var action_t := 0.0

## How far idle has given way to the walk, and the walk to the jog, at this speed (0..1).
var _walk := 0.0
var _jog := 0.0
var _phase := 0.0
var _jog_takeoff := 0.0              ## pelvis height (its parent's z) as a foot leaves the ground
var _idle_t := 0.0
var _action_rate := 1.0
var action_weight := 1.0
## Whether her legs and pelvis hold the jump's pose under the action, as while she attacks in the air.
## `play()` clears it; `land_legs()` hands them to the action.
var air_legs := false
var _action_loop := false
var _action_next := ""
var _action_next_loop := false
var _action_fade_out := 0.2
## Blend of the sword arm toward the ready carry while moving without an action (0..1).
var carry := 0.0
var _pose: Array[Quaternion]
var _tmp: Array[Quaternion]
var _tmp2: Array[Quaternion]
var _grip := {}
var _carry: Array[Quaternion]
var _carry_mask := PackedFloat32Array()
var _legs_mask := PackedFloat32Array()
var _gears := []
var _key := -1
var _eyes := []
var _clock := 0.0
var _gear_angle := 0.0
var _eye_look := Vector2.ZERO
var _eye_goal := Vector2.ZERO
var _eye_timer := 0.0
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	model = MODEL.instantiate()
	add_child(model)
	skel = _find(model, "Skeleton3D")
	mesh = model.find_child("Knight", true, false)
	# the full mesh is too dense for the shadow maps; a low-polygon copy on the same bones casts instead
	var caster := model.find_child("KnightShadow", true, false) as MeshInstance3D
	if caster:
		caster.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
		caster.extra_cull_margin = 0.15
		mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var player: AnimationPlayer = _find(model, "AnimationPlayer")
	player.active = false
	anim.setup(skel, player)
	_pose = anim.new_pose()
	_tmp = anim.new_pose()
	_tmp2 = anim.new_pose()
	_carry = anim.new_pose()
	var jog_len := anim.length("Jog_Fwd")
	_jog_takeoff = (anim.sample("Jog_Fwd", JOG_LANDS * jog_len, _tmp).z
		+ anim.sample("Jog_Fwd", JOG_PUSHES_OFF * jog_len, _tmp).z) * 0.5
	Looks.dress(mesh, {
		"wood_light": Looks.oiled_wood(Color(0.70, 0.47, 0.24), Color(0.44, 0.25, 0.11)),
		"wood_face": Looks.face_wood(Color(0.76, 0.55, 0.34), Color(0.58, 0.38, 0.20),
			FACE_PAINT, FACE_PAINT_PLACEMENT),
		"wood_dark": Looks.lacquered_wood(Color(0.27, 0.155, 0.085), Color(0.085, 0.045, 0.026)),
		"brass": Looks.brass(Color(0.90, 0.70, 0.34)),
		"brass_dark": Looks.dull_brass(Color(0.46, 0.33, 0.15)),
		"steel": Looks.steel(Color(0.76, 0.77, 0.79), Color(0.36, 0.36, 0.38)),
		"leather": Looks.leather(Color(0.13, 0.060, 0.032), Color(0.07, 0.03, 0.018)),
		"eye": Looks.glass_eye(Color(0.10, 0.22, 0.19), Color(0.56, 0.44, 0.19), 0.385, 0.335),
	})
	_setup_extras()
	var t0 := Time.get_ticks_usec()
	var jl := JointLight.new(skel, mesh, anim.bones)
	skel.add_child(jl)
	print("joint light ms ", (Time.get_ticks_usec() - t0) / 1000.0, " joints ", jl._chains.size(), " streaks ", jl.mesh.get_faces().size() / 6 if jl.mesh else 0)
	for c in jl._chains:
		print("  ", skel.get_bone_name(c[0]))
	mesh.extra_cull_margin = 0.15
	for v: VisualInstance3D in find_children("*", "VisualInstance3D", true, false):
		v.layers = Layers.CHARACTERS
	_apply_pose(0.0)


func _find(n: Node, type: String) -> Node:
	if n.is_class(type):
		return n
	for c in n.get_children():
		var r := _find(c, type)
		if r:
			return r
	return null


# ------------------------------------------------------------------ rig extras

func _setup_extras() -> void:
	for g in [["gear_a", 1.0], ["gear_b", -1.6], ["gear_c", -2.0]]:
		var b := skel.find_bone(g[0])
		if b >= 0:
			_gears.append([b, g[1], skel.get_bone_rest(b).basis.get_rotation_quaternion()])
	_key = skel.find_bone("key")
	for n in ["eye_l", "eye_r"]:
		var b := skel.find_bone(n)
		if b >= 0:
			var inv := skel.get_bone_global_rest(b).basis.inverse()
			_eyes.append([b, skel.get_bone_rest(b).basis.get_rotation_quaternion(),
				(inv * Vector3.UP).normalized(), (inv * Vector3.RIGHT).normalized()])
	# the sword hand always keeps its grip; the sword arm leans toward a ready carry while moving
	anim.sample("Sword_Idle", 0.0, _carry)
	_carry_mask.resize(skel.get_bone_count())
	_carry_mask.fill(0.0)
	for b in skel.get_bone_count():
		var n := skel.get_bone_name(b)
		if n.ends_with("_r") and (n.begins_with("index") or n.begins_with("middle") or n.begins_with("ring")
				or n.begins_with("pinky") or n.begins_with("thumb")):
			_grip[b] = _carry[b]
	for pair in [["clavicle_r", 0.5], ["upperarm_r", 1.0], ["lowerarm_r", 1.0], ["hand_r", 1.0]]:
		var b := skel.find_bone(pair[0])
		if b >= 0:
			_carry_mask[b] = pair[1]
	# the pelvis half keeps the jump, so the action's twist still reaches the hips
	_legs_mask.resize(skel.get_bone_count())
	_legs_mask.fill(0.0)
	for b in skel.get_bone_count():
		var n := skel.get_bone_name(b)
		if n == "pelvis":
			_legs_mask[b] = 0.5
		elif n.ends_with("_l") or n.ends_with("_r"):
			if n.begins_with("thigh") or n.begins_with("calf") or n.begins_with("foot") or n.begins_with("ball") \
					or n.begins_with("poleyn"):
				_legs_mask[b] = 1.0
	_rng.seed = 20261122


# ------------------------------------------------------------------ control API

## Start a full-body clip. When it ends it fades back to locomotion over `fade_out`, unless
## `then()` has queued a follow-on clip.
func play(clip: String, blend := 0.12, start := 0.0, rate := 1.0, loop := false, fade_out := 0.2) -> void:
	anim.inertialize(blend)
	action = clip
	action_t = start
	_action_rate = rate
	action_weight = 1.0
	air_legs = false
	_action_next = ""
	_action_loop = loop
	_action_fade_out = fade_out


## Give her legs and pelvis back to the action, blended over `blend` seconds.
func land_legs(blend := 0.1) -> void:
	if air_legs:
		anim.inertialize(blend)
		air_legs = false


## Queue a clip that takes over, without a blend, when the current one ends.
func then(clip: String, loop := false) -> void:
	_action_next = clip
	_action_next_loop = loop


func stop(blend := 0.2) -> void:
	if action != "":
		anim.inertialize(blend)
		action = ""


func action_length() -> float:
	return anim.length(action) if action != "" else 0.0


## Advance animation clocks by one physics step; returns root motion (model space) for that step.
func tick(dt: float) -> Vector3:
	var rm := Vector3.ZERO
	if action != "":
		var t0 := action_t
		action_t += dt * _action_rate
		var len := anim.length(action)
		rm = anim.root_delta(action, t0, minf(action_t, len))
		if action_t >= len:
			if _action_loop:
				action_t = fmod(action_t, len)
			elif _action_next != "":
				action = _action_next
				action_t = 0.0
				_action_next = ""
				_action_loop = _action_next_loop
				_action_rate = 1.0
			else:
				stop(_action_fade_out)
	# stride phase advances so the planted foot matches the ground speed, and hurries through flight
	if speed > 0.02:
		var rate := speed / (lerpf(WALK_STRIDE, JOG_STRIDE, _jog) * maxf(_walk, 0.05))
		_phase = fposmod(_phase + dt * rate * (1.0 + (JOG_FLIGHT_RATE - 1.0) * _jog * _jog_flight()), 1.0)
	_idle_t = fposmod(_idle_t + dt, anim.length("Idle"))
	return rm


## How airborne the jog is at the current stride phase: 0 while a foot is planted, 1 in flight,
## easing over the last and first few hundredths of flight.
func _jog_flight() -> float:
	var h := fposmod(_phase, 0.5)
	return 1.0 - smoothstep(JOG_LANDS - 0.03, JOG_LANDS, h) + smoothstep(JOG_PUSHES_OFF, JOG_PUSHES_OFF + 0.03, h)


# ------------------------------------------------------------------ pose

func _process(dt: float) -> void:
	_apply_pose(dt)


func _apply_pose(dt: float) -> void:
	var pos := _locomotion(_pose)
	if action != "":
		var p2 := anim.sample(action, action_t, _tmp)
		anim.blend(_pose, _tmp, action_weight)
		pos = pos.lerp(p2, action_weight)
		if air_legs:
			pos = anim.sample("Jump", fposmod(_clock, anim.length("Jump")), _tmp)
			anim.blend(_pose, _tmp, 1.0, _legs_mask)
	for b in _grip:
		_pose[b] = _grip[b]
	anim.apply(_pose, pos, dt)
	_mechanics(dt)


func _locomotion(into: Array[Quaternion]) -> Vector3:
	var pos := anim.sample("Idle", _idle_t, into)
	if _walk > 0.0:
		var p := anim.sample("Walk", _phase * anim.length("Walk"), _tmp)
		if _jog > 0.0:
			var pj := anim.sample("Jog_Fwd", _phase * anim.length("Jog_Fwd"), _tmp2)
			pj.z -= maxf(pj.z - _jog_takeoff, 0.0) * (1.0 - JOG_FLIGHT_RISE) * _jog_flight()
			anim.blend(_tmp, _tmp2, _jog)
			p = p.lerp(pj, _jog)
		anim.blend(into, _tmp, _walk)
		pos = pos.lerp(p, _walk)
	if carry > 0.0:
		anim.blend(into, _carry, carry, _carry_mask)
	return pos


func _mechanics(dt: float) -> void:
	_clock += dt
	# the movement runs faster the harder she works
	_gear_angle += dt * (0.9 + speed * 0.9 + (2.5 if action != "" else 0.0))
	for g in _gears:
		skel.set_bone_pose_rotation(g[0], g[2] * Quaternion(Vector3.UP, _gear_angle * g[1]))
	if _key >= 0:
		# the key creeps round in escapement ticks
		var ticks := _gear_angle * 1.5
		var k := floorf(ticks) + smoothstep(0.0, 0.35, fposmod(ticks, 1.0))
		skel.set_bone_pose_rotation(_key, skel.get_bone_rest(_key).basis.get_rotation_quaternion() * Quaternion(Vector3.UP, k * TAU / 24.0))
	# eyes: small glances, quick moves, long holds
	_eye_timer -= dt
	if _eye_timer <= 0.0:
		_eye_timer = _rng.randf_range(0.9, 3.2)
		_eye_goal = Vector2(_rng.randf_range(-0.16, 0.16), _rng.randf_range(-0.045, 0.04)) if _rng.randf() < 0.75 else Vector2.ZERO
	_eye_look = _eye_look.lerp(_eye_goal, 1.0 - exp(-dt * 22.0))
	for e in _eyes:
		skel.set_bone_pose_rotation(e[0], e[1] * Quaternion(e[2], _eye_look.x) * Quaternion(e[3], _eye_look.y))


## Debug / showcase: hold one clip at a time.
func pose_at(clip: String, t: float) -> void:
	action = clip
	action_t = t
	_action_rate = 0.0
	action_weight = 1.0
	_action_loop = true

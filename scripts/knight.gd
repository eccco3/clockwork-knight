class_name Knight
extends Node3D
## The clockwork knight's body: materials, animation state, and the little mechanical motions
## (turning chest gears, the winding key, glancing eyes). The controller drives it through
## `speed`, `play()` / `stop()` and `tick()`.

const MODEL := preload("res://assets/models/knight.glb")
const WOOD := preload("res://shaders/knight_wood.gdshader")
const SURFACE := preload("res://shaders/knight_surface.gdshader")
const EYE := preload("res://shaders/knight_eye.gdshader")
const FACE_PAINT := preload("res://assets/textures/knight/face_paint.png")

## Natural ground speed and cycle length of the gait clips (measured from their root motion).
const WALK_NATURAL := 0.975
const WALK_STRIDE := 1.300
const JOG_STRIDE := 5.000
const WALK_FULL_AT := 0.9          ## speed at which idle has fully given way to the walk
const JOG_FROM := 1.5
const JOG_FULL_AT := 3.8

var model: Node3D
var skel: Skeleton3D
var mesh: MeshInstance3D
var anim := KnightAnimator.new()

## Horizontal speed in m/s, set by the controller.
var speed := 0.0
var action := ""
var action_t := 0.0

var _phase := 0.0
var _idle_t := 0.0
var _action_rate := 1.0
var action_weight := 1.0
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
	model = MODEL.instantiate()
	add_child(model)
	skel = _find(model, "Skeleton3D")
	mesh = _find(model, "MeshInstance3D")
	var player: AnimationPlayer = _find(model, "AnimationPlayer")
	player.active = false
	anim.setup(skel, player)
	_pose = anim.new_pose()
	_tmp = anim.new_pose()
	_tmp2 = anim.new_pose()
	_carry = anim.new_pose()
	_setup_materials()
	_setup_extras()
	mesh.extra_cull_margin = 0.15
	for v: VisualInstance3D in find_children("*", "VisualInstance3D", true, false):
		v.layers = Hall.CHARACTER_LAYER
	_apply_pose(0.0)


func _find(n: Node, type: String) -> Node:
	if n.is_class(type):
		return n
	for c in n.get_children():
		var r := _find(c, type)
		if r:
			return r
	return null


# ------------------------------------------------------------------ materials

func _wood(early: Color, late: Color, p: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = WOOD
	m.set_shader_parameter("color_early", early)
	m.set_shader_parameter("color_late", late)
	for k in p:
		m.set_shader_parameter(k, p[k])
	return m


func _surface(albedo: Color, p: Dictionary) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = SURFACE
	m.set_shader_parameter("albedo", albedo)
	for k in p:
		m.set_shader_parameter(k, p[k])
	return m


func _setup_materials() -> void:
	var eye := ShaderMaterial.new()
	eye.shader = EYE
	var mats := {
		"wood_light": _wood(Color(0.70, 0.47, 0.24), Color(0.44, 0.25, 0.11),
			{"ring_density": 135.0, "ring_contrast": 0.55, "coat": 0.35, "coat_roughness": 0.20}),
		"wood_face": _wood(Color(0.76, 0.55, 0.34), Color(0.58, 0.38, 0.20),
			{"ring_density": 170.0, "ring_contrast": 0.30, "pore_strength": 0.12, "fiber_strength": 0.12,
			"figure_strength": 0.10, "coat": 0.3, "coat_roughness": 0.24, "roughness_min": 0.34, "roughness_max": 0.50, "bump": 0.05,
			# the lacquer texture: FACE_GRAIN in tools/knight/build_knight.py, PAINT_* in tools/knight/head.py
			"paint_tex": FACE_PAINT, "paint_origin": Vector3(0.09, 0.05, 0.60), "paint_size": Vector3(0.064, -0.100, 0.044)}),
		"wood_dark": _wood(Color(0.27, 0.155, 0.085), Color(0.085, 0.045, 0.026),
			{"ring_density": 120.0, "ring_contrast": 0.62, "figure_strength": 0.40, "coat": 0.9,
			"coat_roughness": 0.15, "roughness_min": 0.24, "roughness_max": 0.42, "paint": 0.0}),
		"brass": _surface(Color(0.90, 0.70, 0.34), {"roughness": 0.26, "tarnish": 0.30}),
		"brass_dark": _surface(Color(0.46, 0.33, 0.15), {"roughness": 0.42, "tarnish": 0.5}),
		"steel": _surface(Color(0.76, 0.77, 0.79), {"roughness": 0.30, "tarnish": 0.10, "streak": 0.95,
			"tarnish_color": Color(0.36, 0.36, 0.38), "roughness_var": 0.12}),
		"leather": _surface(Color(0.13, 0.060, 0.032), {"metallic": 0.0, "roughness": 0.60, "tarnish": 0.4,
			"tarnish_color": Color(0.07, 0.03, 0.018), "streak": 0.0, "grain_scale": 520.0, "bump": 1.4}),
		"eye": eye,
	}
	for s in mesh.mesh.get_surface_count():
		var src := mesh.mesh.surface_get_material(s)
		if src and mats.has(src.resource_name):
			mesh.set_surface_override_material(s, mats[src.resource_name])


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
	_action_next = ""
	_action_loop = loop
	_action_fade_out = fade_out


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
	# stride phase advances so the planted foot matches the ground speed
	var wj := clampf((speed - JOG_FROM) / (JOG_FULL_AT - JOG_FROM), 0.0, 1.0)
	wj = wj * wj * (3.0 - 2.0 * wj)
	var stride := lerpf(WALK_STRIDE, JOG_STRIDE, wj)
	var ww := clampf(speed / WALK_FULL_AT, 0.0, 1.0)
	if speed > 0.02:
		_phase = fposmod(_phase + dt * speed / (stride * maxf(ww, 0.05)), 1.0)
	_idle_t = fposmod(_idle_t + dt, anim.length("Idle"))
	return rm


# ------------------------------------------------------------------ pose

func _process(dt: float) -> void:
	_apply_pose(dt)


func _apply_pose(dt: float) -> void:
	var pos := _locomotion(_pose)
	if action != "":
		var p2 := anim.sample(action, action_t, _tmp)
		anim.blend(_pose, _tmp, action_weight)
		pos = pos.lerp(p2, action_weight)
	for b in _grip:
		_pose[b] = _grip[b]
	anim.apply(_pose, pos, dt)
	_mechanics(dt)


func _locomotion(into: Array[Quaternion]) -> Vector3:
	var ww := clampf(speed / WALK_FULL_AT, 0.0, 1.0)
	var wj := clampf((speed - JOG_FROM) / (JOG_FULL_AT - JOG_FROM), 0.0, 1.0)
	wj = wj * wj * (3.0 - 2.0 * wj)
	var pos := anim.sample("Idle", _idle_t, into)
	if ww > 0.0:
		var p := anim.sample("Walk", _phase * anim.length("Walk"), _tmp)
		if wj > 0.0:
			var pj := anim.sample("Jog_Fwd", _phase * anim.length("Jog_Fwd"), _tmp2)
			anim.blend(_tmp, _tmp2, wj)
			p = p.lerp(pj, wj)
		anim.blend(into, _tmp, ww)
		pos = pos.lerp(p, ww)
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

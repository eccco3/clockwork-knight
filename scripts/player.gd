class_name Player
extends CharacterBody3D
## The knight's controller: camera-relative movement, jump, dodge-roll and a three-hit sword
## combo. Rolls and attacks travel by the root motion of their clips, so feet stay planted.

const WALK_SPEED := 1.3
const RUN_SPEED := 4.6
const ACCEL := 20.0
const DECEL := 24.0
const AIR_ACCEL := 5.0
const TURN_RATE := 11.0
const JUMP_VELOCITY := 7.3
const ROLL_RATE := 1.12
const ROLL_SCALE := 0.74
const ROLL_START := 2.0 / 30.0
const ROLL_FREE_AT := 1.02           ## clip time after which movement may take over
const BUFFER := 0.22

const SWINGS: Array[String] = ["Sword_Regular_A", "Sword_Regular_B", "Sword_Regular_C"]
const RECOVER := {"Sword_Regular_A": "Sword_Regular_A_Rec", "Sword_Regular_B": "Sword_Regular_B_Rec"}
const FINISHER_FREE_AT := 1.05       ## clip time in the third swing after which she can act again

enum State { GROUND, AIR, ROLL, ATTACK }

@export var capture_mouse := true

var knight: Knight
var camera: CameraRig
var state := State.GROUND
var facing := 0.0
var walk_toggle := false

var _gravity: float = ProjectSettings.get_setting("physics/3d/default_gravity")
var _buf_attack := 0.0
var _buf_roll := 0.0
var _buf_jump := 0.0
var _combo := 0
var _queued := false
var _face_goal := 0.0
var _face_rate := TURN_RATE
var _move_basis := Basis.IDENTITY
var _air_t := 0.0
var _jumped := false
var _speed_s := 0.0
var _lean := Vector2.ZERO
var _prev_hvel := Vector3.ZERO


func _ready() -> void:
	add_to_group("player")
	setup_input()
	collision_layer = 2
	collision_mask = 1
	floor_snap_length = 0.25
	floor_max_angle = deg_to_rad(50.0)
	var col := CollisionShape3D.new()
	var cap := CapsuleShape3D.new()
	cap.radius = 0.30
	cap.height = 1.74
	col.shape = cap
	col.position.y = 0.87
	add_child(col)
	knight = Knight.new()
	knight.name = "Knight"
	add_child(knight)
	facing = rotation.y
	rotation.y = 0.0
	_face_goal = facing
	knight.rotation.y = facing
	camera = CameraRig.new()
	camera.name = "CameraRig"
	camera.target = self
	camera.yaw = facing + PI
	add_child(camera)
	# a faint lantern-warm fill that travels with the view, so she never sinks into silhouette
	var fill := OmniLight3D.new()
	fill.name = "Fill"
	fill.light_color = Color(1.0, 0.86, 0.70)
	fill.light_energy = 0.55
	fill.omni_range = 7.0
	fill.omni_attenuation = 1.2
	fill.light_specular = 0.4
	fill.shadow_enabled = false
	fill.position = Vector3(0.5, 0.5, 0.3)
	camera.camera.add_child(fill)
	if capture_mouse and OS.get_cmdline_user_args().is_empty() and DisplayServer.get_name() != "headless":
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


static func setup_input() -> void:
	if InputMap.has_action("move_forward"):
		return
	var keys := {
		"move_forward": [KEY_W, KEY_UP], "move_back": [KEY_S, KEY_DOWN],
		"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
		"jump": [KEY_SPACE], "roll": [KEY_SHIFT, KEY_Q, KEY_K], "attack": [KEY_J, KEY_F],
		"walk": [KEY_CTRL], "walk_toggle": [KEY_C],
		"look_left": [], "look_right": [], "look_up": [], "look_down": [],
	}
	var buttons := {"jump": [JOY_BUTTON_A], "roll": [JOY_BUTTON_B], "attack": [JOY_BUTTON_X, JOY_BUTTON_RIGHT_SHOULDER],
		"walk_toggle": [JOY_BUTTON_LEFT_STICK]}
	var mouse := {"attack": MOUSE_BUTTON_LEFT, "roll": MOUSE_BUTTON_RIGHT}
	var axes := {
		"move_left": [JOY_AXIS_LEFT_X, -1.0], "move_right": [JOY_AXIS_LEFT_X, 1.0],
		"move_forward": [JOY_AXIS_LEFT_Y, -1.0], "move_back": [JOY_AXIS_LEFT_Y, 1.0],
		"look_left": [JOY_AXIS_RIGHT_X, -1.0], "look_right": [JOY_AXIS_RIGHT_X, 1.0],
		"look_up": [JOY_AXIS_RIGHT_Y, -1.0], "look_down": [JOY_AXIS_RIGHT_Y, 1.0],
	}
	for a in keys:
		InputMap.add_action(a, 0.2)
		for k in keys[a]:
			var e := InputEventKey.new()
			e.physical_keycode = k
			InputMap.action_add_event(a, e)
		for b in buttons.get(a, []):
			var e := InputEventJoypadButton.new()
			e.button_index = b
			InputMap.action_add_event(a, e)
		if mouse.has(a):
			var e := InputEventMouseButton.new()
			e.button_index = mouse[a]
			InputMap.action_add_event(a, e)
		if axes.has(a):
			var e := InputEventJoypadMotion.new()
			e.axis = axes[a][0]
			e.axis_value = axes[a][1]
			InputMap.action_add_event(a, e)


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		if e.physical_keycode == KEY_ESCAPE:
			Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		elif e.physical_keycode == KEY_F11:
			var w := get_window()
			w.mode = Window.MODE_WINDOWED if w.mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN
	elif e is InputEventMouseButton and e.pressed and capture_mouse and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED \
			and e.button_index == MOUSE_BUTTON_LEFT:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		_buf_attack = 0.0
		get_viewport().set_input_as_handled()


func _dir(yaw: float) -> Vector3:
	return Vector3(sin(yaw), 0.0, cos(yaw))


func _physics_process(dt: float) -> void:
	_buf_attack = BUFFER if Input.is_action_just_pressed("attack") else _buf_attack - dt
	_buf_roll = BUFFER if Input.is_action_just_pressed("roll") else _buf_roll - dt
	_buf_jump = BUFFER if Input.is_action_just_pressed("jump") else _buf_jump - dt
	if Input.is_action_just_pressed("walk_toggle"):
		walk_toggle = not walk_toggle

	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back", 0.15)
	var amount := minf(input.length(), 1.0)
	var wish := camera.ground_direction(input)
	wish.y = 0.0
	wish = wish.normalized() if wish.length_squared() > 1e-6 else Vector3.ZERO
	var walking := Input.is_action_pressed("walk") != walk_toggle
	var top := WALK_SPEED if walking else RUN_SPEED
	# a part-tilted stick walks; the last third of its travel runs
	var want_speed := minf(top, WALK_SPEED) * minf(amount / 0.65, 1.0)
	if amount > 0.65:
		want_speed = lerpf(want_speed, top, (amount - 0.65) / 0.35)

	var rm := knight.tick(dt)
	var on_floor := is_on_floor()
	var hvel := Vector3(velocity.x, 0.0, velocity.z)

	match state:
		State.GROUND:
			var goal := wish * want_speed
			hvel = hvel.move_toward(goal, (ACCEL if goal.length() > hvel.length() else DECEL) * dt)
			_face_rate = TURN_RATE
			if wish != Vector3.ZERO:
				_face_goal = atan2(wish.x, wish.z)
			if knight.action == "Jump_Land" and hvel.length() > 1.6 and knight.action_t > 0.26:
				knight.stop(0.28)
			if not on_floor:
				_air_t += dt
				if _air_t > 0.14:
					_jumped = false
					state = State.AIR
					knight.play("Jump", 0.3, 0.0, 1.0, true)
			else:
				_air_t = 0.0
				if _buf_roll > 0.0:
					_start_roll(wish)
				elif _buf_attack > 0.0:
					_start_attack(0, wish)
				elif _buf_jump > 0.0:
					_start_jump()
		State.AIR:
			_air_t += dt
			hvel = hvel.move_toward(wish * maxf(want_speed, hvel.length() * minf(amount, 1.0)), AIR_ACCEL * dt)
			if wish != Vector3.ZERO:
				_face_goal = atan2(wish.x, wish.z)
			_face_rate = 5.0
			if on_floor and velocity.y <= 0.01:
				_land(hvel.length())
		State.ROLL:
			hvel = _move_basis * Vector3(rm.x, 0.0, rm.z) / dt * ROLL_SCALE
			_face_rate = 22.0
			if knight.action != "Roll":
				state = State.GROUND
			elif knight.action_t > ROLL_FREE_AT:
				if _buf_attack > 0.0:
					_start_attack(0, wish)
				elif wish != Vector3.ZERO:
					knight.stop(0.28)
					state = State.GROUND
		State.ATTACK:
			hvel = _move_basis * Vector3(rm.x, 0.0, rm.z) / dt
			_face_rate = 16.0
			_attack_logic(wish)

	if on_floor and velocity.y <= 0.0:
		velocity.y = -0.5
	else:
		velocity.y -= _gravity * dt
	velocity.x = hvel.x
	velocity.z = hvel.z
	move_and_slide()

	facing = lerp_angle(facing, _face_goal, 1.0 - exp(-_face_rate * dt))
	var real := get_real_velocity()
	var real_h := Vector3(real.x, 0.0, real.z)
	_speed_s = lerpf(_speed_s, real_h.length(), 1.0 - exp(-dt * 18.0))
	knight.speed = _speed_s
	knight.carry = lerpf(knight.carry, 0.55 if _speed_s > 0.3 else 0.25, 1.0 - exp(-dt * 6.0))
	# lean into acceleration and turns, in her own frame
	var acc := (real_h - _prev_hvel) / dt
	_prev_hvel = real_h
	var local := Basis(Vector3.UP, -facing) * acc
	var want_lean := Vector2.ZERO
	if state == State.GROUND and on_floor:
		want_lean = Vector2(clampf(local.z * 0.006, -0.10, 0.12), clampf(-local.x * 0.007, -0.14, 0.14))
	_lean = _lean.lerp(want_lean, 1.0 - exp(-dt * 7.0))
	knight.basis = Basis(Vector3.UP, facing) * Basis(Vector3.RIGHT, _lean.x) * Basis(Vector3.BACK, _lean.y)


func _start_jump() -> void:
	_buf_jump = 0.0
	_jumped = true
	_air_t = 0.0
	velocity.y = JUMP_VELOCITY
	state = State.AIR
	knight.play("Jump_Start", 0.07)
	knight.then("Jump", true)


func _land(hspeed: float) -> void:
	state = State.GROUND
	if _air_t < 0.25 and not _jumped:
		knight.stop(0.18)
	elif hspeed > 1.6:
		knight.play("Jump_Land", 0.07, 4.0 / 30.0, 1.5, false, 0.28)
		knight.action_weight = 0.6
	else:
		knight.play("Jump_Land", 0.07, 2.0 / 30.0, 1.25, false, 0.3)
		knight.action_weight = 0.8          # a lighter landing than the clip's deep crouch
	_air_t = 0.0
	_jumped = false


func _start_roll(wish: Vector3) -> void:
	_buf_roll = 0.0
	if wish != Vector3.ZERO:
		_face_goal = atan2(wish.x, wish.z)
	_move_basis = Basis(Vector3.UP, _face_goal)
	state = State.ROLL
	knight.play("Roll", 0.10, ROLL_START, ROLL_RATE, false, 0.25)


func _start_attack(i: int, wish: Vector3) -> void:
	_buf_attack = 0.0
	_queued = false
	_combo = i
	if wish != Vector3.ZERO:
		_face_goal = atan2(wish.x, wish.z)
	_move_basis = Basis(Vector3.UP, _face_goal)
	state = State.ATTACK
	var clip := SWINGS[i]
	knight.play(clip, 0.10 if i == 0 else 0.08, 0.0, 1.0, false, 0.35)
	if RECOVER.has(clip):
		knight.then(RECOVER[clip])


func _attack_logic(wish: Vector3) -> void:
	var cur := knight.action
	if cur == "":
		state = State.GROUND
		return
	var recovering := cur.ends_with("_Rec")
	if _buf_attack > 0.0 and _combo < SWINGS.size() - 1:
		_queued = true
	if recovering:
		if _queued:
			_start_attack(_combo + 1, wish)
		elif _buf_roll > 0.0:
			_start_roll(wish)
		elif _buf_jump > 0.0 and is_on_floor():
			_start_jump()
		elif knight.action_t > 0.18 and wish != Vector3.ZERO:
			knight.stop(0.3)
			state = State.GROUND
	elif _combo == SWINGS.size() - 1 and knight.action_t > FINISHER_FREE_AT:
		if _buf_attack > 0.0:
			_start_attack(0, wish)
		elif _buf_roll > 0.0:
			_start_roll(wish)
		elif _buf_jump > 0.0 and is_on_floor():
			_start_jump()
		elif wish != Vector3.ZERO:
			knight.stop(0.35)
			state = State.GROUND

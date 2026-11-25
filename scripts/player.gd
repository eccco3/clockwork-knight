class_name Player
extends CharacterBody3D
## The knight's controller: camera-relative movement, jump, dodge-roll, a three-hit sword combo
## and a slash in the air. Rolls and ground attacks travel by the root motion of their clips, so
## feet stay planted; the air slash keeps the jump's motion.
##
## She fights with a Health, a Stamina and a Strike. Swings and rolls spend stamina and need some
## left; her blade lands on any foe it passes through in a swing's hit window (Knight.BLOWS), and
## blows pass through her for most of a roll. An attack turns her toward the nearest foe within
## REACH of the way she aims it. A blow staggers her, and with no health left she collapses, the
## screen fades and the scene starts over.

const WALK_SPEED := 1.3
const RUN_SPEED := 4.6
const ACCEL := 32.0
const DECEL := 40.0
const CORNER_RATE := 14.0
const CORNER_MAX := deg_to_rad(130.0)
const AIR_ACCEL := 5.0
const TURN_RATE := 16.0
const JUMP_VELOCITY := 7.3
const ROLL_RATE := 1.12
const ROLL_SCALE := 0.74
const ROLL_START := 2.0 / 30.0
const ROLL_FREE_AT := 1.02           ## clip time after which movement may take over
const BUFFER := 0.22

const SWINGS: Array[String] = ["Sword_Regular_A", "Sword_Regular_B", "Sword_Regular_C"]
const RECOVER := {"Sword_Regular_A": "Sword_Regular_A_Rec", "Sword_Regular_B": "Sword_Regular_B_Rec"}
## In the air she plays the heavy combo's last blow, a leaping overhead cut, from its wind-up; past
## its follow-through she falls in the jump pose, but if she lands first she finishes it on the ground.
const AIR_SLASH := "Sword_Heavy_Combo"
const AIR_SLASH_FROM := 2.3
const AIR_SLASH_FALLS_AT := 3.1
## Clip time in a finishing blow after which she can act again.
const FREE_AT := {"Sword_Regular_C": 1.05, "Sword_Heavy_Combo": 3.0}

## She starts as one among equals: little stamina, and a sword that fells a grinner in three blows.
const HEALTH := 100.0
const STAMINA := 100.0
const COSTS := {"Sword_Regular_A": 16.0, "Sword_Regular_B": 18.0, "Sword_Regular_C": 26.0, "Sword_Heavy_Combo": 22.0,
	"Roll": 22.0}
const SWORD_DAMAGE := 10.0
const SWORD_SHOVE := 0.1
const SWORD_STOP := 0.06
## The Roll clip's seconds through which blows pass her by.
const DODGE := Vector2(0.12, 0.62)
## A foe this near, and this far off the way she aims, draws her attack round to it.
const REACH := 3.2
const REACH_ANGLE := deg_to_rad(70.0)
## Hit_Chest's seconds after which she can roll out of a stagger, and the seconds a blow's shove lasts.
const STAGGER_FREE_AT := 0.2
const SHOVE_TIME := 0.25
## Seconds from the killing blow until the screen starts to fade.
const FADE_AFTER := 1.9

enum State { GROUND, AIR, ROLL, ATTACK, AIR_ATTACK, HURT, DEAD }

var knight: Knight
var camera: CameraRig
var health := Health.new()
var stamina := Stamina.new(STAMINA)
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
var _strike := Strike.new(health)
var _blow := -1
var _stop := 0.0
var _shove := Vector3.ZERO
var _shove_t := 0.0
var _dead_t := 0.0


func _ready() -> void:
	add_to_group("player")
	collision_layer = Layers.CHARACTERS
	collision_mask = Layers.SCENERY | Layers.CHARACTERS
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
	health.name = "Health"
	health.most = HEALTH
	health.side = &"knight"
	add_child(health)
	health.hurt.connect(_on_hurt)
	health.died.connect(_on_died)
	add_child(Hurtbox.new(health, 0.3, 1.72))
	_strike.damage = SWORD_DAMAGE
	_strike.shove = SWORD_SHOVE
	_strike.stop = SWORD_STOP
	add_child(Hud.new(health, stamina))


func _dir(yaw: float) -> Vector3:
	return Vector3(sin(yaw), 0.0, cos(yaw))


## Attacks are read from events, so a click that something else consumes never reaches here.
func _unhandled_input(e: InputEvent) -> void:
	if e.is_action_pressed("attack", false, true):
		_buf_attack = BUFFER


func _physics_process(dt: float) -> void:
	_buf_attack -= dt
	_buf_roll = BUFFER if Input.is_action_just_pressed("roll") else _buf_roll - dt
	_buf_jump = BUFFER if Input.is_action_just_pressed("jump") else _buf_jump - dt
	if Input.is_action_just_pressed("walk_toggle"):
		walk_toggle = not walk_toggle
	stamina.tick(dt)
	if _stop > 0.0:
		# a blow landing holds her still a moment, as it does the one it lands on
		_stop -= dt
		return

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
			hvel = _run(hvel, wish * want_speed, dt)
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
			elif _buf_attack > 0.0:
				_start_air_attack(wish)
		State.AIR_ATTACK:
			_air_t += dt
			_face_rate = 16.0
			if on_floor and velocity.y <= 0.01:
				_land(hvel.length())
			elif knight.action_t > AIR_SLASH_FALLS_AT:
				state = State.AIR
				knight.play("Jump", 0.3, 0.0, 1.0, true)
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
		State.HURT:
			hvel = _shoved(dt)
			_face_rate = 0.0
			if knight.action != "Hit_Chest":
				state = State.GROUND
			elif knight.action_t > STAGGER_FREE_AT and on_floor and _buf_roll > 0.0:
				_start_roll(wish)
		State.DEAD:
			hvel = _shoved(dt)
			_face_rate = 0.0
			_dead_t += dt
			if _dead_t >= FADE_AFTER and _dead_t - dt < FADE_AFTER:
				App.restart()

	health.dodging = state == State.ROLL and knight.action == "Roll" \
		and knight.action_t >= DODGE.x and knight.action_t <= DODGE.y
	_land_blows()

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


## Ground velocity toward `goal`. Into a corner she swings her heading round at speed; past
## CORNER_MAX she brakes through a standstill, planting and pushing off the other way.
func _run(hvel: Vector3, goal: Vector3, dt: float) -> Vector3:
	var rate := ACCEL if goal.length() > hvel.length() else DECEL
	if hvel.length() < 0.5 or goal == Vector3.ZERO or hvel.angle_to(goal) > CORNER_MAX:
		return hvel.move_toward(goal, rate * dt)
	var heading := hvel.normalized().slerp(goal.normalized(), 1.0 - exp(-CORNER_RATE * dt))
	return heading * move_toward(hvel.length(), goal.length(), rate * dt)


func _start_jump() -> void:
	_buf_jump = 0.0
	_jumped = true
	_air_t = 0.0
	velocity.y = JUMP_VELOCITY
	state = State.AIR
	knight.play("Jump_Start", 0.07)
	knight.then("Jump", true)


func _land(hspeed: float) -> void:
	var stepped_off := _air_t < 0.25 and not _jumped
	_air_t = 0.0
	_jumped = false
	if state == State.AIR_ATTACK:
		# she finishes the slash on the ground, her legs taking it up where it has got to
		state = State.ATTACK
		knight.land_legs()
		return
	state = State.GROUND
	if stepped_off:
		knight.stop(0.18)
	elif hspeed > 1.6:
		knight.play("Jump_Land", 0.07, 4.0 / 30.0, 1.5, false, 0.28)
		knight.action_weight = 0.6
	else:
		knight.play("Jump_Land", 0.07, 2.0 / 30.0, 1.25, false, 0.3)
		knight.action_weight = 0.8          # a lighter landing than the clip's deep crouch


## Commits her heading to the stick, or to where she faces, for a move driven by root motion.
func _aim(wish: Vector3) -> void:
	if wish != Vector3.ZERO:
		_face_goal = atan2(wish.x, wish.z)
	_move_basis = Basis(Vector3.UP, _face_goal)


## The way to aim an attack: toward the nearest living foe within REACH and REACH_ANGLE of the way she
## would aim it otherwise, if there is one.
func _toward_foe(wish: Vector3) -> Vector3:
	var ahead := wish if wish != Vector3.ZERO else _dir(facing)
	var best := wish
	var nearest := INF
	for other: Health in get_tree().get_nodes_in_group(Health.FIGHTERS):
		if not other.alive() or not health.foe(other):
			continue
		var to := (other.figure().global_position - global_position) * Vector3(1, 0, 1)
		var off := ahead.angle_to(to)
		var far := to.length() * (1.0 + off)
		if to.length() > 0.01 and to.length() < REACH and off < REACH_ANGLE and far < nearest:
			nearest = far
			best = to.normalized()
	return best


func _start_roll(wish: Vector3) -> void:
	_buf_roll = 0.0
	if not stamina.spend(COSTS["Roll"]):
		return
	_aim(wish)
	state = State.ROLL
	knight.play("Roll", 0.10, ROLL_START, ROLL_RATE, false, 0.25)


func _start_attack(i: int, wish: Vector3) -> void:
	_buf_attack = 0.0
	_queued = false
	if not stamina.spend(COSTS[SWINGS[i]]):
		return
	_combo = i
	_aim(_toward_foe(wish))
	state = State.ATTACK
	var clip := SWINGS[i]
	knight.play(clip, 0.10 if i == 0 else 0.08, 0.0, 1.0, false, 0.35)
	if RECOVER.has(clip):
		knight.then(RECOVER[clip])


## The jump keeps carrying her; only her upper body swings until she lands.
func _start_air_attack(wish: Vector3) -> void:
	_buf_attack = 0.0
	_queued = false
	if not stamina.spend(COSTS[AIR_SLASH]):
		return
	_combo = SWINGS.size() - 1          # a finishing blow: no swing follows it
	_aim(_toward_foe(wish))
	state = State.AIR_ATTACK
	knight.play(AIR_SLASH, 0.10, AIR_SLASH_FROM, 1.0, false, 0.35)
	knight.air_legs = true


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
	elif knight.action_t > FREE_AT.get(cur, INF):
		if _buf_attack > 0.0:
			_start_attack(0, wish)
		elif _buf_roll > 0.0:
			_start_roll(wish)
		elif _buf_jump > 0.0 and is_on_floor():
			_start_jump()
		elif wish != Vector3.ZERO:
			knight.stop(0.35)
			state = State.GROUND


## Sweeps her blade through the hit window of the swing she is in, and holds still a moment when it lands.
func _land_blows() -> void:
	var blow := knight.blow() if state == State.ATTACK or state == State.AIR_ATTACK else -1
	if blow >= 0:
		if blow != _blow:
			_strike.begin()
		for hit in _strike.sweep(knight.blade()):
			_stop = maxf(_stop, hit.stop)
			camera.shake(0.2)
	_blow = blow


func _on_hurt(hit: Hit) -> void:
	_take(hit)
	state = State.HURT
	# heavier blows stagger her longer
	knight.play("Hit_Chest", 0.05, 0.0, clampf(1.15 - hit.damage * 0.018, 0.7, 1.0), false, 0.3)


func _on_died(hit: Hit) -> void:
	_take(hit)
	state = State.DEAD
	health.dodging = false
	knight.play("Hit_Chest", 0.05, 0.0, 0.8, false)
	knight.then(KnightCollapse.NAME, false, true)
	knight.wound_down = true
	_dead_t = 0.0


func _take(hit: Hit) -> void:
	_stop = hit.stop
	_shove = hit.way * hit.shove * 2.0 / SHOVE_TIME
	_shove_t = SHOVE_TIME
	_queued = false
	_buf_attack = 0.0
	camera.shake(0.3 + hit.damage * 0.015)
	Burst.splinters(get_parent(), hit.at, hit.way)


## The velocity of the last blow's shove, slowing evenly to nothing over SHOVE_TIME.
func _shoved(dt: float) -> Vector3:
	_shove_t = maxf(_shove_t - dt, 0.0)
	return _shove * _shove_t / SHOVE_TIME

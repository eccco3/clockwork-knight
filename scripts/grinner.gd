class_name Grinner
extends Node3D
## A grinner: the model of its kind, whose own AnimationTree (built by tools/grinner/import_grinner.gd) blends
## its idle into its waddle or run and plays its moves, and the travelling that their root motion does.
##
## pounce() leaps ahead; the walking grinner's swipe() and the scuttler's bite() strike in place. Each winds up
## first. flinch() cuts into whatever it is doing, unless it is shrugging blows off, as shrugging() says: in a
## leap, and late in a swipe or bite. striking() is true while the claws or teeth can hit. die() cuts into
## anything and stays down.
##
## It fights `target`, by default the nearest foe within SIGHT: it waddles straight at it, pounces from mid range
## and swipes (the scuttler bites) up close, each attack ready again a while after it ends, and never waits its
## turn behind other grinners. While an attack's hit window is open, the paths of its ATTACKS edges land the blow
## on whichever foe they cross. A blow makes it flinch, or, while it shrugs blows off or flinches already, only
## jolts its upper body. It keeps clear of other figures' bodies and stands on the ground beneath it.

const GAIT := &"parameters/Gait/blend_position"
const PLAYBACK := &"parameters/playback"
## The markers on its moves' clips: their hit window is open from HIT until RECOVER, and they shrug blows off
## from SHRUG until HEED, or until their end if they have no HEED.
const HIT := &"hit"
const RECOVER := &"recover"
const SHRUG := &"shrug"
const HEED := &"heed"

const SIDE := &"grinners"
## The knight's sword fells one in three blows.
const HEALTH := 30.0
## Its body, for blocking others and for taking blows: an upright capsule.
const GIRTH := 0.3
const HEIGHT := 1.25
const SIGHT := 18.0
## Seconds between looks round for a nearer foe.
const LOOK_EVERY := 0.5
## It waddles in until its target is STAND_IN metres inside the reach of its attacks from close up, and stands its
## ground until the target is out of that reach.
const STAND_IN := 0.2
## Radians a second it turns at a full waddle, and how far off its target it may start an attack.
const TURN := 2.2
const FACING := 0.5
## Seconds after any attack before it starts the next.
const BREATHER := Vector2(0.35, 0.8)
## Each attack by move: from reach.x to reach.y metres away (centre to centre) it may start it, and again `rest`
## seconds (give or take a fifth) after it ends. While it winds up it turns after its target at `track` radians a
## second. A leap is stretched or shrunk to end `lands` metres short of where its target stands as it leaves the
## ground; 0 keeps the clip's own travel. Its `edges`, pairs of bones `thickness` thick, strike while its hit
## window is open.
const ATTACKS := {
	&"Swipe": {"reach": Vector2(0.0, 1.15), "rest": 1.5, "damage": 12.0, "shove": 0.3, "stop": 0.07, "track": 4.5,
		"lands": 0.0, "thickness": 0.06, "edges": [[&"forearm_l", &"middle_3_l"], [&"forearm_r", &"middle_3_r"]]},
	&"Bite": {"reach": Vector2(0.0, 1.1), "rest": 1.3, "damage": 12.0, "shove": 0.25, "stop": 0.07, "track": 5.0,
		"lands": 0.0, "thickness": 0.14, "edges": [[&"head", &"jaw"]]},
	&"Pounce": {"reach": Vector2(2.6, 5.0), "rest": 6.0, "damage": 22.0, "shove": 0.7, "stop": 0.1, "track": 3.0,
		"lands": 0.55, "thickness": 0.07, "edges": [[&"forearm_r", &"middle_3_r"], [&"forearm_l", &"middle_3_l"]]},
}
## How its upper body jolts when a blow does not make it flinch: radians a second a blow throws it, how stiffly it
## springs back, how soon it settles, and the share of the jolt each bone takes.
const JOLT := 5.5
const JOLT_SPRING := 180.0
const JOLT_DAMPING := 13.0
const JOLTED := {&"spine": 0.3, &"chest": 0.45, &"neck": 0.15, &"head": 0.3}
## Seconds a blow's shove lasts.
const SHOVE_TIME := 0.2
## Radians a second it turns, as it falls, to face the blow that felled it.
const FALL_TURN := 12.0

## Its kind: the walking grinner, or the scuttler on all fours.
@export var model: PackedScene = preload("res://assets/models/grinner.glb")
## 0 stands idle, 1 waddles or runs at full pace.
@export_range(0.0, 1.0) var gait := 0.0:
	set(value):
		gait = value
		if _tree:
			_tree[GAIT] = gait
## Whether it seeks out foes and fights them. dev/crowd.gd turns it off to steer its crowd itself.
@export var fights := true
## Whom it fights, a foe's Health. When it has none or that one dies, it takes the nearest foe within SIGHT.
var target: Health
var health := Health.new()

var _tree: AnimationTree
var _clips: AnimationPlayer
var _playback: AnimationNodeStateMachinePlayback
var _skel: Skeleton3D
var _cadence := Cadence.new()
var _body := AnimatableBody3D.new()
var _strike := Strike.new(health)
var _rng := RandomNumberGenerator.new()
var _clock := 0.0
var _look := 0.0
var _ready_at := {}
var _next_attack := 0.0
var _near := 0.0
var _warp := 1.0
var _striking_was := false
var _stop := 0.0
var _shove := Vector3.ZERO
var _shove_t := 0.0
var _fall_yaw := NAN
var _jolt := Vector2.ZERO
var _jolt_rate := Vector2.ZERO
var _clear := PhysicsShapeQueryParameters3D.new()
var _ground := PhysicsRayQueryParameters3D.new()


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	var figure := model.instantiate()
	add_child(figure)
	for v: VisualInstance3D in figure.find_children("*", "VisualInstance3D", true, false):
		v.layers = Layers.CHARACTERS
	_tree = figure.get_node("AnimationTree")
	_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	_clips = _tree.get_node(_tree.anim_player)
	_playback = _tree[PLAYBACK]
	_tree[GAIT] = gait
	_skel = figure.find_children("*", "Skeleton3D", true, false)[0]
	for attack: StringName in ATTACKS:
		if _clips.has_animation(attack) and ATTACKS[attack].reach.x == 0.0:
			_near = maxf(_near, ATTACKS[attack].reach.y)
	health.name = "Health"
	health.most = HEALTH
	health.side = SIDE
	add_child(health)
	health.hurt.connect(_on_hurt)
	health.died.connect(_on_died)
	add_child(Hurtbox.new(health, GIRTH + 0.05, HEIGHT))
	_body.name = "Body"
	_body.sync_to_physics = false
	_body.collision_layer = Layers.CHARACTERS
	_body.collision_mask = 0
	var capsule := CapsuleShape3D.new()
	capsule.radius = GIRTH
	capsule.height = HEIGHT
	var shape := CollisionShape3D.new()
	shape.shape = capsule
	shape.position.y = HEIGHT * 0.5
	_body.add_child(shape)
	add_child(_body)
	var ball := SphereShape3D.new()
	ball.radius = GIRTH
	_clear.shape = ball
	_clear.collision_mask = Layers.CHARACTERS
	_clear.exclude = [_body.get_rid()]
	_ground.collision_mask = Layers.SCENERY
	_rng.seed = hash(global_position)
	_look = _rng.randf() * LOOK_EVERY


## Thinks, animates and travels at its Cadence. Far away or out of view it steps every few frames, and a move
## asked for there begins up to three frames late. A blow landing on it or by it holds it still a moment.
func _process(dt: float) -> void:
	if _stop > 0.0:
		_stop -= dt
		return
	var step := _cadence.step(self, dt)
	if step <= 0.0:
		return
	_clock += step
	if not health.alive():
		if not is_nan(_fall_yaw):
			rotation.y = rotate_toward(rotation.y, _fall_yaw, FALL_TURN * step)
	elif fights:
		_fight(step)
	_tree.advance(step)
	_travel(step)
	_jolt_body(step)
	_land_blows()


func pounce() -> void:
	_playback.travel(&"Pounce")


func swipe() -> void:
	_playback.travel(&"Swipe")


func bite() -> void:
	_playback.travel(&"Bite")


func flinch() -> void:
	if _flinches():
		_playback.travel(&"Flinch")


func die() -> void:
	_playback.travel(&"Death")


## The move being played, or &"Gait" while it stands or waddles.
func move() -> StringName:
	return _playback.get_current_node()


## True from the start of an attack until its first marker.
func winding_up() -> bool:
	if not _clips.has_animation(move()):
		return false
	var clip := _clips.get_animation(move())
	return clip.get_marker_names().size() > 0 and clip.get_prev_marker(_playback.get_current_play_position()) == &""


## True while the hit window of an attack is open.
func striking() -> bool:
	return _within(HIT, RECOVER)


## True while a move shrugs blows off, taking them with only a jolt.
func shrugging() -> bool:
	return _within(SHRUG, HEED)


## Whether flinch() would cut in: not while it shrugs blows off, flinches already or lies dead.
func _flinches() -> bool:
	return not shrugging() and move() != &"Flinch" and move() != &"Death"


## True once the current move has passed its marker `opens`, until it passes `closes` or, without one, ends. A move
## fading back into the gait at its end is still the current move here.
func _within(opens: StringName, closes: StringName) -> bool:
	var playing := move()
	var now := _playback.get_current_play_position()
	if playing == &"Gait" and _playback.get_fading_from_node() != &"":
		playing = _playback.get_fading_from_node()
		now = _playback.get_fading_from_play_position()
	if not _clips.has_animation(playing):
		return false
	var clip := _clips.get_animation(playing)
	return clip.has_marker(opens) and now >= clip.get_marker_time(opens) \
		and (not clip.has_marker(closes) or now < clip.get_marker_time(closes))


## One step of fighting: keeps a target, closes on it and starts an attack when one is ready, in reach and faced,
## and while winding up turns after the target and aims its leap.
func _fight(step: float) -> void:
	_look -= step
	if _look <= 0.0 or (target and not target.alive()):
		_look = LOOK_EVERY
		_choose_target()
	var to := Vector3.ZERO
	if target:
		to = (target.figure().global_position - global_position) * Vector3(1, 0, 1)
	var now := move()
	if now == &"Gait":
		_close_on(to, step)
	elif ATTACKS.has(now) and winding_up() and to != Vector3.ZERO:
		var attack: Dictionary = ATTACKS[now]
		_turn(to, attack.track, step)
		if attack.lands > 0.0:
			_warp = clampf((to.length() - attack.lands) / _travelled(now), 0.5, 1.25)


func _choose_target() -> void:
	if target and target.alive() and global_position.distance_to(target.figure().global_position) < SIGHT * 1.5:
		return
	target = null
	var nearest := SIGHT
	for other: Health in get_tree().get_nodes_in_group(Health.FIGHTERS):
		var far := global_position.distance_to(other.figure().global_position)
		if other.alive() and health.foe(other) and far < nearest:
			nearest = far
			target = other


## Waddles at the target until it is well within reach, and starts whichever attack is ready, in reach and faced.
func _close_on(to: Vector3, step: float) -> void:
	if to == Vector3.ZERO:
		gait = move_toward(gait, 0.0, step * 2.0)
		return
	var far := to.length()
	var off := absf(angle_difference(rotation.y, atan2(to.x, to.z)))
	for attack: StringName in ATTACKS:
		var reach: Vector2 = ATTACKS[attack].reach
		if _clips.has_animation(attack) and far >= reach.x and far <= reach.y and off < FACING \
				and _clock >= _ready_at.get(attack, 0.0) and _clock >= _next_attack:
			_begin(attack)
			return
	var walking := far > _near - (STAND_IN if gait >= 0.5 else 0.0)
	gait = move_toward(gait, 1.0 if walking else 0.0, step * 2.5)
	_turn(to, TURN * (0.35 + 0.65 * gait), step)


func _begin(attack: StringName) -> void:
	_playback.travel(attack)
	var takes := _clips.get_animation(attack).length
	_ready_at[attack] = _clock + takes + ATTACKS[attack].rest * _rng.randf_range(0.8, 1.2)
	_next_attack = _clock + takes + _rng.randf_range(BREATHER.x, BREATHER.y)
	_warp = 1.0
	gait = 0.0


func _turn(to: Vector3, rate: float, step: float) -> void:
	rotation.y = rotate_toward(rotation.y, atan2(to.x, to.z), rate * step)


## How far a move's root travels from its start to its end.
func _travelled(clip_name: StringName) -> float:
	var clip := _clips.get_animation(clip_name)
	for t in clip.get_track_count():
		if clip.track_get_type(t) == Animation.TYPE_POSITION_3D and clip.track_get_path(t).get_concatenated_subnames() == "root":
			return maxf(clip.position_track_interpolate(t, clip.length).distance_to(clip.position_track_interpolate(t, 0.0)), 0.1)
	return 1.0


## Travels by the root motion of what it plays, its leap stretched to land where it aimed, and by any shove; then
## steps out of other figures' bodies and stands on the ground.
func _travel(step: float) -> void:
	var travel := global_basis * _tree.get_root_motion_position()
	if ATTACKS.get(move(), {}).get("lands", 0.0) > 0.0:
		travel *= _warp
	_shove_t = maxf(_shove_t - step, 0.0)
	global_position += travel + _shove * (_shove_t / SHOVE_TIME) * step
	if health.alive():
		_keep_clear()
	_stand()


## Steps half way out of any other figure's body it has come into, so that crowds ease apart.
func _keep_clear() -> void:
	_clear.transform = Transform3D(Basis.IDENTITY, global_position + Vector3.UP * HEIGHT * 0.5)
	var pairs := get_world_3d().direct_space_state.collide_shape(_clear, 8)
	var out := Vector3.ZERO
	for i in range(0, pairs.size(), 2):
		out += (pairs[i + 1] - pairs[i]) * Vector3(1, 0, 1)
	global_position += out * 0.5


func _stand() -> void:
	_ground.from = global_position + Vector3.UP
	_ground.to = global_position + Vector3.DOWN * 2.0
	var found := get_world_3d().direct_space_state.intersect_ray(_ground)
	if found:
		global_position.y = found.position.y


## Lands the current attack's blow on each foe its edges cross while its hit window is open.
func _land_blows() -> void:
	var open := striking() and health.alive()
	if open:
		if not _striking_was:
			var attack: Dictionary = ATTACKS[move()]
			_strike.damage = attack.damage
			_strike.shove = attack.shove
			_strike.stop = attack.stop
			_strike.thickness = attack.thickness
			_strike.begin()
		for hit in _strike.sweep(_edges()):
			_stop = maxf(_stop, hit.stop)
	_striking_was = open


## The striking edges of the current attack where its bones are now.
func _edges() -> PackedVector3Array:
	var edges := PackedVector3Array()
	for pair: Array in ATTACKS[move()].edges:
		for bone: StringName in pair:
			edges.append(_skel.global_transform * _skel.get_bone_global_pose(_skel.find_bone(bone)).origin)
	return edges


func _on_hurt(hit: Hit) -> void:
	_take(hit, 1.0)
	if _flinches():
		flinch()
	else:
		var way := global_basis.inverse() * hit.way
		_jolt_rate += Vector2(way.x, way.z).normalized() * JOLT


func _on_died(hit: Hit) -> void:
	_take(hit, 1.6)
	_stop *= 1.5
	# it reels back from the blow that fells it
	_fall_yaw = atan2(-hit.way.x, -hit.way.z)
	_body.collision_layer = 0
	gait = 0.0
	die()


func _take(hit: Hit, bleeds: float) -> void:
	_stop = hit.stop
	_shove = hit.way * hit.shove * 2.0 / SHOVE_TIME
	_shove_t = SHOVE_TIME
	Burst.ichor(get_parent(), hit.at, hit.way, bleeds)


## Springs the upper body back from a jolt, bending it by what is left of the jolt on top of the clip's pose.
func _jolt_body(step: float) -> void:
	if _jolt == Vector2.ZERO and _jolt_rate == Vector2.ZERO:
		return
	var left := step
	while left > 0.0:
		var dt := minf(left, 1.0 / 120.0)
		_jolt_rate += (-JOLT_SPRING * _jolt - JOLT_DAMPING * _jolt_rate) * dt
		_jolt += _jolt_rate * dt
		left -= dt
	if _jolt.length() < 0.002 and _jolt_rate.length() < 0.02:
		_jolt = Vector2.ZERO
		_jolt_rate = Vector2.ZERO
		return
	var axis := Vector3.UP.cross(Vector3(_jolt.x, 0.0, _jolt.y)).normalized()
	for bone_name: StringName in JOLTED:
		var bone := _skel.find_bone(bone_name)
		var turn := Quaternion(_skel.get_bone_global_pose(bone).basis.get_rotation_quaternion().inverse() * axis,
			_jolt.length() * JOLTED[bone_name])
		_skel.set_bone_pose_rotation(bone, _skel.get_bone_pose_rotation(bone) * turn)

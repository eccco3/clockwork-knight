class_name Grinner
extends Node3D
## A grinner: the model, whose own AnimationTree (built by tools/grinner/import_grinner.gd) blends its idle
## into its waddle and plays its moves, and the travelling that their root motion does.
##
## pounce() leaps four metres ahead and swipe() strikes in place; each winds up first, and only then can
## flinch() cut in. striking() is true while the claws can hit. die() cuts into anything and stays down.

const MODEL := preload("res://assets/models/grinner.glb")
const GAIT := &"parameters/Gait/blend_position"
const PLAYBACK := &"parameters/playback"
const HIT := &"hit"

## 0 stands idle, 1 waddles at full pace.
@export_range(0.0, 1.0) var gait := 0.0:
	set(value):
		gait = value
		if _tree:
			_tree[GAIT] = gait

var _tree: AnimationTree
var _clips: AnimationPlayer
var _playback: AnimationNodeStateMachinePlayback


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	var model := MODEL.instantiate()
	add_child(model)
	for v: VisualInstance3D in model.find_children("*", "VisualInstance3D", true, false):
		v.layers = Layers.CHARACTERS
	_tree = model.get_node("AnimationTree")
	_clips = _tree.get_node(_tree.anim_player)
	_playback = _tree[PLAYBACK]
	_tree[GAIT] = gait


func _process(_dt: float) -> void:
	global_position += global_basis * _tree.get_root_motion_position()


func pounce() -> void:
	_playback.travel(&"Pounce")


func swipe() -> void:
	_playback.travel(&"Swipe")


func flinch() -> void:
	_playback.travel(&"Flinch")


func die() -> void:
	_playback.travel(&"Death")


## The move being played, or &"Gait" while it stands or waddles.
func move() -> StringName:
	return _playback.get_current_node()


## True from the start of an attack until its first marker: the time a hit makes it flinch.
func winding_up() -> bool:
	return _clips.has_animation(move()) and _clips.get_animation(move()).get_marker_names().size() > 0 and _phase() == &""


## True while the hit window of an attack is open.
func striking() -> bool:
	return _phase() == HIT


## The marker the current move has last passed: the phase it is in.
func _phase() -> StringName:
	if not _clips.has_animation(move()):
		return &""
	return _clips.get_animation(move()).get_prev_marker(_playback.get_current_play_position())

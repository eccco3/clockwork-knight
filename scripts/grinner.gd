class_name Grinner
extends Node3D
## A grinner: the model, whose own AnimationTree blends its idle into its waddle, and the walking that
## the waddle's root motion does.

const MODEL := preload("res://assets/models/grinner.glb")
const GAIT := &"parameters/blend_position"

## 0 stands idle, 1 waddles at full pace.
@export_range(0.0, 1.0) var gait := 0.0:
	set(value):
		gait = value
		if _tree:
			_tree[GAIT] = gait

var _tree: AnimationTree


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	var model := MODEL.instantiate()
	add_child(model)
	for v: VisualInstance3D in model.find_children("*", "VisualInstance3D", true, false):
		v.layers = Layers.CHARACTERS
	_tree = model.get_node("AnimationTree")
	_tree[GAIT] = gait


func _process(_dt: float) -> void:
	global_position += global_basis * _tree.get_root_motion_position()

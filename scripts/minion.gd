class_name Minion
extends Node3D
## A minion: a small clockwork soldier of the knight's side, in pale wood, black lacquer and the crimson of
## the hall's banner, with a short spear. The root of his imported model, which dresses its materials in his
## colours. Every minion wears the same materials, made once. He is not rigged yet, and stands as his build
## posed him.

static var _looks: Dictionary[String, Material] = {}


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	if _looks.is_empty():
		_looks = {
			"wood": Looks.oiled_wood(Color(0.74, 0.55, 0.33), Color(0.52, 0.34, 0.17)),
			"wood_dark": Looks.lacquered_wood(Color(0.085, 0.062, 0.048), Color(0.030, 0.022, 0.018)),
			"lacquer": Looks.lacquered_wood(Color(0.46, 0.065, 0.050), Color(0.33, 0.042, 0.038)),
			"brass": Looks.brass(Color(0.90, 0.70, 0.34)),
			"steel": Looks.steel(Color(0.76, 0.77, 0.79), Color(0.36, 0.36, 0.38)),
			"leather": Looks.leather(Color(0.13, 0.060, 0.032), Color(0.07, 0.03, 0.018)),
		}
	for mesh: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		Looks.dress(mesh, _looks)
		mesh.layers = Layers.CHARACTERS

class_name Rosalyn
extends Node3D
## Rosalyn, a clockwork woman of lacquered tulipwood in a smocked dress: the root of her imported
## model, which dresses her wood, brass and eyes in her colours. Her dress and hair carry their own
## baked textures. Her AnimationTree (built by tools/rosalyn/import_rosalyn.gd) loops her Idle, and
## she blinks over it now and then.

const FACE_PAINT := preload("res://assets/textures/rosalyn/face_paint.png")
const FACE_PAINT_PLACEMENT := preload("res://assets/textures/rosalyn/face_paint.json")
const BLINKS := Vector2(1.5, 6.0)  ## seconds from one blink to the next, at random between these
const TWICE := 0.15  ## the chance that a blink comes again straight after
const AGAIN := 0.35  ## seconds from a blink to its repeat: just longer than the Blink clip

var _tree: AnimationTree
var _next_blink := 0.0


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	var looks: Dictionary[String, Material] = {
		"wood": Looks.lacquered_wood(Color(0.86, 0.70, 0.50), Color(0.70, 0.50, 0.32)),
		"wood_face": Looks.face_wood(Color(0.88, 0.73, 0.54), Color(0.77, 0.59, 0.41),
			FACE_PAINT, FACE_PAINT_PLACEMENT, true),
		"lacquer": Looks.lacquered_wood(Color(0.93, 0.80, 0.42), Color(0.78, 0.60, 0.24)),
		"brass": Looks.brass(Color(0.90, 0.70, 0.34)),
		"eye": Looks.glass_eye(Color(0.11, 0.26, 0.46), Color(0.48, 0.66, 0.80), 0.40, 0.345),
	}
	for mesh: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		Looks.dress(mesh, looks)
		mesh.layers = Layers.CHARACTERS
	_tree = $AnimationTree
	_next_blink = randf_range(BLINKS.x, BLINKS.y)


func _process(delta: float) -> void:
	_next_blink -= delta
	if _next_blink <= 0.0:
		_tree.set("parameters/Blink/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
		_next_blink = AGAIN if randf() < TWICE else randf_range(BLINKS.x, BLINKS.y)

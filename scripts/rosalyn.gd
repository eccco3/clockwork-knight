class_name Rosalyn
extends Node3D
## Rosalyn, a clockwork woman of lacquered tulipwood in a smocked dress: the root of her imported
## model, which dresses her wood, brass and eyes in her colours and paints her brows over her face,
## where their bones carry them. Her dress and hair carry their own baked textures. Her AnimationTree
## (built by tools/rosalyn/import_rosalyn.gd) loops her Idle, and she blinks over it now and then.
##
## `say` gives her a line: she talks through her speech clips until it is spoken, crossing from one to
## another every few seconds, or keeps to the one it names, and the line goes to the scene's Subtitles.
## While the knight is near and before her, she turns her head and eyes to the knight (Gaze).

const FACE_PAINT := preload("res://assets/textures/rosalyn/face_paint.png")
const FACE_PAINT_PLACEMENT := preload("res://assets/textures/rosalyn/face_paint.json")
const BROW := preload("res://assets/textures/rosalyn/brow.png")
const BROW_PLACEMENT := preload("res://assets/textures/rosalyn/brow.json")
const FACE_WOOD: Array[Color] = [Color(0.88, 0.73, 0.54), Color(0.77, 0.59, 0.41)]
const BLINKS := Vector2(1.5, 6.0)  ## seconds from one blink to the next, at random between these
const TWICE := 0.15  ## the chance that a blink comes again straight after
const AGAIN := 0.35  ## seconds from a blink to its repeat: just longer than the Blink clip
const NAME := "Rosalyn"
const WORDS := 2.6  ## words she says a second, when a line has no voice to time it
const AFTER := 0.5  ## seconds she holds a line after its words
const TALK_FADE := 0.6  ## seconds to fall into talking, and out of it
const GESTURES := Vector2(2.5, 5.0)  ## seconds from one speech clip to the next, at random between these
const NEAR := 4.5  ## metres within which she turns to the knight
const ASIDE := deg_to_rad(100.0)  ## how far round from her front the knight may stand
const KNIGHT_EYES := 1.55  ## above the knight's feet
const ATTEND_FADE := 0.8  ## seconds to turn to the knight, or away
const MOUTH := Vector3(0.0, 1.57, 0.1)  ## where her voice comes from

var _tree: AnimationTree
var _gaze: Gaze
var _voice: AudioStreamPlayer3D
var _speech: PackedStringArray
var _manner := ""
var _next_blink := 0.0
var _talking := 0.0
var _next_gesture := 0.0


func _ready() -> void:
	add_to_group(Layers.CHARACTER_GROUP)
	var looks: Dictionary[String, Material] = {
		"wood": Looks.lacquered_wood(Color(0.86, 0.70, 0.50), Color(0.70, 0.50, 0.32)),
		"wood_face": Looks.face_wood(FACE_WOOD[0], FACE_WOOD[1], FACE_PAINT, FACE_PAINT_PLACEMENT, true),
		"lacquer": Looks.lacquered_wood(Color(0.93, 0.80, 0.42), Color(0.78, 0.60, 0.24)),
		"brass": Looks.brass(Color(0.90, 0.70, 0.34)),
		"eye": Looks.glass_eye(Color(0.11, 0.26, 0.46), Color(0.48, 0.66, 0.80), 0.40, 0.345),
	}
	for mesh: MeshInstance3D in find_children("*", "MeshInstance3D", true, false):
		Looks.dress(mesh, looks)
		mesh.layers = Layers.CHARACTERS
	var skeleton: Skeleton3D = find_children("*", "Skeleton3D", true, false)[0]
	_paint_brows(skeleton)
	_gaze = Gaze.new()
	_gaze.influence = 0.0
	skeleton.add_child(_gaze)
	_voice = AudioStreamPlayer3D.new()
	_voice.position = MOUTH
	add_child(_voice)
	_tree = $AnimationTree
	var gestures: AnimationNodeTransition = (_tree.tree_root as AnimationNodeBlendTree).get_node("Speech")
	for k in gestures.get_input_count():
		_speech.append(gestures.get_input_name(k))
	_next_blink = randf_range(BLINKS.x, BLINKS.y)


## She speaks `line`, for as long as `voice` plays or else as its words take, in the manner of the speech
## clip it names, or else in all of them by turns.
func say(line: String, voice: AudioStream = null, manner := "") -> void:
	var seconds := voice.get_length() if voice else line.split(" ", false).size() / WORDS
	if voice:
		_voice.stream = voice
		_voice.play()
	_talking = seconds + AFTER
	_manner = manner
	_next_gesture = 0.0
	get_tree().call_group(Subtitles.GROUP, "show_line", NAME, line, _talking)


func is_talking() -> bool:
	return _talking > 0.0


## The speech clips a line may name as its manner.
func manners() -> PackedStringArray:
	return _speech


func _process(delta: float) -> void:
	_blink(delta)
	_talk(delta)
	_attend(delta)


func _blink(delta: float) -> void:
	_next_blink -= delta
	if _next_blink <= 0.0:
		_tree.set("parameters/Blink/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
		_next_blink = AGAIN if randf() < TWICE else randf_range(BLINKS.x, BLINKS.y)


func _talk(delta: float) -> void:
	_talking = maxf(_talking - delta, 0.0)
	var amount: float = _tree.get("parameters/Talk/blend_amount")
	_tree.set("parameters/Talk/blend_amount", move_toward(amount, 1.0 if is_talking() else 0.0, delta / TALK_FADE))
	_next_gesture -= delta
	if is_talking() and _next_gesture <= 0.0:
		var now: String = _tree.get("parameters/Speech/current_state")
		var others := Array(_speech).filter(func(clip: String) -> bool: return clip != now)
		_tree.set("parameters/Speech/transition_request", _manner if _manner else others.pick_random())
		_next_gesture = randf_range(GESTURES.x, GESTURES.y)


func _attend(delta: float) -> void:
	var knight := get_tree().get_first_node_in_group("player") as Node3D
	if knight:
		_gaze.target = knight.global_position + Vector3.UP * KNIGHT_EYES
	_gaze.influence = move_toward(_gaze.influence, 1.0 if knight and _before_her(knight) else 0.0, delta / ATTEND_FADE)


func _before_her(node: Node3D) -> bool:
	var at := global_transform.affine_inverse() * node.global_position
	return Vector2(at.x, at.z).length() < NEAR and absf(atan2(at.x, at.z)) < ASIDE


## Each brow is a decal on her face that its bone carries: square to her face at rest, it looks into it from
## the front, its texture's top up and its first column nearest her nose, mirrored on her right.
func _paint_brows(skeleton: Skeleton3D) -> void:
	var size: Array = BROW_PLACEMENT.data["size"]
	for side: float in [1.0, -1.0]:
		var follow := BoneAttachment3D.new()
		follow.bone_name = "brow_l" if side > 0.0 else "brow_r"
		skeleton.add_child(follow)
		var brow := Decal.new()
		brow.texture_albedo = BROW
		brow.modulate = FACE_WOOD[0].lerp(FACE_WOOD[1], 0.5)
		brow.size = Vector3(size[0], size[1], size[2])
		brow.upper_fade = 0.0
		brow.lower_fade = 0.0
		brow.cull_mask = Layers.CHARACTERS
		var rest := skeleton.get_bone_global_rest(skeleton.find_bone(follow.bone_name))
		var square := Transform3D(Basis(Vector3(side, 0.0, 0.0), Vector3.BACK, Vector3.DOWN), rest.origin)
		brow.transform = rest.affine_inverse() * square
		follow.add_child(brow)

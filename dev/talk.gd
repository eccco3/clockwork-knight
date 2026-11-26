extends "res://dev/stage.gd"
## Rosalyn speaking with the knight, on the bare stage: she stands before the knight and turns to her while
## she is near, and T has her say the next of her voiced lines (assets/voices/rosalyn), with subtitles. M changes
## how her mouth moves with them, as Mouth tries it: still, on a jaw, swapped lip pieces or pivoted ones. V looks
## closely at her face, or back. 1 to 4 hold her to one of her speech clips, 0 lets her vary them again.
## dev/drive.tscn reaches the same through call:voice:<line number>, call:mouth:<still|jaw|swapped|pivoted>,
## call:say:<line> for a line without a voice, and call:speak:<clip>, which has her say all the lines in one
## breath, unvoiced, in that clip's manner, or in all of them by turns for call:speak:any; call:reseed:<n>
## makes her blinks and gestures the same from run to run.

const ROSALYN := preload("res://assets/models/rosalyn.glb")
const VOICES := "res://assets/voices/rosalyn/"
const LINES := preload("res://assets/voices/rosalyn/lines.json")
const KEYS := "T  next line      M  mouth: %s      V  close up      1-4  only %s      0  all of them"
const CLOSE := [Vector3(0.0, 1.60, 1.80), Vector3(0.0, 1.59, 2.1)]  ## the close camera's eye, and where it looks

var _rosalyn: Rosalyn
var _manners: PackedStringArray
var _manner := ""
var _line := 0
var _keys: Label
var _close: Camera3D


func _ready() -> void:
	super()
	_rosalyn = ROSALYN.instantiate()
	_rosalyn.name = "Rosalyn"
	_rosalyn.position = Vector3(0.0, 0.0, 2.2)
	_rosalyn.rotation.y = PI
	add_child(_rosalyn)
	var subtitles := Subtitles.new()
	subtitles.name = "Subtitles"
	add_child(subtitles)
	_manners = _rosalyn.manners()
	_close = Camera3D.new()
	_close.fov = 30.0
	add_child(_close)
	_close.look_at_from_position(CLOSE[0], CLOSE[1])
	var layer := CanvasLayer.new()
	layer.name = "Keys"
	_keys = Label.new()
	_keys.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	_keys.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_keys.position += Vector2(-24, 20)
	_keys.add_theme_color_override("font_color", Color(1.0, 0.93, 0.82))
	_keys.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	_keys.add_theme_constant_override("outline_size", 4)
	layer.add_child(_keys)
	add_child(layer)
	_label()


func say(line: String) -> void:
	_rosalyn.say(line, null, _manner)


## She says the line of that number with its voice.
func voice(number: String) -> void:
	var lines: Dictionary = LINES.data["lines"]
	var key: String = lines.keys()[int(number) % lines.size()]
	_rosalyn.say(lines[key], load(VOICES + key + ".wav"), _manner)


func speak(manner: String) -> void:
	_manner = manner if manner in _manners else ""
	say(" ".join(LINES.data["lines"].values()))


func reseed(number: String) -> void:
	seed(int(number))


## Her mouth moves the way of that name: still, jaw, swapped or pivoted.
func mouth(style: String) -> void:
	_rosalyn.mouth.style = Mouth.Style.keys().find(style.to_upper()) as Mouth.Style
	_label()


func _label() -> void:
	_keys.text = KEYS % [String(Mouth.Style.keys()[_rosalyn.mouth.style]).to_lower(), " / ".join(_manners)]


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	var k: int = e.physical_keycode
	if k == KEY_T:
		voice(str(_line))
		_line += 1
	elif k == KEY_M:
		mouth(Mouth.Style.keys()[(_rosalyn.mouth.style + 1) % Mouth.Style.size()])
	elif k == KEY_V:
		if _close.current:
			get_node("Player").camera.camera.make_current()
		else:
			_close.make_current()
	elif k == KEY_0:
		_manner = ""
	elif k >= KEY_1 and k < KEY_1 + _manners.size():
		_manner = _manners[k - KEY_1]

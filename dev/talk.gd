extends "res://dev/stage.gd"
## Rosalyn speaking with the knight, on the bare stage: she stands before the knight and turns to her while
## she is near, and T has her say the next of LINES, with subtitles. 1 to 4 hold her to one of her speech
## clips, 0 lets her vary them again. dev/drive.tscn reaches the same through call:say:<line> and
## call:speak:<clip>, which has her say all of LINES in one breath, in that clip's manner, or in all of
## them by turns for call:speak:any.

const ROSALYN := preload("res://assets/models/rosalyn.glb")
const LINES: Array[String] = [
	"Good evening. I wondered when you would come back.",
	"Sit by the fire a while. The night is long, and the road will keep.",
	"Do you hear that? Every clock in the hall has stopped at the same minute.",
	"No. I will not open the east doors, not tonight, and not for anyone.",
	"Perhaps I was made for waiting. Perhaps it is the thing I do best.",
	"Tell me, what did you see out there, past the fog?",
]
const KEYS := "T  next line      1-4  only %s      0  all of them"

var _rosalyn: Rosalyn
var _manners: PackedStringArray
var _manner := ""
var _line := 0


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
	var layer := CanvasLayer.new()
	layer.name = "Keys"
	var keys := Label.new()
	keys.text = KEYS % " / ".join(_manners)
	keys.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	keys.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	keys.position += Vector2(-24, 20)
	keys.add_theme_color_override("font_color", Color(1.0, 0.93, 0.82))
	keys.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	keys.add_theme_constant_override("outline_size", 4)
	layer.add_child(keys)
	add_child(layer)


func say(line: String) -> void:
	_rosalyn.say(line, null, _manner)


func speak(manner: String) -> void:
	_manner = manner if manner in _manners else ""
	say(" ".join(LINES))


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	var k: int = e.physical_keycode
	if k == KEY_T:
		say(LINES[_line])
		_line = (_line + 1) % LINES.size()
	elif k == KEY_0:
		_manner = ""
	elif k >= KEY_1 and k < KEY_1 + _manners.size():
		_manner = _manners[k - KEY_1]

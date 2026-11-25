class_name Subtitles
extends CanvasLayer
## What is said, at the foot of the screen: each line with its speaker's name, for as long as it is spoken,
## then fading. A scene that wants subtitles holds one; speakers reach it through its group:
## get_tree().call_group(Subtitles.GROUP, "show_line", speaker, line, seconds).

const GROUP := &"subtitles"
const FADE := 0.4
const RAISED := 110  ## pixels above the foot of the screen

var _label: Label
var _left := 0.0


func _ready() -> void:
	add_to_group(GROUP)
	_label = Label.new()
	_label.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_label.grow_horizontal = Control.GROW_DIRECTION_BOTH
	_label.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_label.position.y -= RAISED
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_label.custom_minimum_size.x = 900.0
	_label.add_theme_font_size_override("font_size", 26)
	_label.add_theme_color_override("font_color", Color(1.0, 0.95, 0.86))
	_label.add_theme_color_override("font_outline_color", Color(0.05, 0.03, 0.02, 0.9))
	_label.add_theme_constant_override("outline_size", 8)
	_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_label.visible = false
	add_child(_label)


func show_line(speaker: String, line: String, seconds: float) -> void:
	_label.text = "%s:  %s" % [speaker, line]
	_left = seconds
	_label.visible = true


func _process(delta: float) -> void:
	_left -= delta
	_label.modulate.a = clampf(1.0 + _left / FADE, 0.0, 1.0)
	_label.visible = _left > -FADE

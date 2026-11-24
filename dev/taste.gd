extends Harness
## Teaches the face tools the dev's taste: shows two faces from tools/faces/pool side by side and asks
## which he prefers. tools/faces/rate.py chooses the pairs and saves each answer at once, so he can
## close the window at any time and carry on later.
##
##   godot --path . res://dev/taste.tscn
##
## Left arrow or A, or a click on the left face, picks it; right arrow or D the right one; Backspace
## takes back the last answer. auto=<n> answers n pairs at random and quits, shot=<png> photographs
## the screen before quitting, answers=<jsonl> keeps the answers elsewhere: for tests, on quiet.py.

const PYTHON := "res://toolchain/blender/4.5/python/bin/python.exe"
const RATE := "res://tools/faces/rate.py"
const KEYS := "←  or  A   ·   click a face   ·   D  or  →          Backspace  undo"
const BACKGROUND := Color(0.11, 0.12, 0.14)

var _pipe: FileAccess
var _errors: FileAccess
var _faces: Array[TextureRect] = []
var _status: Label


func _ready() -> void:
	_build()
	var command := ["-I", ProjectSettings.globalize_path(RATE)]
	if args.has("answers"):
		command += ["--answers", args["answers"]]
	var rate := OS.execute_with_pipe(ProjectSettings.globalize_path(PYTHON), command)
	if rate.is_empty():
		_fail("could not start " + RATE)
		return
	_pipe = rate["stdio"]
	_errors = rate["stderr"]
	_read()
	if args.has("auto"):
		_auto(int(args["auto"]))


func _build() -> void:
	RenderingServer.set_default_clear_color(BACKGROUND)
	var layer := CanvasLayer.new()
	add_child(layer)
	var page := VBoxContainer.new()
	page.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	page.add_theme_constant_override("separation", 18)
	layer.add_child(page)
	_status = _label(page, 18, Color(0.75, 0.75, 0.72))
	var pair := HBoxContainer.new()
	pair.size_flags_vertical = Control.SIZE_EXPAND_FILL
	pair.add_theme_constant_override("separation", 24)
	page.add_child(pair)
	for side in ["left", "right"]:
		var face := TextureRect.new()
		face.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		face.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		face.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		face.gui_input.connect(func(e: InputEvent):
			if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
				_pick(side))
		pair.add_child(face)
		_faces.append(face)
	_label(page, 18, Color(1.0, 0.93, 0.82)).text = KEYS


func _label(parent: Control, size: int, colour: Color) -> Label:
	var label := Label.new()
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", colour)
	parent.add_child(label)
	return label


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	match e.physical_keycode:
		KEY_LEFT, KEY_A:
			_pick("left")
		KEY_RIGHT, KEY_D:
			_pick("right")
		KEY_BACKSPACE:
			_pick("undo")


func _pick(what: String) -> void:
	if _pipe == null:
		return
	_pipe.store_line(what)
	_pipe.flush()
	_read()


## Shows the pair rate.py sends.
func _read() -> void:
	var line := _pipe.get_line()
	var shown = JSON.parse_string(line) if not line.is_empty() else null
	if not shown is Dictionary:
		_fail(_errors.get_as_text() if line.is_empty() else line)
		return
	for i in 2:
		_faces[i].texture = ImageTexture.create_from_image(Image.load_from_file(shown[["left", "right"][i]]))
	_status.text = "%d answers      direction settled %d%%      re-shown pairs answered alike: %d of %d" % [
		shown["answers"], roundi(100.0 * shown["settled"]), shown["agreed"], shown["repeats"]]


func _fail(message: String) -> void:
	_pipe = null
	_status.text = "rate.py stopped: " + message
	push_error(_status.text)


func _auto(count: int) -> void:
	for i in count:
		await get_tree().process_frame
		_pick("left" if randf() < 0.5 else "right")
	for i in 10:
		await get_tree().process_frame
	if args.has("shot"):
		save(await grab(), args["shot"])
	get_tree().quit()

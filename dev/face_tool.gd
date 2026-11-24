class_name FaceTool
extends Harness
## What the dev's face tools share: a session in tools/faces/ that reads his answers on stdin and replies
## to each with one JSON line, which the tool shows; a page with a status line, the faces and the keys.
## The session saves every answer at once, so he can close the window at any time and carry on later.
##
## auto=<n> gives n random answers and quits, shot=<png> photographs the screen before quitting: for
## tests, on quiet.py.

const PYTHON := "toolchain/blender/4.5/python/bin/python.exe"
const BACKGROUND := Color(0.11, 0.12, 0.14)

var status: Label
var _pipe: FileAccess
var _errors: FileAccess


## Starts the session script (res://...) with its arguments and shows its first reply.
func start(script: String, arguments: Array) -> void:
	var python := _python()
	var session := OS.execute_with_pipe(python, ["-I", ProjectSettings.globalize_path(script)] + arguments) \
			if not python.is_empty() else {}
	if session.is_empty():
		fail("could not start " + script)
		return
	_pipe = session["stdio"]
	_errors = session["stderr"]
	_read()


## The toolchain's Python, in the project or, from a worktree, a folder above it.
static func _python() -> String:
	var dir := ProjectSettings.globalize_path("res://").simplify_path()
	while true:
		if FileAccess.file_exists(dir.path_join(PYTHON)):
			return dir.path_join(PYTHON)
		if dir.get_base_dir() == dir:
			return ""
		dir = dir.get_base_dir()
	return ""


## Sends an answer and shows the reply.
func send(answer: String) -> void:
	if _pipe == null:
		return
	_pipe.store_line(answer)
	_pipe.flush()
	_read()


## Shows a reply of the session; each tool lays it out.
func show(_reply: Dictionary) -> void:
	pass


func _read() -> void:
	var line := _pipe.get_line()
	var reply = JSON.parse_string(line) if not line.is_empty() else null
	if not reply is Dictionary:
		fail(_errors.get_as_text() if line.is_empty() else line)
		return
	show(reply)


func fail(message: String) -> void:
	_pipe = null
	status.text = "%s stopped: %s" % [name, message]
	push_error(status.text)


## The page: the status line on top, then `middle`, then the keys.
func page(middle: Control, keys: String) -> void:
	RenderingServer.set_default_clear_color(BACKGROUND)
	var layer := CanvasLayer.new()
	add_child(layer)
	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	column.add_theme_constant_override("separation", 18)
	layer.add_child(column)
	status = label(column, 18, Color(0.75, 0.75, 0.72))
	middle.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(middle)
	label(column, 18, Color(1.0, 0.93, 0.82)).text = keys


func label(parent: Control, size: int, colour: Color) -> Label:
	var text := Label.new()
	text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	text.add_theme_font_size_override("font_size", size)
	text.add_theme_color_override("font_color", colour)
	parent.add_child(text)
	return text


## A picture of faces that fills its share of the page.
func face() -> TextureRect:
	var picture := TextureRect.new()
	picture.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	picture.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	picture.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return picture


## Shows the picture file at `path` in `picture`, or nothing for "".
func shows(picture: TextureRect, path: String) -> void:
	picture.texture = ImageTexture.create_from_image(Image.load_from_file(path)) if not path.is_empty() else null


## With auto=<n>: n answers picked at random from `answers`, then the shot and quit.
func auto(answers: Array) -> void:
	if not args.has("auto"):
		return
	for i in int(args["auto"]):
		await get_tree().process_frame
		send(answers.pick_random())
	for i in 10:
		await get_tree().process_frame
	if args.has("shot"):
		save(await grab(), args["shot"])
	get_tree().quit()

class_name FaceTool
extends Harness
## What the dev's face tools share: a session in tools/faces/ that reads his requests on stdin and replies
## to each with one JSON line, which the tool shows, and may send more, with "notice" set, as work it does
## in the background moves on; a page with a status line, the faces and the keys. The page never waits on
## the session, and a request goes only once the last is answered, so each answer is to what he sees. The
## session saves every answer at once, so he can close the window at any time and carry on later.
##
## For tests, on quiet.py: auto=<n> gives up to n random answers, one each pace=<seconds> or as soon as
## the last is answered, stopping once the status line holds until=<text>; then key=<name> presses that
## key and waits for until=<text> again; shot=<png> photographs the screen; then it quits.

const PYTHON := "toolchain/blender/4.5/python/bin/python.exe"
const BACKGROUND := Color(0.11, 0.12, 0.14)

var status: Label
var keys: Label
var _pipe: FileAccess
var _errors: FileAccess
var _pid := 0
var _received := PackedByteArray()
var _asked := 0


## Starts the session script (res://...) with its arguments; its first reply shows when it comes.
func start(script: String, arguments: Array) -> void:
	var python := _python()
	var session := OS.execute_with_pipe(python, ["-I", ProjectSettings.globalize_path(script)] + arguments, false) \
			if not python.is_empty() else {}
	if session.is_empty():
		fail("could not start " + script)
		return
	_pipe = session["stdio"]
	_errors = session["stderr"]
	_pid = session["pid"]
	_asked = 1


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


## Sends a request, unless the last is still unanswered.
func send(request: String) -> void:
	if _pipe == null or _asked > 0:
		return
	_pipe.store_line(request)
	_pipe.flush()
	_asked += 1


## Shows a reply or notice of the session; each tool lays it out.
func show(_reply: Dictionary) -> void:
	pass


func _process(_delta: float) -> void:
	if _pipe == null:
		return
	var running := OS.is_process_running(_pid)
	_received.append_array(_drain(_pipe))
	var end := _received.find(10)
	while end >= 0 and _pipe != null:
		_receive(_received.slice(0, end).get_string_from_utf8())
		_received = _received.slice(end + 1)
		end = _received.find(10)
	if not running and _pipe != null:
		fail(_drain(_errors).get_string_from_utf8().strip_edges())


## What the pipe holds now, without waiting for more.
static func _drain(pipe: FileAccess) -> PackedByteArray:
	var all := PackedByteArray()
	var chunk := pipe.get_buffer(65536)
	while not chunk.is_empty():
		all.append_array(chunk)
		chunk = pipe.get_buffer(65536)
	return all


func _receive(line: String) -> void:
	var reply = JSON.parse_string(line)
	if not reply is Dictionary:
		fail(line)
		return
	if not reply.get("notice", false):
		_asked -= 1
	show(reply)


func fail(message: String) -> void:
	_pipe = null
	_asked = 0
	status.text = "%s stopped: %s" % [name, message]
	push_error(status.text)


## The page: the status line on top, then `middle`, then the keys.
func page(middle: Control, keys_text: String) -> void:
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
	keys = label(column, 18, Color(1.0, 0.93, 0.82))
	keys.text = keys_text


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


## With auto=<n>: the test the header describes, its answers picked at random from `answers`.
func auto(answers: Array) -> void:
	if not args.has("auto"):
		return
	var pace := float(args.get("pace", "0"))
	for i in int(args["auto"]):
		await _until(func(): return _asked == 0)
		if _pipe == null or _seen():
			break
		send(answers.pick_random())
		await get_tree().create_timer(pace).timeout
	if args.has("key"):
		await _until(func(): return _asked == 0)
		var press := InputEventKey.new()
		press.physical_keycode = OS.find_keycode_from_string(args["key"])
		press.pressed = true
		Input.parse_input_event(press)
		await get_tree().process_frame
		await _until(func(): return _pipe == null or not args.has("until") or _seen())
	await _until(func(): return _asked == 0)
	for i in 10:
		await get_tree().process_frame
	if args.has("shot"):
		save(await grab(), args["shot"])
	get_tree().quit()


func _seen() -> bool:
	return args.has("until") and status.text.contains(args["until"])


func _until(done: Callable) -> void:
	while not done.call():
		await get_tree().process_frame

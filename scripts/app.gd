extends Node
## Keys that belong to the application rather than to play, and the controls hint. Esc frees the
## cursor and a click captures it again, F11 toggles fullscreen and H hides the hint. The cursor
## is captured for mouse look while an orbit camera is in play. The hint shows while a playable
## scene is running: one whose root has metadata/playable, its title in the playtest picker.

const PLAYABLE := &"playable"
const HINT := "WASD  move      Ctrl  walk  (C toggles)      Space  jump      Shift / RMB  dodge-roll      LMB  attack ×3\n" \
	+ "Mouse  look      Wheel  zoom      Esc  free cursor      F11  fullscreen      H  hide this\n" \
	+ "Gamepad:  stick move · right stick look · A jump · B roll · X attack"

var _cameras := 0
var _hint: Label
var _hint_t := 0.0
var _hint_on := true


func _ready() -> void:
	_build_hint()
	get_tree().node_added.connect(_on_node_added)
	# the scene Godot starts with is in the tree before autoloads are ready
	if get_tree().current_scene:
		_on_node_added(get_tree().current_scene)


func _on_node_added(node: Node) -> void:
	if node is CameraRig:
		_add_camera.call_deferred(node)
	if node.has_meta(PLAYABLE) and node == get_tree().current_scene:	# not under a harness's scene
		_hint.visible = true
		_hint.modulate.a = 1.0
		_hint_t = 0.0
		node.tree_exiting.connect(func(): _hint.visible = false)


func _add_camera(camera: CameraRig) -> void:
	if not camera.is_inside_tree() or not _in_play(camera):
		return
	_cameras += 1
	camera.tree_exiting.connect(func(): _cameras -= 1)
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


## Only real play may capture the cursor: Windows confines a captured cursor with ClipCursor, which
## reaches the dev's screen even from quiet.py's hidden desktop. Harnesses such as dev/drive.tscn
## and dev/shot.tscn load the game under a scene of their own, so a camera is in play only when the
## running scene itself built it, in a windowed run without user arguments.
func _in_play(camera: CameraRig) -> bool:
	var scene := camera.get_parent()
	while scene and scene.scene_file_path.is_empty():
		scene = scene.get_parent()
	return scene == get_tree().current_scene and OS.get_cmdline_user_args().is_empty() \
		and DisplayServer.get_name() != "headless"


func _build_hint() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_hint = Label.new()
	_hint.name = "Hint"
	_hint.text = HINT
	_hint.visible = false
	_hint.add_theme_font_size_override("font_size", 15)
	_hint.add_theme_color_override("font_color", Color(1.0, 0.93, 0.82))
	_hint.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	_hint.add_theme_constant_override("shadow_offset_x", 1)
	_hint.add_theme_constant_override("shadow_offset_y", 1)
	_hint.add_theme_constant_override("line_spacing", 4)
	_hint.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	_hint.position += Vector2(24, -24)
	_hint.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_hint.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(_hint)


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventKey and e.pressed and not e.echo:
		match e.physical_keycode:
			KEY_ESCAPE:
				Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
			KEY_F11:
				var w := get_window()
				w.mode = Window.MODE_WINDOWED if w.mode == Window.MODE_FULLSCREEN else Window.MODE_FULLSCREEN
			KEY_H:
				_hint_on = not _hint_on
				_hint_t = 0.0


## The recapturing click arrives in _input, ahead of the scene's _unhandled_input, so it is
## consumed before the player can read it as an attack.
func _input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT and _cameras > 0 \
			and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		get_viewport().set_input_as_handled()


func _process(dt: float) -> void:
	_hint_t += dt
	# full strength at first, then it settles back so it does not sit on the picture
	var want := 0.0 if not _hint_on else (1.0 if _hint_t < 14.0 else 0.38)
	_hint.modulate.a = lerpf(_hint.modulate.a, want, 1.0 - exp(-dt * 3.0))

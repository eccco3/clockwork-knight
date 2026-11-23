extends Node3D
## The playable scene: the hall, the knight at its spawn marker, and a small controls hint.

const HALL := preload("res://scenes/hall.tscn")

var player: Player
var _hint: Label
var _hint_t := 0.0
var _hint_on := true


func _ready() -> void:
	var hall := HALL.instantiate()
	add_child(hall)
	player = Player.new()
	player.name = "Player"
	var spawn := hall.get_node_or_null("PlayerSpawn") as Node3D
	var at := spawn.position if spawn else Vector3.ZERO
	player.position = at
	# face down the hall
	player.rotation.y = atan2(-at.x, -at.z) if Vector2(at.x, at.z).length() > 0.5 else 0.0
	add_child(player)
	_build_hint()


func _build_hint() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	_hint = Label.new()
	_hint.name = "Hint"
	_hint.text = "WASD  move      Ctrl  walk  (C toggles)      Space  jump      Shift / RMB  dodge-roll      LMB  attack ×3\n" \
		+ "Mouse  look      Wheel  zoom      Esc  free cursor      F11  fullscreen      H  hide this\n" \
		+ "Gamepad:  stick move · right stick look · A jump · B roll · X attack"
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
	if e is InputEventKey and e.pressed and not e.echo and e.physical_keycode == KEY_H:
		_hint_on = not _hint_on
		_hint_t = 0.0


func _process(dt: float) -> void:
	_hint_t += dt
	# full strength at first, then it settles back so it does not sit on the picture
	var want := 0.0 if not _hint_on else (1.0 if _hint_t < 14.0 else 0.38)
	_hint.modulate.a = lerpf(_hint.modulate.a, want, 1.0 - exp(-dt * 3.0))

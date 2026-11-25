extends FaceTool
## Teaches the face tools the dev's taste in the faces of one sex: shows two from that sex's pool in
## tools/faces/pool, or its latest refinement round, side by side and asks which he prefers;
## tools/faces/rate.py chooses the pairs.
##
##   godot --path . res://dev/taste_women.tscn      or taste_men.tscn
##
## Left arrow or A, or a click on the left face, picks it; right arrow or D the right one; Backspace
## takes back the last answer. answers=<jsonl> keeps the answers elsewhere, for tests.

const RATE := "res://tools/faces/rate.py"
const KEYS := "←  or  A   ·   click a face   ·   D  or  →          Backspace  undo"

@export_enum("women", "men") var sex := "women"
var _faces: Array[TextureRect] = []


func _ready() -> void:
	var pair := HBoxContainer.new()
	pair.add_theme_constant_override("separation", 24)
	for side in ["left", "right"]:
		var picture := face()
		picture.gui_input.connect(func(e: InputEvent):
			if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
				send(side))
		pair.add_child(picture)
		_faces.append(picture)
	page(pair, KEYS)
	start(RATE, ["--sex", sex] + (["--answers", args["answers"]] if args.has("answers") else []))
	auto(["left", "right"])


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	match e.physical_keycode:
		KEY_LEFT, KEY_A:
			send("left")
		KEY_RIGHT, KEY_D:
			send("right")
		KEY_BACKSPACE:
			send("undo")


func show(shown: Dictionary) -> void:
	for i in 2:
		shows(_faces[i], shown[["left", "right"][i]])
	status.text = "%s, %s:  %d answers      direction settled %d%%      re-shown pairs answered alike: %d of %d" % [
		sex.capitalize(), shown["set"], shown["answers"], roundi(100.0 * shown["settled"]), shown["agreed"], shown["repeats"]]

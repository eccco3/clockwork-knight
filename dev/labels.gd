extends FaceTool
## Learns which faces read as women and which as men: shows the dev one face of the label set in
## tools/faces/pool/labels at a time, from the front and turned, and he labels it with one key;
## tools/faces/label.py keeps the labels, from which tools/faces/sexes.py learns the direction.
##
##   blender --background --python tools/faces/build_faces.py -- --labels     renders the set, once
##   godot --path . res://dev/labels.tscn
##
## W woman, A androgynous, M man, U unclear; Backspace takes back the last label. labels=<jsonl>
## keeps the labels elsewhere, for tests.

const LABEL := "res://tools/faces/label.py"
const KINDS := {KEY_W: "woman", KEY_A: "androgynous", KEY_M: "man", KEY_U: "unclear"}
const KEYS := "W  woman      A  androgynous      M  man      U  unclear          Backspace  undo"

var _face: TextureRect


func _ready() -> void:
	_face = face()
	page(_face, KEYS)
	start(LABEL, ["--labels", args["labels"]] if args.has("labels") else [])
	auto(KINDS.values())


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	if e.physical_keycode in KINDS:
		send(KINDS[e.physical_keycode])
	elif e.physical_keycode == KEY_BACKSPACE:
		send("undo")


func show(shown: Dictionary) -> void:
	shows(_face, shown["face"])
	var counts := "woman %d   androgynous %d   man %d   unclear %d" % [
		shown["woman"], shown["androgynous"], shown["man"], shown["unclear"]]
	if shown["face"].is_empty():
		status.text = "All %d faces labelled, thank you.      %s" % [shown["faces"], counts]
	else:
		status.text = "Face labels:  %d of about %d      %s" % [shown["labelled"], shown["target"], counts]

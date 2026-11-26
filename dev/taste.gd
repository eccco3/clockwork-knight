extends FaceTool
## Teaches the face tools the dev's taste in the faces of one sex: shows two from that sex's pool in
## tools/faces/pool, or its latest refinement round, side by side and asks which he prefers;
## tools/faces/rate.py chooses the pairs, and renders the next round in the background once a set has had
## its answers, switching to it when it is rendered.
##
##   godot --path . res://dev/taste_women.tscn      or taste_men.tscn
##
## Left arrow or A, or a click on the left face, picks it; right arrow or D the right one; Backspace
## takes back the last answer. B shows the best faces learnt so far, rendering them again first if he has
## answered since, and B again goes back to rating. answers=<jsonl> keeps the answers elsewhere, for tests.

const RATE := "res://tools/faces/rate.py"
const KEYS := "←  or  A   ·   click a face   ·   D  or  →          Backspace  undo          B  best faces"
const BEST_KEYS := "B  back to rating"
const NEW := 5                                  # answers on a round during which the status line calls it new

@export_enum("women", "men") var sex := "women"
var _faces: Array[TextureRect] = []
var _pair := HBoxContainer.new()
var _best: TextureRect
var _best_from = null                           # how many answers the best faces shown were learnt from
var _shown := {}


func _ready() -> void:
	_pair.add_theme_constant_override("separation", 24)
	for side in ["left", "right"]:
		var picture := face()
		picture.gui_input.connect(func(e: InputEvent):
			if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
				send(side))
		_pair.add_child(picture)
		_faces.append(picture)
	_best = face()
	_best.visible = false
	var middle := MarginContainer.new()
	middle.add_child(_pair)
	middle.add_child(_best)
	page(middle, KEYS)
	start(RATE, ["--sex", sex] + (["--answers", args["answers"]] if args.has("answers") else []))
	auto(["left", "right"])


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	if e.physical_keycode == KEY_B:
		_toggle_best()
	elif not _best.visible:
		match e.physical_keycode:
			KEY_LEFT, KEY_A:
				send("left")
			KEY_RIGHT, KEY_D:
				send("right")
			KEY_BACKSPACE:
				send("undo")


func _toggle_best() -> void:
	_best.visible = not _best.visible
	_pair.visible = not _best.visible
	keys.text = BEST_KEYS if _best.visible else KEYS
	if _best.visible:
		send("best")
	if not _shown.is_empty():
		show(_shown)


func show(shown: Dictionary) -> void:
	if _pair_of(shown) != _pair_of(_shown):
		for i in 2:
			shows(_faces[i], shown[["left", "right"][i]])
	_shown = shown
	var best: Dictionary = shown["best"]
	var stale: bool = shown["answers"] > 0 and best["answers"] != shown["answers"]
	if _best.visible and best["answers"] != _best_from:
		shows(_best, best["picture"])
		_best_from = best["answers"]
	if _best.visible and stale and not best["rendering"] and best["failed"].is_empty():
		send("best")
	status.text = _best_status(shown, stale) if _best.visible else _rating_status(shown)


## The pair a reply shows: a round's pictures keep their paths when the next round replaces it.
static func _pair_of(shown: Dictionary) -> Array:
	return [shown.get("set"), shown.get("left"), shown.get("right")]


func _rating_status(shown: Dictionary) -> String:
	var next: Dictionary = shown["next"]
	var round := "next round after %d more answers" % (shown["quota"] - shown["here"])
	if not next["failed"].is_empty():
		round = "next round failed: " + next["failed"]
	elif next["rendering"]:
		round = "next round rendering: %d of %d faces" % [next["rendered"], next["faces"]] if next["faces"] > 0 \
				else "next round: drawing its faces"
	elif next["faces"] > 0 and next["rendered"] == next["faces"]:
		round = "next round ready: it starts with your next answer"
	elif shown["set"].begins_with("refine") and shown["here"] < NEW:
		round = "a new round: these faces are drawn from all your answers"
	return "%s, %s:  %d answers, %d here      foreseen: %d of your last %d      re-shown pairs answered alike: %d of %d      %s" % [
		sex.capitalize(), shown["set"].replace("refine", "round"), shown["answers"], shown["here"],
		shown["foreseen"], shown["recent"], shown["agreed"], shown["repeats"], round]


func _best_status(shown: Dictionary, stale: bool) -> String:
	var best: Dictionary = shown["best"]
	if not best["failed"].is_empty():
		return "Best %s failed: %s" % [sex, best["failed"]]
	if shown["answers"] == 0:
		return "No answers yet: the best %s are learnt from your answers" % sex
	if not stale:
		return "Best 25 %s, best first, from all %d answers" % [sex, shown["answers"]]
	var rendering := "rendering them from all %d answers" % shown["answers"]
	if best["picture"].is_empty():
		return "Best %s: %s" % [sex, rendering]
	return "Best 25 %s from %d answers, best first; %s" % [sex, best["answers"], rendering]

extends FaceTool
## Asks the dev which strengths of each candidate feature (tools/faces/candidates.py) a woman's face may
## take, and which he likes best: shows the feature alone on the women's base face at nine strengths, the
## front above the profile, and keeps his answers in tools/faces/features_women.json at once.
##
##   blender --background --python tools/faces/candidates.py -- --only eyes,nose,mouth     renders them, once
##   godot --path . res://dev/features_women.tscn
##
## A click on a strength makes it the favourite, keeping the strengths out to it; a right-click keeps the
## strengths from the favourite out to that one, or only the favourite when it is clicked; X keeps only 0,
## dropping the feature; the arrows or A and D go to the other features. A feature with a favourite is
## answered. For tests, on quiet.py: answers=<json> keeps the answers elsewhere, feature=<n> starts at that
## one, choose=<strengths> clicks each in turn, an r before one right-clicking it, and shot=<png>
## photographs the screen and quits.

const CANDIDATES := "res://tools/faces/candidates/index.json"
const ANSWERS := "res://tools/faces/features_women.json"
const KEYS := "click  favourite      right-click  keep out to there      X  drop: keep only 0      ← →  or  A  D  other features"
const FAVOURITE := Color(1.0, 0.8, 0.35)
const KEPT := Color(0.5, 0.56, 0.62)
const LEFT_OUT := 0.35                          # how bright the strengths left out show

var _features: Array = []
var _steps: Array = []
var _tile := Vector2(540, 600)
var _folder := ""
var _answers := {}
var _path := ""
var _at := 0
var _frames: Array[PanelContainer] = []         # by view, then strength
var _cells: Array[TextureRect] = []
var _heads: Array[Label] = []


func _ready() -> void:
	var grid := GridContainer.new()
	page(grid, KEYS)
	_start(grid)
	if args.has("shot"):
		for i in 10:
			await get_tree().process_frame
		save(await grab(), args["shot"])
		get_tree().quit()


func _start(grid: GridContainer) -> void:
	var index_path := ProjectSettings.globalize_path(CANDIDATES)
	var index = JSON.parse_string(FileAccess.get_file_as_string(index_path)) if FileAccess.file_exists(index_path) else null
	if not index is Dictionary or index["features"].is_empty():
		status.text = "No candidate features rendered: run tools/faces/candidates.py"
		return
	_features = index["features"]
	_steps = index["steps"]
	_tile = Vector2(index["tile"][0], index["tile"][1])
	_folder = index_path.get_base_dir()
	_path = args.get("answers", ProjectSettings.globalize_path(ANSWERS))
	if FileAccess.file_exists(_path):
		var kept = JSON.parse_string(FileAccess.get_file_as_string(_path))
		_answers = kept if kept is Dictionary else {}
	_at = clampi(int(args.get("feature", "0")), 0, _features.size() - 1)
	_lay_out(grid)
	_show()
	if args.has("choose"):
		for said in args["choose"].split(","):
			_choose(float(said.trim_prefix("r")), said.begins_with("r"))


func _lay_out(grid: GridContainer) -> void:
	grid.columns = _steps.size()
	grid.add_theme_constant_override("h_separation", 6)
	grid.add_theme_constant_override("v_separation", 6)
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for s in _steps:
		var head := label(grid, 18, Color(0.75, 0.75, 0.72))
		head.text = _strength(s)
		head.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		_heads.append(head)
	for view in 2:
		for j in _steps.size():
			var frame := PanelContainer.new()
			frame.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
			frame.add_theme_stylebox_override("panel", StyleBoxFlat.new())
			var cell := face()
			cell.size_flags_vertical = Control.SIZE_EXPAND_FILL
			frame.add_child(cell)
			var s: float = _steps[j]
			frame.gui_input.connect(func(e: InputEvent):
				if e is InputEventMouseButton and e.pressed and e.button_index in [MOUSE_BUTTON_LEFT, MOUSE_BUTTON_RIGHT]:
					_choose(s, e.button_index == MOUSE_BUTTON_RIGHT))
			grid.add_child(frame)
			_frames.append(frame)
			_cells.append(cell)


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed) or _features.is_empty():
		return
	match e.physical_keycode:
		KEY_LEFT, KEY_A:
			_at = (_at + _features.size() - 1) % _features.size()
			_show()
		KEY_RIGHT, KEY_D:
			_at = (_at + 1) % _features.size()
			_show()
		KEY_X:
			if not e.echo:
				_keep([0.0, 0.0], 0.0)


## A click (or a right-click) on strength s of the feature shown.
func _choose(s: float, right: bool) -> void:
	if _features[_at]["one_way"] and s < 0.0:
		return
	var answer: Dictionary = _answers.get(_key(), {})
	var kept: Array = answer.get("range", [0.0, 0.0])
	var lo: float = kept[0]
	var hi: float = kept[1]
	if not right:
		_keep([minf(lo, s), maxf(hi, s)], s)
		return
	var favourite = answer.get("favourite")
	var at: float = favourite if favourite != null else 0.0
	if is_equal_approx(s, at):
		_keep([at, at], favourite)
	elif s < at:
		_keep([s, maxf(hi, at)], favourite)
	else:
		_keep([minf(lo, at), s], favourite)


## Keeps the strengths from kept[0] to kept[1] of the feature shown, and the favourite unless it is null.
func _keep(kept: Array, favourite) -> void:
	var answer := {"name": _features[_at]["name"], "range": kept}
	if favourite != null:
		answer["favourite"] = favourite
	_answers[_key()] = answer
	var file := FileAccess.open(_path, FileAccess.WRITE)
	if file == null:
		fail("could not save to " + _path)
		return
	file.store_string(JSON.stringify(_answers, "\t") + "\n")
	file.close()
	_show()


func _key() -> String:
	return _features[_at]["key"]


func _show() -> void:
	var feature: Dictionary = _features[_at]
	var picture := ImageTexture.create_from_image(Image.load_from_file(_folder.path_join(feature["picture"])))
	var answer: Dictionary = _answers.get(_key(), {})
	var kept: Array = answer.get("range", [0.0, 0.0])
	var favourite = answer.get("favourite")
	for view in 2:
		for j in _steps.size():
			var s: float = _steps[j]
			var k := view * _steps.size() + j
			var region := AtlasTexture.new()
			region.atlas = picture
			region.region = Rect2(Vector2(j, view) * _tile, _tile)
			_cells[k].texture = region
			var liked: bool = favourite != null and is_equal_approx(s, favourite)
			var within: bool = s >= kept[0] - 1e-4 and s <= kept[1] + 1e-4
			_cells[k].modulate = Color.WHITE if within or liked else Color(LEFT_OUT, LEFT_OUT, LEFT_OUT)
			var style: StyleBoxFlat = _frames[k].get_theme_stylebox("panel")
			style.draw_center = false
			style.set_border_width_all(5 if liked else 2)
			style.border_color = FAVOURITE if liked else (KEPT if within else Color(0, 0, 0, 0))
	var answered := _features.filter(func(f): return _answers.get(f["key"], {}).has("favourite")).size()
	var choice := "no favourite yet" if favourite == null else "favourite %s" % _strength(favourite)
	var keeps := "dropped: keeps only 0" if kept[0] == kept[1] and is_zero_approx(kept[0]) \
			else "keeps %s to %s" % [_strength(kept[0]), _strength(kept[1])]
	status.text = "%s: %s   (%d of %d)      %s, %s      answered %d of %d      %s" % [
		feature["category"].capitalize(), feature["name"], _at + 1, _features.size(), keeps, choice,
		answered, _features.size(), "the front above, the profile below"]


static func _strength(s: float) -> String:
	return "0" if is_zero_approx(s) else "%+.1f" % s

extends FaceTool
## Picking rounds around the base face of one sex (tools/faces/rounds.py): shows a sheet of 25 faces drawn
## around it, from the front, and the dev picks those he likes; tools/faces/pick.py draws each next sheet
## about the average of his picks, as narrow as they show it should be, and renders it in the background.
##
##   godot --path . res://dev/picks_women.tscn
##
## Faces show as they render, about 5 s each. A click picks a face or unpicks it; Enter or Space submits the sheet's picks, none if none, and shows the
## next; P shows the profiles instead, and again the fronts; Backspace takes the last sheet back. For tests,
## on quiet.py: picks=<jsonl> and answers=<json> keep the picks and read the candidate answers elsewhere;
## once the sheet shows, or faces=<n> of it, pick=<i,j,...> clicks those faces and key=<name> presses that key; shot=<png>
## photographs the screen; then it quits.

const PICK := "res://tools/faces/pick.py"
const KEYS := "click  pick or unpick      Enter  or  Space  next sheet      P  profiles / fronts      Backspace  back a sheet"
const PICKED := Color(1.0, 0.8, 0.35)
const SHEET := 25
const TILE := 540.0 / 600.0                     # a face's picture, wide over tall
const GAP := 6

@export_enum("women", "men") var sex := "women"
var _grid := GridContainer.new()
var _frames: Array[PanelContainer] = []
var _cells: Array[TextureRect] = []
var _pictures: Array[Texture2D] = []
var _paths: Array = []
var _sheet := 0
var _picked := {}
var _profile := false
var _shown := {}


func _ready() -> void:
	_grid.add_theme_constant_override("h_separation", GAP)
	_grid.add_theme_constant_override("v_separation", GAP)
	_grid.resized.connect(_fit)
	for i in SHEET:
		var keeps := AspectRatioContainer.new()
		keeps.ratio = TILE
		keeps.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		keeps.size_flags_vertical = Control.SIZE_EXPAND_FILL
		var frame := PanelContainer.new()
		var style := StyleBoxFlat.new()
		style.draw_center = false
		style.set_border_width_all(4)
		frame.add_theme_stylebox_override("panel", style)
		var cell := face()
		cell.size_flags_vertical = Control.SIZE_EXPAND_FILL
		frame.add_child(cell)
		frame.gui_input.connect(func(e: InputEvent):
			if e is InputEventMouseButton and e.pressed and e.button_index == MOUSE_BUTTON_LEFT:
				_toggle(i))
		keeps.add_child(frame)
		_grid.add_child(keeps)
		_frames.append(frame)
		_cells.append(cell)
	page(_grid, KEYS)
	status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	var arguments := ["--sex", sex]
	for given in ["picks", "answers"]:
		if args.has(given):
			arguments += ["--" + given, args[given]]
	start(PICK, arguments)
	_test()


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	match e.physical_keycode:
		KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
			if _pictures.size() == SHEET:
				send("submit " + JSON.stringify(_picked.keys()))
		KEY_P:
			_profile = not _profile
			_lay_out()
		KEY_BACKSPACE:
			send("undo")


## Lays the faces out in as many columns as show them largest in the page's space.
func _fit() -> void:
	var space := _grid.size
	var best := 0.0
	for columns in range(1, SHEET + 1):
		var rows := ceili(float(SHEET) / columns)
		var tall := minf((space.x - GAP * (columns - 1)) / columns / TILE, (space.y - GAP * (rows - 1)) / rows)
		if tall > best:
			best = tall
			_grid.columns = columns


func _toggle(i: int) -> void:
	if i >= _pictures.size():
		return
	if _picked.has(i):
		_picked.erase(i)
	else:
		_picked[i] = true
	_lay_out()


## Shows the sheet's faces as they are rendered, keeping his picks while more arrive.
func show(shown: Dictionary) -> void:
	var paths: Array = shown["pictures"]
	if shown["sheet"] != _sheet or paths.slice(0, _paths.size()) != _paths:
		_sheet = shown["sheet"]
		_paths = []
		_picked = {}
		for i in shown["picked"]:
			_picked[int(i)] = true
		_pictures.clear()
	for path in paths.slice(_paths.size()):
		_pictures.append(ImageTexture.create_from_image(Image.load_from_file(path)))
	_paths = paths
	_shown = shown
	_lay_out()


## Shows each face's front, or its profile, in a frame lit if he picked it, and the status.
func _lay_out() -> void:
	for i in _cells.size():
		var region: AtlasTexture = null
		if i < _pictures.size():
			var tile := Vector2(_pictures[i].get_width() / 2.0, _pictures[i].get_height())
			region = AtlasTexture.new()
			region.atlas = _pictures[i]
			region.region = Rect2(Vector2(tile.x if _profile else 0.0, 0.0), tile)
		_cells[i].texture = region
		var style: StyleBoxFlat = _frames[i].get_theme_stylebox("panel")
		style.border_color = PICKED if _picked.has(i) else Color(0, 0, 0, 0)
	if not _shown.is_empty():
		status.text = _status(_shown)


func _status(shown: Dictionary) -> String:
	var here: Dictionary = shown["here"]
	var sheet := "%s, sheet %d" % [sex.capitalize(), shown["sheet"]]
	if not here["failed"].is_empty():
		return "%s failed: %s" % [sheet, here["failed"]]
	if here["faces"] == 0:
		return sheet + ": drawing its faces"
	if _pictures.size() < SHEET:
		return "%s rendering: %d of %d faces, about 5 s each      %d picked      Enter once all are in" % [
			sheet, _pictures.size(), SHEET, _picked.size()]
	var narrowest := ", ".join(shown["narrowest"].map(func(n): return "%s %d%%" % [n[0], roundi(100.0 * n[1])]))
	var carries := "candidates: " + (", ".join(shown["candidates"]) if not shown["candidates"].is_empty() else "none")
	if shown["unanswered"] > 0:
		carries += "; %d unanswered, held at 0" % shown["unanswered"]
	return "%s%s:  %d picked      %d picks on %d sheets      narrowest spreads: %s      %s      %s" % [
		sheet, ", profiles" if _profile else "", _picked.size(), shown["picks"], shown["sheets"], narrowest, carries,
		_next(shown["next"])]


static func _next(next: Dictionary) -> String:
	if not next["failed"].is_empty():
		return "next sheet failed: " + next["failed"]
	if next["faces"] == 0:
		return "next sheet: drawing"
	if next["rendered"] < next["faces"]:
		return "next sheet rendering: %d of %d" % [next["rendered"], next["faces"]]
	return "next sheet ready"


## The test the header describes.
func _test() -> void:
	if not args.has("shot"):
		return
	await _until(func(): return _pipe == null or _pictures.size() >= int(args.get("faces", SHEET)))
	for i in args.get("pick", "").split(",", false):
		_toggle(int(i))
	if args.has("key"):
		var press := InputEventKey.new()
		press.physical_keycode = OS.find_keycode_from_string(args["key"])
		press.pressed = true
		Input.parse_input_event(press)
	for i in 10:
		await get_tree().process_frame
	save(await grab(), args["shot"])
	get_tree().quit()

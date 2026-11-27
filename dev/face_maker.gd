extends FaceTool
## The face maker: a head of one sex (scripts/face_head.gd) wearing the face its dials make, live, as the face
## sheets show faces (tools/faces/build_head.py): the same paint, hair and brows under the same camera, lamps
## and Filmic look, from the front and, turned, in profile. tools/faces/maker.py hangs the long hair's fall
## from each face, draws faces and saves them.
##
##   godot --path . res://dev/face_maker_women.tscn
##
## A dial moves one of a face's numbers: the largest scan numbers, the 22 features and the 6 brow numbers,
## and each candidate feature the dev keeps, within his strengths. Randomize (R) draws a face about the base
## face as the picks' first sheet draws its faces, but at their full spread; Profile (P) turns her to the
## profile and back; Base face (B) shows the base face again; Save (S) saves the face in assets/faces/ for
## game characters. For tests, on quiet.py: face=<json> opens a saved face; randomize=<seed> draws one;
## dials=<name:value,...> sets dials by name, dashes for spaces; profile=1 turns to the profile;
## saves=<folder> saves there, save=1 saves; time=<frames> sweeps a dial that many frames and prints how
## long the view took; shot=<png> photographs the window and tile=<png> the face alone as a sheet shows it,
## front and profile at its size; then it quits.

const MAKER := "res://tools/faces/maker.py"
const HEAD := "res://assets/models/head_%s.glb"
const TABLE := "res://assets/models/filmic.png"
const KEYS := "drag  a dial      R  randomize      P  profile / front      B  base face      S  save"
const TURN := 0.6                               # seconds to turn to the profile or back
const SUPERSAMPLE := 2.0                        # the view renders this many times as many pixels a side
const REACH := 2.5                              # a lamp's range, in its distances from the head
const SPLIT := 2                                # a lamp is SPLIT x SPLIT spots
const SHADOW_BIAS := 0.02
const COLUMNS := 3
const NAME_WIDTH := 160
const VALUE_WIDTH := 56
const GROUP := Color(1.0, 0.93, 0.82)

@export_enum("women", "men") var sex := "women"
var _head: FaceHead
var _view := SubViewport.new()
var _frame := SubViewportContainer.new()
var _pivot := Node3D.new()
var _columns := HBoxContainer.new()
var _dials := {}                                # by name: its "slider", the "value" shown and the "dial"
var _face := {}
var _changed := false                           # the dials moved since the last fall was asked for
var _next := ""                                 # a request to send once the session has answered
var _about := "starting"
var _profile := false


func _ready() -> void:
	var middle := HBoxContainer.new()
	middle.add_theme_constant_override("separation", 24)
	var keeps := AspectRatioContainer.new()
	keeps.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_frame.stretch = true
	_frame.add_child(_view)
	keeps.add_child(_frame)
	middle.add_child(keeps)
	var side := VBoxContainer.new()
	side.add_theme_constant_override("separation", 16)
	side.add_child(_buttons())
	_columns.add_theme_constant_override("separation", 28)
	side.add_child(_columns)
	middle.add_child(side)
	page(middle, KEYS)
	if not ResourceLoader.exists(HEAD % sex):
		fail("there is no head: build it with tools/faces/build_head.py, or tools/build_models.ps1")
		return
	_head = (load(HEAD % sex) as PackedScene).instantiate()
	_view.add_child(_head)
	var studio: Dictionary = _head.extras["studio"]
	keeps.ratio = float(studio["tile"][0]) / studio["tile"][1]
	_studio(studio)
	var arguments := ["--sex", sex]
	for given in ["face", "saves"]:
		if args.has(given):
			arguments += ["--" + given, args[given]]
	start(MAKER, arguments)
	_tell()
	_test()


func _buttons() -> HBoxContainer:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	for pressed in [["Randomize", _randomize], ["Profile", _turn], ["Base face", _base], ["Save", _save]]:
		var button := Button.new()
		button.text = pressed[0]
		button.focus_mode = Control.FOCUS_NONE
		button.add_theme_font_size_override("font_size", 18)
		button.pressed.connect(pressed[1])
		row.add_child(button)
	return row


func _unhandled_input(e: InputEvent) -> void:
	if not (e is InputEventKey and e.pressed and not e.echo):
		return
	match e.physical_keycode:
		KEY_R:
			_randomize()
		KEY_P:
			_turn()
		KEY_B:
			_base()
		KEY_S:
			_save()


## The sheets' studio about the head (bl.turnaround): their camera and lamps, which turn together about its
## target to show the profile, the world's light about it, and the Filmic look.
func _studio(studio: Dictionary) -> void:
	_view.own_world_3d = true
	_view.msaa_3d = Viewport.MSAA_4X
	_view.scaling_3d_scale = SUPERSAMPLE
	_view.positional_shadow_atlas_size = 8192
	for quadrant in 4:
		_view.set_positional_shadow_atlas_quadrant_subdiv(quadrant, Viewport.SHADOW_ATLAS_QUADRANT_SUBDIV_4)
	RenderingServer.positional_soft_shadow_filter_set_quality(RenderingServer.SHADOW_QUALITY_SOFT_ULTRA)
	var world := _colour(studio["world"])
	var surroundings := WorldEnvironment.new()
	surroundings.environment = Environment.new()
	surroundings.environment.background_mode = Environment.BG_COLOR
	surroundings.environment.background_color = world
	surroundings.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	surroundings.environment.ambient_light_color = world
	surroundings.environment.reflected_light_source = Environment.REFLECTION_SOURCE_BG
	surroundings.environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	_view.add_child(surroundings)
	_pivot.position = _vector(studio["target"])
	_view.add_child(_pivot)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.keep_aspect = Camera3D.KEEP_HEIGHT
	camera.size = studio["scale"]
	camera.position = Vector3(0.0, 0.0, studio["camera"])
	camera.near = studio["camera"] - 1.0
	camera.far = studio["camera"] + 1.0
	_pivot.add_child(camera)
	camera.add_child(_filmic(studio["lut"]))
	for lamp in studio["lamps"]:
		if args.has("lamp") and lamp["name"] != args["lamp"]:  # LAMP TEST
			continue
		for spot in _lamp(lamp):
			_pivot.add_child(spot)


## A lamp of the sheets' (bl.studio), Cycles' square of `watts` across `size`, as SPLIT x SPLIT spots over its
## square aimed at the head, each with its share of the watts, so that its shadows soften as wide as its
## size makes them. A spot of energy e lights a card facing it as a small Cycles lamp of e pi^2 watts does (Godot
## multiplies energy by pi, and a Lambertian surface divides it by pi), measured in both to a percent; a share
## off the square's middle sends the head less by Lambert's law, and the spot's range takes a little off.
func _lamp(lamp: Dictionary) -> Array[SpotLight3D]:
	var spots: Array[SpotLight3D] = []
	var middle := _vector(lamp["at"])
	var facing := Basis.looking_at(-middle)
	var size: float = lamp["size"]
	var side := size / SPLIT
	for i in SPLIT:
		for j in SPLIT:
			var at := middle + facing * ((Vector3(i, j, 0.0) + Vector3(0.5, 0.5, 0.0)) * side - Vector3(0.5, 0.5, 0.0) * size)
			var spot := SpotLight3D.new()
			spot.transform = Transform3D(Basis.looking_at(-at), at)
			spot.spot_range = REACH * at.length()
			var window := pow(1.0 - pow(1.0 / REACH, 4.0), 2.0)
			var lambert := facing.z.dot(at.normalized())
			spot.light_energy = lamp["watts"] / (SPLIT * SPLIT) / (PI * PI) * lambert / window
			spot.light_color = _colour(lamp["colour"])
			spot.light_size = side / sqrt(PI)
			spot.light_specular = 0.5
			spot.spot_attenuation = 2.0
			spot.spot_angle = 10.0
			spot.spot_angle_attenuation = 0.01
			spot.shadow_enabled = true
			spot.shadow_bias = SHADOW_BIAS
			spots.append(spot)
	return spots


## A quad over the camera's view that shows what it sees in Filmic (shaders/filmic.gdshader).
func _filmic(lut: Dictionary) -> MeshInstance3D:
	var cells := int(lut["size"])
	var image := Image.new()
	image.load_png_from_buffer(FileAccess.get_file_as_bytes(TABLE))
	image.convert(Image.FORMAT_RGBA8)
	var slices: Array[Image] = []
	for s in cells:
		slices.append(image.get_region(Rect2i(s * cells, 0, cells, cells)))
	var table := ImageTexture3D.new()
	table.create(Image.FORMAT_RGBA8, cells, cells, cells, false, slices)
	var look := ShaderMaterial.new()
	look.shader = preload("res://shaders/filmic.gdshader")
	look.set_shader_parameter("table", table)
	look.set_shader_parameter("stops", Vector2(lut["stops"][0], lut["stops"][1]))
	look.set_shader_parameter("cells", float(cells))
	var quad := MeshInstance3D.new()
	var mesh := QuadMesh.new()
	mesh.size = Vector2(2.0, 2.0)
	quad.mesh = mesh
	quad.material_override = look
	quad.position = Vector3(0.0, 0.0, -1.0)
	quad.extra_cull_margin = 16384.0
	quad.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return quad


## A linear colour as Godot's colour properties take it.
static func _colour(c: Array) -> Color:
	return Color(c[0], c[1], c[2]).linear_to_srgb()


static func _vector(v: Array) -> Vector3:
	return Vector3(v[0], v[1], v[2])


## Shows the session's answer: the dials, a new face, its fall, where it was saved.
func show(reply: Dictionary) -> void:
	if reply.has("dials"):
		_lay_out(reply["dials"])
		_about = "opened " + args["face"] if args.has("face") else "the base face"
	if reply.has("face"):
		_face = reply["face"]
		_changed = false
		_head.wear(_face)
		for name in _dials:
			_show_dial(name)
	if reply.get("fall") != null:
		_head.hang(reply["fall"])
	if reply.has("saved"):
		_about = "saved in " + reply["saved"]
	_ask()
	_tell()


## Lays the dials out in their groups, in columns about as long as each other.
func _lay_out(groups: Array) -> void:
	var rows := 0
	for group in groups:
		rows += group["dials"].size() + 1
	var column: VBoxContainer = null
	var filled := 0
	for group in groups:
		var size: int = group["dials"].size() + 1
		if column == null or (filled + size > ceili(float(rows) / COLUMNS) and _columns.get_child_count() < COLUMNS):
			column = VBoxContainer.new()
			column.add_theme_constant_override("separation", 4)
			_columns.add_child(column)
			filled = 0
		var title := Label.new()
		title.text = group["title"]
		title.add_theme_font_size_override("font_size", 18)
		title.add_theme_color_override("font_color", GROUP)
		column.add_child(title)
		for dial in group["dials"]:
			column.add_child(_row(dial))
		filled += size


func _row(dial: Dictionary) -> HBoxContainer:
	var row := HBoxContainer.new()
	var named := Label.new()
	named.text = dial["name"]
	named.custom_minimum_size.x = NAME_WIDTH
	named.add_theme_font_size_override("font_size", 15)
	row.add_child(named)
	var slider := HSlider.new()
	slider.min_value = dial["low"]
	slider.max_value = dial["high"]
	slider.step = 0.01
	slider.allow_greater = true
	slider.allow_lesser = true
	slider.custom_minimum_size.x = 120
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	slider.focus_mode = Control.FOCUS_NONE
	slider.value_changed.connect(func(v: float): _turned(dial, v))
	row.add_child(slider)
	var value := Label.new()
	value.custom_minimum_size.x = VALUE_WIDTH
	value.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	value.add_theme_font_size_override("font_size", 15)
	row.add_child(value)
	_dials[dial["name"]] = {"slider": slider, "value": value, "dial": dial}
	return row


## The dial's value on the face.
func _value(dial: Dictionary) -> float:
	return _face["numbers"][int(dial["number"])] if dial.has("number") else _face["strengths"][dial["candidate"]]


func _show_dial(name: String) -> void:
	var shown: Dictionary = _dials[name]
	var v := _value(shown["dial"])
	shown["slider"].set_value_no_signal(v)
	shown["value"].text = "%+.2f" % v


## A dial moved: the head wears the face at once, and its fall follows.
func _turned(dial: Dictionary, v: float) -> void:
	if _face.is_empty():
		return
	if dial.has("number"):
		_face["numbers"][int(dial["number"])] = v
	else:
		_face["strengths"][dial["candidate"]] = v
	_dials[dial["name"]]["value"].text = "%+.2f" % v
	_head.wear(_face)
	_about = "changed at the dials"
	_changed = true
	_ask()
	_tell()


## Sends what waits for the session: a request, else the face if the dials moved.
func _ask() -> void:
	if not idle():
		return
	if not _next.is_empty():
		send(_next)
		_next = ""
	elif _changed:
		send(JSON.stringify({"face": _face}))
		_changed = false


func _request(request: Dictionary, about: String) -> void:
	_next = JSON.stringify(request)
	_about = about
	_ask()
	_tell()


func _randomize(drawn_with = null) -> void:
	_request({"randomize": drawn_with}, "a random face" + ("" if drawn_with == null else ", seed %s" % drawn_with))


func _base() -> void:
	_request({"base": true}, "the base face")


func _save() -> void:
	if not _face.is_empty():
		_request({"save": _face}, "saving")


## Turns the camera and lamps to her profile, or back to her front.
func _turn() -> void:
	_profile = not _profile
	var tween := create_tween().set_trans(Tween.TRANS_SINE)
	tween.tween_property(_pivot, "rotation:y", _yaw(), TURN)
	_tell()


func _yaw() -> float:
	return -deg_to_rad(_head.extras["studio"]["views"][1]) if _profile else 0.0


## The status line, unless the session has stopped and it says why.
func _tell() -> void:
	if _pipe != null:
		status.text = "Face maker: %s      %s      %s" % [sex, _about, "profile" if _profile else "front"]


## The test the header describes.
func _test() -> void:
	if not (args.has("shot") or args.has("tile") or args.has("time")):
		return
	await _settled()
	if args.has("randomize"):
		_randomize(int(args["randomize"]))
		await _settled()
	for setting in args.get("dials", "").split(",", false):
		var named: String = setting.get_slice(":", 0).replace("-", " ")
		if not _dials.has(named):
			fail("there is no dial " + named)
			break
		_dials[named]["slider"].value = float(setting.get_slice(":", 1))
		await _settled()
	if args.has("profile"):
		_profile = true
		_pivot.rotation.y = _yaw()
		_tell()
	if args.has("save"):
		_save()
		await _settled()
	if args.has("time"):
		await _time(int(args["time"]))
	for i in 10:
		await get_tree().process_frame
	if args.has("shot"):
		save(await grab(), args["shot"])
	if args.has("tile"):
		save(await _tile(), args["tile"], "tile")
	get_tree().quit()


## Waits until the session has answered all there is to ask, or has stopped.
func _settled() -> void:
	await _until(func(): return _pipe == null or (idle() and not _face.is_empty() and not _changed and _next.is_empty()))


## Sweeps the first dial for `frames` frames, the head and its fall changing as it goes, and prints how long the
## view took to render.
func _time(frames: int) -> void:
	var view := _view.get_viewport_rid()
	var window := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(view, true)
	RenderingServer.viewport_set_measure_render_time(window, true)
	var slider: HSlider = _dials.values()[0]["slider"]
	var start := slider.value
	var gpu := PackedFloat32Array()
	var cpu := PackedFloat32Array()
	for i in frames:
		slider.value = start + sin(TAU * i / 120.0)
		await RenderingServer.frame_post_draw
		gpu.append(RenderingServer.viewport_get_measured_render_time_gpu(view)
				+ RenderingServer.viewport_get_measured_render_time_gpu(window))
		cpu.append(RenderingServer.viewport_get_measured_render_time_cpu(view)
				+ RenderingServer.viewport_get_measured_render_time_cpu(window) + RenderingServer.get_frame_setup_time_cpu())
	slider.value = start
	await _settled()
	var sorted_gpu := gpu.duplicate()
	sorted_gpu.sort()
	var mean := func(a: PackedFloat32Array) -> float: return Array(a).reduce(func(s, x): return s + x, 0.0) / a.size()
	print("frames: %d, rendering on the GPU %.2f ms on average, %.2f ms at the 95th percentile, %.2f ms at most; on the CPU %.2f ms on average" % [
		frames, mean.call(gpu), sorted_gpu[int(0.95 * (frames - 1))], sorted_gpu[frames - 1], mean.call(cpu)])


## The face alone as a sheet shows it: the front and the profile side by side, each at the sheets' tile size.
func _tile() -> Image:
	var tile: Array = _head.extras["studio"]["tile"]
	var size := Vector2i(tile[0], tile[1])
	_frame.stretch = false
	_view.size = size
	var sheet := Image.create(2 * size.x, size.y, false, Image.FORMAT_RGBA8)
	var turned := _profile
	for side in 2:
		_profile = side == 1
		_pivot.rotation.y = _yaw()
		for i in 4:
			await RenderingServer.frame_post_draw
		var shot := _view.get_texture().get_image()
		shot.convert(Image.FORMAT_RGBA8)
		sheet.blit_rect(shot, Rect2i(Vector2i.ZERO, size), Vector2i(side * size.x, 0))
	_profile = turned
	_pivot.rotation.y = _yaw()
	return sheet

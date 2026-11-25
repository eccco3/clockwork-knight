extends SceneTree
## Dev check (not used at runtime), needs a renderer:  godot --path . --script res://dev/detail_check.gd [-- <model>]
## Proves a figure's model, the grinner's unless another is named, draws exactly one detail level wherever the
## camera is. Each figure gets a world of its own with the camera already in place before its first frame, in the
## middle of every band and inside every boundary's margin, and what that world drew must be one level, the band's
## own outside the margins.
## Then a camera that hovers across each boundary must keep its level until it leaves the margin.
## The boundaries are read from the imported model. Exits with the number of failures.

const SIZE := Vector2i(160, 120)
const SETTLE := 3
const INSIDE := 0.6  # of the margin: where a fresh figure may show either neighbour, and a hover must not switch
const OUTSIDE := 1.5
const GRINNER := "res://assets/models/grinner.glb"

var _model: PackedScene
var _levels: Array[MeshInstance3D] = []
var _failures := 0


func _init() -> void:
	_run()


func _run() -> void:
	await process_frame
	var named := OS.get_cmdline_user_args()
	_model = load(named[0] if named else GRINNER)
	var probe := _model.instantiate()
	root.add_child(probe)
	for mesh: MeshInstance3D in probe.find_children("*_lod?", "MeshInstance3D", true, false):
		_levels.append(mesh)
	_levels.sort_custom(func(a: MeshInstance3D, b: MeshInstance3D) -> bool: return String(a.name) < String(b.name))
	print("levels: ", _levels.map(func(m: MeshInstance3D) -> String:
		return "%s from %.1f m (margin %.1f), %d triangles" % [m.name, m.visibility_range_begin, m.visibility_range_begin_margin, _triangles(m)]))

	var spawns: Array[Array] = []  # [distance, levels it may show]
	for level in _levels.size():
		var begin := _begin(level)
		var end := _begin(level + 1) if level + 1 < _levels.size() else begin + 10.0
		spawns.append([(begin + end) / 2.0, [level]])
		if level > 0:
			var margin := _levels[level].visibility_range_begin_margin
			spawns.append([begin - margin * INSIDE, [level - 1, level]])
			spawns.append([begin + margin * INSIDE, [level - 1, level]])
	var worlds: Array[SubViewport] = []
	for spawn in spawns:
		worlds.append(_world(spawn[0]))
	await _settle()
	for i in spawns.size():
		_expect("spawned at %.2f m" % spawns[i][0], worlds[i], spawns[i][1])
		worlds[i].queue_free()

	for level in range(1, _levels.size()):
		await _hover(level)

	probe.free()
	print("detail levels: %d failures" % _failures)
	quit(_failures)


## Walks the camera in and out across the boundary where `level` begins, and expects hysteresis: the level
## shown changes only once the camera has left the margin.
func _hover(level: int) -> void:
	var b := _begin(level)
	var m := _levels[level].visibility_range_begin_margin
	var near := level - 1
	var path := [[b - m * OUTSIDE, near], [b - m * INSIDE, near], [b + m * INSIDE, near], [b - m * INSIDE, near],
			[b + m * OUTSIDE, level], [b + m * INSIDE, level], [b - m * INSIDE, level], [b + m * INSIDE, level],
			[b - m * OUTSIDE, near]]
	var world := _world(path[0][0])
	for step: Array in path:
		_place(world, step[0])
		await _settle()
		_expect("hovering at %.2f m" % step[0], world, [step[1]])
	world.queue_free()


func _world(distance: float) -> SubViewport:
	var world := SubViewport.new()
	world.size = SIZE
	world.own_world_3d = true
	world.mesh_lod_threshold = 0.0
	world.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	world.add_child(_model.instantiate())
	var camera := Camera3D.new()
	world.add_child(camera)
	camera.current = true
	root.add_child(world)
	_place(world, distance)
	return world


## Puts the camera `distance` metres from the centre of the figure's full-detail mesh, facing it.
func _place(world: SubViewport, distance: float) -> void:
	var mesh: MeshInstance3D = world.get_child(0).find_child("*_lod0", true, false)
	var centre := mesh.global_transform * mesh.get_aabb().get_center()
	var camera: Camera3D = world.get_child(1)
	camera.global_position = centre + Vector3(0, 0, distance)
	camera.look_at(centre)


func _settle() -> void:
	for i in SETTLE:
		await RenderingServer.frame_post_draw


## Fails unless the world drew one level's triangles, and that level is among `allowed`.
func _expect(what: String, world: SubViewport, allowed: Array) -> void:
	var drawn := RenderingServer.viewport_get_render_info(world.get_viewport_rid(),
			RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME)
	var shown := range(_levels.size()).filter(func(l: int) -> bool: return _triangles(_levels[l]) == drawn)
	var ok: bool = shown.size() == 1 and shown[0] in allowed
	if not ok:
		_failures += 1
	print("%s %s: drew %d triangles, %s; expected %s" % ["ok  " if ok else "FAIL", what, drawn,
			"level %d" % shown[0] if shown.size() == 1 else "no single level", " or ".join(allowed.map(str))])


func _begin(level: int) -> float:
	return _levels[level].visibility_range_begin


func _triangles(mesh: MeshInstance3D) -> int:
	var n := 0
	for s in mesh.mesh.get_surface_count():
		n += mesh.mesh.surface_get_array_index_len(s) / 3
	return n

extends Node
## Scripted play-through harness: loads a scene, feeds input actions on a timeline, and saves
## screenshots or a contact sheet. Run with --fixed-fps 60 so the timeline is deterministic.
##
##   godot --path . res://dev/drive.tscn --fixed-fps 60 --resolution 1280x720 -- \
##       scene=res://dev/stage.tscn out=C:/abs/prefix \
##       do="0.5:press:move_forward;1.5:snap;2.0:release:move_forward;2.2:tap:roll;4:shot:end;5:quit"
##
## Events: press/release/tap:<action>, shot:<name> (full frame -> prefix_name.png), snap (adds a
## tile to the contact sheet prefix_sheet.png), snaps:<n>:<interval>, yaw:<radians> / pitch:<r>
## / dist:<m> (orbit camera), perf:start / perf:stop (frame times; run with --disable-vsync),
## set:<node path or name pattern>:<property>:<value>, env:<property>:<value>,
## vp:<property>:<value>, rs:<RenderingServer method>:<args...> (what-if switches), quit.
## side=dx,dy,dz puts a camera at that offset from the player (looking at her) instead of the
## orbit camera. tile=WxH and cols=N shape the sheet. lamps=baked drops the hall's live character lights.

var _args := {}
var _scene: Node
var _events: Array = []
var _t := 0.0
var _tiles: Array[Image] = []
var _release: Array = []
var _pending_snaps := 0
var _snap_dt := 0.1
var _snap_next := 0.0
var _cam: Camera3D
var _side := Vector3.ZERO
var _busy := false
var _track := 0
var _perf: Perf


func _ready() -> void:
	process_physics_priority = -100
	for a in OS.get_cmdline_user_args():
		var i := a.find("=")
		if i > 0:
			_args[a.substr(0, i)] = a.substr(i + 1)
	Player.setup_input()
	Hall.character_lights = _args.get("lamps", "characters") != "baked"
	var tr := Tracker.new()
	tr.host = self
	tr.process_priority = 1000
	add_child(tr)
	var packed: PackedScene = load(_args.get("scene", "res://dev/stage.tscn"))
	_scene = packed.instantiate()
	add_child(_scene)
	if _player():
		_player().set("capture_mouse", false)
	print("load: scene ready at %d ms" % Time.get_ticks_msec())
	RenderingServer.frame_post_draw.connect(func(): print("load: first frame at %d ms" % Time.get_ticks_msec()), CONNECT_ONE_SHOT)
	for e in String(_args.get("do", "")).split(";", false):
		var p := e.split(":")
		_events.append([float(p[0]), p.slice(1)])
	_events.sort_custom(func(a, b): return a[0] < b[0])
	if _args.has("side"):
		var p: PackedStringArray = _args["side"].split(",")
		_side = Vector3(float(p[0]), float(p[1]), float(p[2]))
		_cam = Camera3D.new()
		_cam.fov = float(_args.get("fov", "40"))
		_cam.near = 0.05
		add_child(_cam)


func _player() -> Node3D:
	return get_tree().get_first_node_in_group("player")


func _process(_dt: float) -> void:
	if _cam:
		var pl := _player()
		if pl:
			var at := pl.global_position + Vector3(0, float(_args.get("lookh", "1.0")), 0)
			_cam.look_at_from_position(at + _side, at)
			_cam.make_current()


func _physics_process(dt: float) -> void:
	_t += dt
	for r in _release.duplicate():
		if _t >= r[0]:
			Input.action_release(r[1])
			_release.erase(r)
	while not _events.is_empty() and _events[0][0] <= _t:
		var ev: PackedStringArray = _events.pop_front()[1]
		match ev[0]:
			"press":
				Input.action_press(ev[1])
			"release":
				Input.action_release(ev[1])
			"tap":
				Input.action_press(ev[1])
				_release.append([_t + 0.08, ev[1]])
			"shot":
				_shot(ev[1])
			"snap":
				_pending_snaps += 1
				_snap_next = _t
			"snaps":
				_pending_snaps += int(ev[1])
				_snap_dt = float(ev[2])
				_snap_next = _t
			"yaw", "pitch", "dist":
				var pl := _player()
				if pl and pl.get("camera"):
					if ev[0] == "yaw":
						pl.camera.yaw = float(ev[1])
					elif ev[0] == "pitch":
						pl.camera.pitch = float(ev[1])
					else:
						pl.camera.distance = float(ev[1])
			"track":
				_track = int(ev[1])
			"fps":
				print("fps: ", Engine.get_frames_per_second(), "  frame ms: ", snappedf(Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, 0.01))
			"hide":
				var n := _scene.find_child(ev[1], true, false)
				if n:
					n.set("visible", false)
				else:
					print("hide: no node ", ev[1])
			"call":
				_scene.call(ev[1])
			"set":
				var found := [_scene.get_node(ev[1])] if ev[1].contains("/") else _scene.find_children(ev[1], "", true, false)
				if found.is_empty():
					print("set: no node ", ev[1])
				for n in found:
					n.set(ev[2], str_to_var(ev[3]))
			"env":
				get_viewport().world_3d.environment.set(ev[1], str_to_var(ev[2]))
			"vp":
				get_viewport().set(ev[1], str_to_var(ev[2]))
			"rs":
				RenderingServer.callv(ev[1], Array(ev.slice(2)).map(str_to_var))
			"perf":
				if ev[1] == "start":
					_perf = Perf.new()
					add_child(_perf)
				elif _perf:
					_perf.report()
					_perf.queue_free()
					_perf = null
			"quit":
				_finish()
	if _pending_snaps > 0 and _t >= _snap_next:
		_pending_snaps -= 1
		_snap_next += _snap_dt
		_snap()


class Tracker extends Node:
	var host: Node
	func _process(_dt: float) -> void:
		if host._track <= 0:
			return
		host._track -= 1
		var pl: Node3D = host._player()
		var sk: Skeleton3D = pl.knight.skel
		var out := "track %.3f" % host._t
		for n in ["foot_l", "foot_r"]:
			var g: Vector3 = (sk.global_transform * sk.get_bone_global_pose(sk.find_bone(n))).origin
			out += "  %s %.3f %.3f %.3f" % [n, g.x, g.y, g.z]
		print(out)


class Perf extends Node:
	var frames := PackedFloat32Array()
	var gpu := 0.0
	var cpu := 0.0
	var _last := 0

	func _ready() -> void:
		RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(), true)
		_last = Time.get_ticks_usec()

	func _process(_dt: float) -> void:
		var now := Time.get_ticks_usec()
		frames.append((now - _last) / 1000.0)
		_last = now
		var vp := get_viewport().get_viewport_rid()
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vp)
		cpu += RenderingServer.viewport_get_measured_render_time_cpu(vp) + RenderingServer.get_frame_setup_time_cpu()

	func report() -> void:
		var n := frames.size()
		var sorted := frames.duplicate()
		sorted.sort()
		var total := 0.0
		for f in frames:
			total += f
		print("perf: %d frames at %s  avg %.2f ms (%.0f fps)  p1 %.2f  p99 %.2f  worst %.2f  gpu %.2f  cpu-render %.2f" % [
			n, get_viewport().size, total / n, 1000.0 * n / total, sorted[int(n * 0.01)], sorted[int(n * 0.99)], sorted[n - 1],
			gpu / n, cpu / n])
		print("perf: draw calls %d  primitives %d  vram %.0f MB  texture %.0f MB  buffer %.0f MB" % [
			Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
			Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0,
			Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED) / 1048576.0,
			Performance.get_monitor(Performance.RENDER_BUFFER_MEM_USED) / 1048576.0])


func _grab() -> Image:
	await RenderingServer.frame_post_draw
	return get_viewport().get_texture().get_image()


func _shot(name: String) -> void:
	var img: Image = await _grab()
	var path := "%s_%s.png" % [_args.get("out", "user://drive"), name]
	print("shot: ", path, " -> ", error_string(img.save_png(path)))


func _snap() -> void:
	var img: Image = await _grab()
	var ts: PackedStringArray = String(_args.get("tile", "480x270")).split("x")
	var tw := int(ts[0])
	var th := int(ts[1])
	# crop to the tile's aspect about the centre, then scale
	var src_w := mini(img.get_width(), int(img.get_height() * float(tw) / th))
	var crop := img.get_region(Rect2i((img.get_width() - src_w) / 2, 0, src_w, img.get_height()))
	crop.resize(tw, th, Image.INTERPOLATE_LANCZOS)
	_tiles.append(crop)


func _finish() -> void:
	if _busy:
		return
	_busy = true
	await RenderingServer.frame_post_draw
	if not _tiles.is_empty():
		var cols := int(_args.get("cols", "4"))
		var tw := _tiles[0].get_width()
		var th := _tiles[0].get_height()
		var rows := int(ceil(_tiles.size() / float(cols)))
		var sheet := Image.create(tw * cols, th * rows, false, _tiles[0].get_format())
		for i in _tiles.size():
			sheet.blit_rect(_tiles[i], Rect2i(0, 0, tw, th), Vector2i((i % cols) * tw, (i / cols) * th))
		var path := "%s_sheet.png" % _args.get("out", "user://drive")
		print("sheet: ", path, " -> ", error_string(sheet.save_png(path)))
	get_tree().quit()

extends Harness
## Scripted play-through harness: loads a scene, feeds input actions on a timeline, and saves
## screenshots or a contact sheet. Run with --fixed-fps 60 so the timeline is deterministic.
##
##   godot --path . res://dev/drive.tscn --fixed-fps 60 --resolution 1280x720 -- \
##       scene=res://dev/stage.tscn out=C:/abs/prefix \
##       do="0.5:press:move_forward;1.5:snap;2.0:release:move_forward;2.2:tap:roll;4:shot:end;5:quit"
##
## Events, each <seconds>:<event>:
##   press/release/tap:<action>      input actions; tap releases after 0.08 s
##   shot:<name>                     full frame -> prefix_name.png
##   snap, snaps:<n>:<interval>      tiles for the contact sheet prefix_sheet.png
##   yaw/pitch:<radians>, dist:<m>   the orbit camera; its yaw still steers her movement
##   cam:<at>:<eye>:<seconds>        a scripted camera blends from the last shot, over that many seconds
##                                   (0 cuts), to look at <at> from <eye>. Each is x,y,z, or a node:
##                                   player, or a name or class with an optional #index, raised lookh
##                                   metres, +h or +dx,dy,dz. <eye> may be +dx,dy,dz from <at>.
##   cam:orbit                       back to the orbit camera
##   track:<frames>                  prints the knight's body, ankles, balls and pelvis each frame
##   fps                             prints frames per second and process time
##   perf:start, perf:stop           frame times; run with --disable-vsync --max-fps 0
##   hide:<node name>
##   call:<method>[:<argument>]      on the scene root, as dev/shot.tscn's call=
##   tell:<node>:<method>            on a node named as cam: names them, e.g. tell:Grinner:pounce
##   set:<node path or name pattern>:<property>:<value>, env:<property>:<value>,
##   vp:<property>:<value>, rs:<RenderingServer method>:<args...>   what-if switches
##   quit                            writes the contact sheet and quits
## side=dx,dy,dz puts a camera at that offset from the player, looking at her from lookh metres up
## (default 1.0) with fov degrees (default 40), instead of the orbit camera. tile=WxH and cols=N
## shape the sheet. lamps=baked drops the hall's live character lights.
## Replace godot with python -I dev/quiet.py to run on a hidden desktop.

var _events: Array = []
var _t := 0.0
var _tiles: Array[Image] = []
var _release: Array = []
var _pending_snaps := 0
var _snap_dt := 0.1
var _snap_next := 0.0
var _cam: Camera3D
var _view: Shot
var _subjects := {}
var _busy := false
var _track := 0
var _perf: Perf


func _ready() -> void:
	process_physics_priority = -100
	var tr := Tracker.new()
	tr.host = self
	tr.process_priority = 1000
	add_child(tr)
	load_scene("res://dev/stage.tscn")
	print("load: scene ready at %d ms" % Time.get_ticks_msec())
	RenderingServer.frame_post_draw.connect(func(): print("load: first frame at %d ms" % Time.get_ticks_msec()), CONNECT_ONE_SHOT)
	for e in String(args.get("do", "")).split(";", false):
		var p := e.split(":")
		_events.append([float(p[0]), p.slice(1)])
	_events.sort_custom(func(a, b): return a[0] < b[0])
	if args.has("side"):
		_cut_to(PackedStringArray(["player", "+" + args["side"], "0"]))


func _player() -> Node3D:
	return get_tree().get_first_node_in_group("player")


## A scripted camera's shot. While it glides in, it blends from the shot before, which keeps moving.
class Shot:
	var at: String
	var eye: String
	var start: float
	var glide: float
	var prev: Shot


func _cut_to(spec: PackedStringArray) -> void:
	if spec[0] == "orbit":
		_view = null
		var pl := _player()
		if pl and pl.get("camera"):
			pl.camera.camera.make_current()
		return
	var s := Shot.new()
	s.at = spec[0]
	s.eye = spec[1]
	s.start = _t
	s.glide = float(spec[2])
	s.prev = _view
	var cur := get_viewport().get_camera_3d()
	if not _view and cur:
		s.prev = Shot.new()
		s.prev.eye = _format(cur.global_position)
		s.prev.at = _format(cur.global_position - cur.global_basis.z * 3.0)
	if not _cam:
		_cam = add_camera(40)
	_view = s


func _format(v: Vector3) -> String:
	return "%f,%f,%f" % [v.x, v.y, v.z]


## The shot's eye and look point now.
func _pose(s: Shot) -> Array[Vector3]:
	var at := _point(s.at, Vector3.ZERO)
	var eye := _point(s.eye, at)
	var k := smoothstep(0.0, 1.0, (_t - s.start) / s.glide) if s.glide > 0.0 else 1.0
	if k >= 1.0:
		s.prev = null
	if s.prev:
		var from := _pose(s.prev)
		return [from[0].lerp(eye, k), from[1].lerp(at, k)]
	return [eye, at]


## x,y,z; +dx,dy,dz from base; or a node's origin raised lookh metres, or +h, or +dx,dy,dz.
func _point(spec: String, base: Vector3) -> Vector3:
	if spec.begins_with("+"):
		return base + vector(spec.substr(1))
	if spec.split(",")[0].is_valid_float():
		return vector(spec)
	var p := spec.split("+")
	var n := _subject(p[0])
	var off := Vector3.UP * float(args.get("lookh", "1.0"))
	if p.size() > 1:
		off = vector(p[1]) if p[1].contains(",") else Vector3.UP * float(p[1])
	return (n.global_position if n else Vector3.ZERO) + off


func _subject(spec: String) -> Node3D:
	if spec == "player":
		return _player()
	if not _subjects.has(spec) or not is_instance_valid(_subjects[spec]):
		var p := spec.split("#")
		var found := scene.find_children("*", "Node3D", true, false).filter(func(n: Node) -> bool:
			var sc: Script = n.get_script()
			return n.name.match(p[0]) or n.is_class(p[0]) or (sc != null and sc.get_global_name() == p[0]))
		var i := int(p[1]) if p.size() > 1 else 0
		_subjects[spec] = found[i] if i < found.size() else null
		if not _subjects[spec]:
			print("cam: no node ", spec)
	return _subjects[spec]


func _process(_dt: float) -> void:
	if _view:
		var pose := _pose(_view)
		_cam.look_at_from_position(pose[0], pose[1])
		_cam.make_current()


## Actions go in as events, as real input does, so handlers see them.
func _send(action: String, pressed: bool) -> void:
	var e := InputEventAction.new()
	e.action = action
	e.pressed = pressed
	Input.parse_input_event(e)


func _physics_process(dt: float) -> void:
	_t += dt
	for r in _release.duplicate():
		if _t >= r[0]:
			_send(r[1], false)
			_release.erase(r)
	while not _events.is_empty() and _events[0][0] <= _t:
		var ev: PackedStringArray = _events.pop_front()[1]
		match ev[0]:
			"press":
				_send(ev[1], true)
			"release":
				_send(ev[1], false)
			"tap":
				_send(ev[1], true)
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
			"cam":
				_cut_to(ev.slice(1))
			"track":
				_track = int(ev[1])
			"fps":
				print("fps: ", Engine.get_frames_per_second(), "  frame ms: ", snappedf(Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0, 0.01))
			"hide":
				var n := scene.find_child(ev[1], true, false)
				if n:
					n.set("visible", false)
				else:
					print("hide: no node ", ev[1])
			"call":
				scene.callv(ev[1], [":".join(ev.slice(2))] if ev.size() > 2 else [])
			"tell":
				var n := _subject(ev[1])
				if n:
					n.call(ev[2])
			"set":
				var found := [scene.get_node(ev[1])] if ev[1].contains("/") else scene.find_children(ev[1], "", true, false)
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
		var p := pl.global_position
		var out := "track %.3f  body %.3f %.3f %.3f" % [host._t, p.x, p.y, p.z]
		for n in ["foot_l", "foot_r", "ball_l", "ball_r", "pelvis"]:
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


func _shot(name: String) -> void:
	save(await grab(), "%s_%s.png" % [args.get("out", "user://drive"), name])


func _snap() -> void:
	var img: Image = await grab()
	var ts: PackedStringArray = String(args.get("tile", "480x270")).split("x")
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
		var cols := int(args.get("cols", "4"))
		var tw := _tiles[0].get_width()
		var th := _tiles[0].get_height()
		var rows := int(ceil(_tiles.size() / float(cols)))
		var sheet := Image.create(tw * cols, th * rows, false, _tiles[0].get_format())
		for i in _tiles.size():
			sheet.blit_rect(_tiles[i], Rect2i(0, 0, tw, th), Vector2i((i % cols) * tw, (i / cols) * th))
		save(sheet, "%s_sheet.png" % args.get("out", "user://drive"), "sheet")
	get_tree().quit()

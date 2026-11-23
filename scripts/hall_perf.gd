extends SceneTree
## Frame-time probe for the hall (dev tool, not used at runtime):
##   godot --path . --disable-vsync --max-fps 0 --resolution 1920x1080 --script res://scripts/hall_perf.gd
## Flies a camera through a few representative views and prints average / worst frame times.

const VIEWS := [
	[Vector3(0, 1.7, 5.5), Vector3(0, 1.6, -12)],
	[Vector3(0, 2.4, -4), Vector3(0, 1.0, -12)],
	[Vector3(0, 1.7, -6), Vector3(0, 2.0, 12)],
	[Vector3(3.5, 2.8, 6.5), Vector3(-4, 1.0, -3)],
]


func _init() -> void:
	_run()


func _run() -> void:
	await process_frame
	var hall: Node3D = (load("res://scenes/hall.tscn") as PackedScene).instantiate()
	root.add_child(hall)
	var env: Environment = hall.get_node("WorldEnvironment").environment
	for a in OS.get_cmdline_user_args():
		match a:
			"noshadow":
				for l in hall.find_children("*", "Light3D", true, false):
					l.shadow_enabled = false
			"noomnishadow":
				for l in hall.find_children("*", "OmniLight3D", true, false):
					l.shadow_enabled = false
			"nosize":
				for l in hall.find_children("*", "Light3D", true, false):
					l.light_size = 0.0
					l.light_angular_distance = 0.0
			"halfgi":
				RenderingServer.gi_set_use_half_resolution(true)
			"nolightmap":
				hall.get_node("LightmapGI").visible = false
			"nossil":
				env.ssil_enabled = false
			"nossao":
				env.ssao_enabled = false
			"nofog":
				env.volumetric_fog_enabled = false
			"noglow":
				env.glow_enabled = false
			"nomsaa":
				root.msaa_3d = Viewport.MSAA_DISABLED
			"noprobe":
				hall.get_node("ReflectionProbe").visible = false
			"nofire":
				hall.get_node("Fire").visible = false
		print("option: ", a)
	var cam := Camera3D.new()
	cam.fov = 70.0
	root.add_child(cam)
	cam.make_current()
	for i in 120:
		await process_frame
	var report := []
	for v in VIEWS.slice(0, 1) if OS.get_cmdline_user_args().size() > 0 else VIEWS:
		cam.look_at_from_position(v[0], v[1])
		for i in 40:
			await process_frame
		var t0 := Time.get_ticks_usec()
		var worst := 0
		var last := t0
		var n := 240
		for i in n:
			await process_frame
			var now := Time.get_ticks_usec()
			worst = maxi(worst, now - last)
			last = now
		var avg := float(Time.get_ticks_usec() - t0) / n / 1000.0
		report.append("%.2f ms (%.0f fps), worst %.2f ms" % [avg, 1000.0 / avg, worst / 1000.0])
	print("window: ", root.size, "  draw calls: ", Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
		"  primitives: ", Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
		"  vram MB: ", Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0)
	for i in report.size():
		print("view %d: %s" % [i, report[i]])
	quit()

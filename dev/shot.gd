extends Node
## Screenshot harness. Loads a scene, optionally places its own camera, lets the
## renderer settle, writes PNG(s) and quits.
##
##   godot --path . res://dev/shot.tscn --resolution 1280x720 -- \
##       scene=res://scenes/hall.tscn out=C:/tmp/a.png pos=0,1.6,6 look=0,1.2,0 fov=60 frames=120
##
## Several views in one run: views="x,y,z>x,y,z;x,y,z>x,y,z" writes out_0.png, out_1.png ...
## Omit pos/views to use whatever camera the scene itself makes current.
## call=method[:arg] invokes a method on the scene root after loading (for posing things).
## lamps=baked drops the hall's live character lights.
## Replace godot with python -I dev/quiet.py to run on a hidden desktop.

var _args := {}
var _cam: Camera3D
var _scene: Node

func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var i := a.find("=")
		if i > 0:
			_args[a.substr(0, i)] = a.substr(i + 1)
	Hall.character_lights = _args.get("lamps", "characters") != "baked"
	var packed: PackedScene = load(_args.get("scene", "res://scenes/main.tscn"))
	_scene = packed.instantiate()
	add_child(_scene)
	if _args.has("call"):
		var parts: PackedStringArray = _args["call"].split(":")
		if parts.size() > 1:
			_scene.call(parts[0], parts[1])
		else:
			_scene.call(parts[0])
	var views: Array = []
	if _args.has("views"):
		for v in _args["views"].split(";"):
			var pl: PackedStringArray = v.split(">")
			views.append([_vec(pl[0]), _vec(pl[1])])
	elif _args.has("pos"):
		views.append([_vec(_args["pos"]), _vec(_args.get("look", "0,1,0"))])
	if not views.is_empty():
		_cam = Camera3D.new()
		_cam.fov = float(_args.get("fov", "60"))
		_cam.near = 0.05
		add_child(_cam)
		_cam.make_current()
	_run(views)

func _vec(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))

func _run(views: Array) -> void:
	var frames := int(_args.get("frames", "90"))
	var out: String = _args.get("out", "user://shot.png")
	if views.is_empty():
		await _settle(frames)
		_save(out)
	else:
		for i in views.size():
			_cam.look_at_from_position(views[i][0], views[i][1])
			await _settle(frames if i == 0 else maxi(frames / 2, 30))
			_save(out if views.size() == 1 else out.replace(".png", "_%d.png" % i))
	get_tree().quit()

func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame
	await RenderingServer.frame_post_draw

func _save(path: String) -> void:
	var img := get_viewport().get_texture().get_image()
	var err := img.save_png(path)
	print("shot: ", path, " -> ", error_string(err))

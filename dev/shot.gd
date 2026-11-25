extends Harness
## Screenshot harness. Loads a scene, optionally places its own camera, lets the
## renderer settle, writes PNG(s) and quits.
##
##   godot --path . res://dev/shot.tscn --resolution 1280x720 -- \
##       scene=res://scenes/hall.tscn out=C:/tmp/a.png pos=0,1.6,6 look=0,1.2,0 fov=60 frames=120
##
## Several views in one run: views="x,y,z>x,y,z;x,y,z>x,y,z" writes out_0.png, out_1.png ...
## Omit pos/views to use whatever camera the scene itself makes current.
## bone=<name> measures pos, look and views from where that bone of the scene's skeleton is.
## call=method[:arg] invokes a method on the scene root after loading (for posing things).
## lamps=baked drops the hall's live character lights.
## Replace godot with python -I dev/quiet.py to run on a hidden desktop.

var _cam: Camera3D

func _ready() -> void:
	load_scene("res://scenes/main.tscn")
	if args.has("call"):
		var parts: PackedStringArray = args["call"].split(":", true, 1)
		scene.callv(parts[0], Array(parts.slice(1)))
	var views: Array = []
	if args.has("views"):
		for v in args["views"].split(";"):
			var pl: PackedStringArray = v.split(">")
			views.append([vector(pl[0]), vector(pl[1])])
	elif args.has("pos"):
		views.append([vector(args["pos"]), vector(args.get("look", "0,1,0"))])
	if not views.is_empty():
		_cam = add_camera(60)
		_cam.make_current()
	_run(views)

func _run(views: Array) -> void:
	var frames := int(args.get("frames", "90"))
	var out: String = args.get("out", "user://shot.png")
	if views.is_empty():
		await _settle(frames)
		save(await grab(), out)
	else:
		var origin := await _origin()
		for i in views.size():
			_cam.look_at_from_position(origin + views[i][0], origin + views[i][1])
			await _settle(frames if i == 0 else maxi(frames / 2, 30))
			save(await grab(), out if views.size() == 1 else out.replace(".png", "_%d.png" % i))
	get_tree().quit()

func _origin() -> Vector3:
	if not args.has("bone"):
		return Vector3.ZERO
	await _settle(2)
	var skel: Skeleton3D = scene.find_children("*", "Skeleton3D", true, false)[0]
	return skel.global_transform * skel.get_bone_global_pose(skel.find_bone(args["bone"])).origin


func _settle(n: int) -> void:
	for i in n:
		await get_tree().process_frame

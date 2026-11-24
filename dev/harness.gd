class_name Harness
extends Node
## What the dev harnesses share: key=value user arguments, the scene under test (lamps=baked drops
## the hall's live character lights), a camera of their own and PNG output.

var args := {}
var scene: Node


func _init() -> void:
	for a in OS.get_cmdline_user_args():
		var i := a.find("=")
		if i > 0:
			args[a.substr(0, i)] = a.substr(i + 1)


func load_scene(default: String) -> void:
	Hall.character_lights = args.get("lamps", "characters") != "baked"
	scene = (load(args.get("scene", default)) as PackedScene).instantiate()
	add_child(scene)


func add_camera(default_fov: float) -> Camera3D:
	var cam := Camera3D.new()
	cam.fov = float(args.get("fov", default_fov))
	cam.near = 0.05
	add_child(cam)
	return cam


static func vector(s: String) -> Vector3:
	var p := s.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))


func grab() -> Image:
	await RenderingServer.frame_post_draw
	return get_viewport().get_texture().get_image()


func save(img: Image, path: String, what := "shot") -> void:
	print(what, ": ", path, " -> ", error_string(img.save_png(path)))

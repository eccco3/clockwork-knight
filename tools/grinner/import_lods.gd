@tool
extends EditorScenePostImport
## Import script of grinner.glb: shows one detail level at a time, chosen by distance from the camera.

const BEGIN: Array[float] = [0.0, 6.0, 12.0, 22.0]
const MARGIN := 0.5

func _post_import(scene: Node) -> Object:
	for node in scene.find_children("grinner_lod*", "MeshInstance3D"):
		var mesh := node as MeshInstance3D
		var level := String(mesh.name).right(1).to_int()
		mesh.visibility_range_begin = BEGIN[level]
		mesh.visibility_range_begin_margin = MARGIN if level > 0 else 0.0
		if level + 1 < BEGIN.size():
			mesh.visibility_range_end = BEGIN[level + 1]
			mesh.visibility_range_end_margin = MARGIN
	return scene

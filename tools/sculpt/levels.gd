@tool
extends RefCounted
## Detail levels for the import script of a figure whose build exported them as meshes named <figure>_lod0,
## <figure>_lod1 and so on, coarser as the number rises.


## Shows exactly one of the scene's meshes matching `pattern` at a time, chosen by distance from the camera:
## level n from begin[n] metres. Returns them, finest first.
##
## Each level is the visibility parent of the next finer one, which draws only while its parent is hidden for
## being nearer than its begin. One level decides each boundary, with `margin` as hysteresis, so exactly one
## draws even where a figure or camera first appears inside a margin. (Paired begin and end ranges keep a
## state each, and a fresh pair both stands back from the boundary, drawing nothing there.)
static func chain(scene: Node, pattern: String, begin: Array[float], margin: float) -> Array[MeshInstance3D]:
	var levels: Array[MeshInstance3D] = []
	levels.resize(begin.size())
	for mesh: MeshInstance3D in scene.find_children(pattern, "MeshInstance3D"):
		levels[String(mesh.name).right(1).to_int()] = mesh
	for level in levels.size():
		var mesh := levels[level]
		mesh.visibility_range_begin = begin[level]
		mesh.visibility_range_begin_margin = margin if level > 0 else 0.0
		if level + 1 < levels.size():
			mesh.visibility_parent = mesh.get_path_to(levels[level + 1])
	return levels

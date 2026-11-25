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


## Leaves the casting of the figure's shadow, at every distance, to a copy of the coarsest of `levels` on the same
## skin, named <figure>_shadow, which draws nowhere else. The shadow maps are too coarse to show finer levels.
## It keeps the level's own mesh, whose automatic simplifications thin it further with distance.
static func shadow_from_coarsest(levels: Array[MeshInstance3D]) -> MeshInstance3D:
	for level in levels:
		level.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var coarsest := levels[-1]
	var caster := coarsest.duplicate() as MeshInstance3D
	caster.name = String(coarsest.name).get_slice("_lod", 0) + "_shadow"
	caster.visibility_range_begin = 0.0
	caster.visibility_range_begin_margin = 0.0
	caster.visibility_parent = NodePath()
	caster.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	coarsest.add_sibling(caster)
	caster.owner = coarsest.owner
	return caster

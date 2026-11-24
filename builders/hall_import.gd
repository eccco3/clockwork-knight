@tool
extends EditorScenePostImport
## Post-import hook for assets/models/hall.glb: meshes whose name starts with "ns_" are fine
## dressing (floor boards, masonry facing, books, tableware, ironwork...) and do not cast shadows.
## Four lights cast shadows, and the chandeliers draw only characters into theirs, so this keeps
## the fire's shadow map, the one that draws the hall, cheap.


func _post_import(scene: Node) -> Object:
	for n in scene.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		if String(mi.name).begins_with("ns_"):
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return scene

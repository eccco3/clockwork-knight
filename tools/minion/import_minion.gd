@tool
extends EditorScenePostImport
## Import script of minion.glb. Shows exactly one detail level at a time, chosen by distance from the camera,
## and leaves the casting of his shadow at every distance to the stand-in, which draws nowhere else.

const Levels := preload("res://tools/sculpt/levels.gd")
const BEGIN: Array[float] = [0.0, 5.0, 11.0]
const MARGIN := 0.5


func _post_import(scene: Node) -> Object:
	for level in Levels.chain(scene, "minion_lod*", BEGIN, MARGIN):
		level.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var caster: MeshInstance3D = scene.find_child("minion_shadow")
	caster.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
	return scene

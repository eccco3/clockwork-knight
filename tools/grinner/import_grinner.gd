@tool
extends EditorScenePostImport
## Import script of grinner.glb. Shows one detail level at a time, chosen by distance from the camera,
## loops the clips, and adds an AnimationTree that blends Idle into Waddle along `parameters/blend_position`
## (0 to 1). The waddle's travel is root motion: whoever owns the grinner moves it by the tree's
## `get_root_motion_position()`.

const BEGIN: Array[float] = [0.0, 6.0, 12.0, 22.0]
const MARGIN := 0.5
const GAIT := {"Idle": 0.0, "Waddle": 1.0}

func _post_import(scene: Node) -> Object:
	for node in scene.find_children("grinner_lod*", "MeshInstance3D"):
		var mesh := node as MeshInstance3D
		var level := String(mesh.name).right(1).to_int()
		mesh.visibility_range_begin = BEGIN[level]
		mesh.visibility_range_begin_margin = MARGIN if level > 0 else 0.0
		if level + 1 < BEGIN.size():
			mesh.visibility_range_end = BEGIN[level + 1]
			mesh.visibility_range_end_margin = MARGIN

	var player: AnimationPlayer = scene.find_child("AnimationPlayer")
	var gait := AnimationNodeBlendSpace1D.new()
	gait.min_space = 0.0
	for clip: String in GAIT:
		player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
		var node := AnimationNodeAnimation.new()
		node.animation = clip
		gait.add_blend_point(node, GAIT[clip], -1, clip)
	var tree := AnimationTree.new()
	tree.name = "AnimationTree"
	tree.tree_root = gait
	scene.add_child(tree)
	tree.owner = scene
	tree.anim_player = tree.get_path_to(player)
	tree.root_motion_track = NodePath("%s:root" % scene.get_path_to(scene.find_child("Skeleton3D")))
	return scene

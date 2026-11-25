@tool
extends EditorScenePostImport
## Import script of rosalyn.glb. Loops her Idle and adds an AnimationTree that plays it, with her Blink added
## over it each time `parameters/Blink/request` fires. Blink keeps only its lids' tracks, so a blink shuts them
## from wherever the idle holds them, as she looks down, and leaves the rest of her be.


func _post_import(scene: Node) -> Object:
	var player: AnimationPlayer = scene.find_child("AnimationPlayer")
	player.get_animation("Idle").loop_mode = Animation.LOOP_LINEAR
	var shut := player.get_animation("Blink")
	for track in range(shut.get_track_count() - 1, -1, -1):
		if not shut.track_get_path(track).get_concatenated_subnames().begins_with("lid_"):
			shut.remove_track(track)
	var blink := AnimationNodeOneShot.new()
	blink.mix_mode = AnimationNodeOneShot.MIX_MODE_ADD
	blink.fadein_time = 0.0
	blink.fadeout_time = 0.0
	var blend := AnimationNodeBlendTree.new()
	blend.add_node("Idle", _clip("Idle"))
	blend.add_node("Shut", _clip("Blink"))
	blend.add_node("Blink", blink)
	blend.connect_node("Blink", 0, "Idle")
	blend.connect_node("Blink", 1, "Shut")
	blend.connect_node("output", 0, "Blink")

	var tree := AnimationTree.new()
	tree.name = "AnimationTree"
	tree.tree_root = blend
	scene.add_child(tree)
	tree.owner = scene
	tree.anim_player = tree.get_path_to(player)
	return scene


func _clip(name: String) -> AnimationNodeAnimation:
	var node := AnimationNodeAnimation.new()
	node.animation = name
	return node

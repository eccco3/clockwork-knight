@tool
extends EditorScenePostImport
## Import script of rosalyn.glb. Loops her Idle and her speech clips, which the build names in the skeleton's
## extras as `speech`, and adds an AnimationTree. Its Transition `Speech` crosses from one speech clip to
## another at `parameters/Speech/transition_request`, its Blend2 `Talk` blends from the Idle to them along
## `parameters/Talk/blend_amount`, and her Blink is added over both each time `parameters/Blink/request` fires.
## Every loop is as long as the Idle and keeps on playing in step with it, so whatever is blended, her
## breathing and her weight go on as one. The clips blend from her RESET, how she stands.
## Blink keeps only its lids' tracks, so a blink shuts them from wherever the clips hold them, as she looks
## down, and leaves the rest of her be.

const GESTURE_FADE := 0.9  ## seconds one speech clip takes to cross into the next


func _post_import(scene: Node) -> Object:
	var player: AnimationPlayer = scene.find_child("AnimationPlayer")
	var extras: Dictionary = scene.find_children("*").filter(func(n: Node) -> bool: return n.has_meta("extras"))[0].get_meta("extras")
	var speech: Array = extras["speech"]
	for clip: String in ["Idle"] + speech:
		player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
	var shut := player.get_animation("Blink")
	for track in range(shut.get_track_count() - 1, -1, -1):
		if not shut.track_get_path(track).get_concatenated_subnames().begins_with("lid_"):
			shut.remove_track(track)

	var blend := AnimationNodeBlendTree.new()
	var gestures := AnimationNodeTransition.new()
	gestures.sync = true
	gestures.xfade_time = GESTURE_FADE
	for k in speech.size():
		gestures.add_input(speech[k])
		gestures.set_input_reset(k, false)
		blend.add_node(speech[k], _clip(speech[k]))
	blend.add_node("Speech", gestures)
	for k in speech.size():
		blend.connect_node("Speech", k, speech[k])
	var talk := AnimationNodeBlend2.new()
	talk.sync = true
	blend.add_node("Idle", _clip("Idle"))
	blend.add_node("Talk", talk)
	blend.connect_node("Talk", 0, "Idle")
	blend.connect_node("Talk", 1, "Speech")
	var blink := AnimationNodeOneShot.new()
	blink.mix_mode = AnimationNodeOneShot.MIX_MODE_ADD
	blink.fadein_time = 0.0
	blink.fadeout_time = 0.0
	blend.add_node("Shut", _clip("Blink"))
	blend.add_node("Blink", blink)
	blend.connect_node("Blink", 0, "Talk")
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

@tool
extends EditorScenePostImport
## Import script of grinner.glb. Shows one detail level at a time, chosen by distance from the camera, and
## adds an AnimationTree: a state machine whose state Gait blends Idle into Waddle along
## `parameters/Gait/blend_position` (0 to 1) and whose other states are the moves, each played once.
## `parameters/playback` travels to a move; the attacks and the flinch come back to Gait when they end, a flinch
## cuts into an attack, and Death cuts into anything and stays. All travel is root motion: whoever owns the
## grinner moves it by the tree's `get_root_motion_position()`.
##
## The build's marks become markers on the animations, named after the phase that begins there: `leap`, `hit`
## and `recover` on Pounce, `hit` and `recover` on Swipe. An attack is winding up until its first marker, and
## its hit window is open from `hit` to `recover`.

const BEGIN: Array[float] = [0.0, 6.0, 12.0, 22.0]
const MARGIN := 0.5
const GAIT := {"Idle": 0.0, "Waddle": 1.0}
const RETURNING: Array[String] = ["Pounce", "Swipe", "Flinch"]
const INTERRUPTION := "Flinch"
const END := "Death"
const FADE_IN := 0.1
const FADE_OUT := 0.25
const CUT := 0.08

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
	var marks: Dictionary = scene.find_children("*").filter(func(n: Node) -> bool: return n.has_meta("extras"))[0].get_meta("extras")["marks"]
	for clip: String in marks:
		for phase: String in marks[clip]:
			player.get_animation(clip).add_marker(phase, marks[clip][phase])

	var gait := AnimationNodeBlendSpace1D.new()
	gait.min_space = 0.0
	for clip: String in GAIT:
		player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
		gait.add_blend_point(_clip(clip), GAIT[clip], -1, clip)
	var machine := AnimationNodeStateMachine.new()
	machine.add_node("Gait", gait)
	machine.add_transition("Start", "Gait", _transition(0.0, AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO))
	for move: String in RETURNING + [END]:
		machine.add_node(move, _clip(move))
		machine.add_transition("Gait", move, _transition(FADE_IN))
	for move in RETURNING:
		var back := _transition(FADE_OUT, AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO)
		back.switch_mode = AnimationNodeStateMachineTransition.SWITCH_MODE_AT_END
		machine.add_transition(move, "Gait", back)
		machine.add_transition(move, END, _transition(FADE_IN))
		if move != INTERRUPTION:
			machine.add_transition(move, INTERRUPTION, _transition(CUT))

	var tree := AnimationTree.new()
	tree.name = "AnimationTree"
	tree.tree_root = machine
	scene.add_child(tree)
	tree.owner = scene
	tree.anim_player = tree.get_path_to(player)
	tree.root_motion_track = NodePath("%s:root" % scene.get_path_to(scene.find_child("Skeleton3D")))
	return scene


func _clip(name: String) -> AnimationNodeAnimation:
	var node := AnimationNodeAnimation.new()
	node.animation = name
	return node


func _transition(fade: float, advance := AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED) -> AnimationNodeStateMachineTransition:
	var t := AnimationNodeStateMachineTransition.new()
	t.xfade_time = fade
	t.advance_mode = advance
	return t

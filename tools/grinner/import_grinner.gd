@tool
extends EditorScenePostImport
## Import script of every kind of grinner's model. Shows exactly one detail level at a time, chosen by distance
## from the camera, and adds an AnimationTree: a state machine whose state Gait blends the kind's looping clips,
## its idle into its walk or run, along `parameters/Gait/blend_position` (0 to 1) and whose other states are its
## moves, each played once. `parameters/playback` travels to a move; the attacks and the flinch come back to
## Gait when they end, a flinch cuts into an attack, and Death cuts into anything and stays. All travel is root
## motion: whoever owns the grinner moves it by the tree's `get_root_motion_position()`.
##
## The build says which clips are which in the skeleton's extras: `gait` places each looping clip along the
## blend, and `marks` gives each move the seconds its phases begin, which become markers on the animations,
## named after the phase: `hit` and `recover` on every attack, and `leap` before them on a pounce. An attack is
## winding up until its first marker, and its hit window is open from `hit` to `recover`.

const BEGIN: Array[float] = [0.0, 6.0, 12.0, 22.0]
const MARGIN := 0.5
const INTERRUPTION := "Flinch"
const END := "Death"
const FADE_IN := 0.1
const FADE_OUT := 0.25
const CUT := 0.08

func _post_import(scene: Node) -> Object:
	_chain_levels(scene)

	var player: AnimationPlayer = scene.find_child("AnimationPlayer")
	var extras: Dictionary = scene.find_children("*").filter(func(n: Node) -> bool: return n.has_meta("extras"))[0].get_meta("extras")
	var marks: Dictionary = extras["marks"]
	for clip: String in marks:
		for phase: String in marks[clip]:
			player.get_animation(clip).add_marker(phase, marks[clip][phase])

	var gait := AnimationNodeBlendSpace1D.new()
	gait.min_space = 0.0
	for clip: String in extras["gait"]:
		player.get_animation(clip).loop_mode = Animation.LOOP_LINEAR
		gait.add_blend_point(_clip(clip), extras["gait"][clip], -1, clip)
	var machine := AnimationNodeStateMachine.new()
	machine.add_node("Gait", gait)
	machine.add_transition("Start", "Gait", _transition(0.0, AnimationNodeStateMachineTransition.ADVANCE_MODE_AUTO))
	for move: String in marks:
		machine.add_node(move, _clip(move))
		machine.add_transition("Gait", move, _transition(FADE_IN))
	for move: String in marks.keys().filter(func(m: String) -> bool: return m != END):
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


## Each level is the visibility parent of the next finer one, which draws only while its parent is hidden for
## being nearer than its begin. One level decides each boundary, with its margin as hysteresis, so exactly one
## draws even where a grinner or camera first appears inside a margin. (Paired begin and end ranges keep a
## state each, and a fresh pair both stands back from the boundary, drawing nothing there.)
func _chain_levels(scene: Node) -> void:
	var levels: Array[MeshInstance3D] = []
	levels.resize(BEGIN.size())
	for mesh: MeshInstance3D in scene.find_children("*_lod?", "MeshInstance3D"):
		levels[String(mesh.name).right(1).to_int()] = mesh
	for level in levels.size():
		var mesh := levels[level]
		mesh.visibility_range_begin = BEGIN[level]
		mesh.visibility_range_begin_margin = MARGIN if level > 0 else 0.0
		if level + 1 < levels.size():
			mesh.visibility_parent = mesh.get_path_to(levels[level + 1])


func _clip(name: String) -> AnimationNodeAnimation:
	var node := AnimationNodeAnimation.new()
	node.animation = name
	return node


func _transition(fade: float, advance := AnimationNodeStateMachineTransition.ADVANCE_MODE_ENABLED) -> AnimationNodeStateMachineTransition:
	var t := AnimationNodeStateMachineTransition.new()
	t.xfade_time = fade
	t.advance_mode = advance
	return t

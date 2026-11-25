extends SceneTree
## Dev check (not used at runtime):  godot --headless --fixed-fps 60 --path . --script res://dev/grinner_check.gd
##     [-- model=res://assets/models/scuttler.glb attacks=pounce,bite cut=0.15 late=0.45,0.6]
## Plays each of a grinner's moves through its AnimationTree and prints, in seconds since the move was
## asked for, when it wound up, struck, and came back to its gait, and how far its root motion took it.
## Then cuts a flinch into each wind-up `cut` seconds in, and into the first attack, a pounce in mid leap at
## the first of `late`, a flinch, which it ignores, and at the second a death.

const STEP := 1.0 / 60.0

var _model: PackedScene
var _attacks: PackedStringArray = ["pounce", "swipe"]
var _cut := 0.3
var _late: PackedFloat64Array = [0.8, 1.0]


func _init() -> void:
	for a in OS.get_cmdline_user_args():
		var value := a.get_slice("=", 1)
		match a.get_slice("=", 0):
			"model": _model = load(value)
			"attacks": _attacks = value.split(",")
			"cut": _cut = float(value)
			"late": _late = value.split_floats(",")
	_run()


func _run() -> void:
	await process_frame
	for move: String in _attacks + PackedStringArray(["flinch", "die"]):
		await _play(move, [])
	for attack: String in _attacks:
		await _play(attack, [[_cut, "flinch"]])
	await _play(_attacks[0], [[_late[0], "flinch"], [_late[1], "die"]])
	quit()


func _play(move: String, cuts: Array) -> void:
	var grinner := Grinner.new()
	if _model:
		grinner.model = _model
	root.add_child(grinner)
	for i in 30:
		await process_frame
	var began := {}
	var ended := {}
	var states: Array[StringName] = []
	grinner.call(move)
	var t := 0.0
	while t < 4.0 and not (t > 0.5 and grinner.move() == &"Gait"):
		await process_frame
		t += STEP
		for cut: Array in cuts:
			if absf(t - cut[0]) < STEP / 2:
				grinner.call(cut[1])
		if states.is_empty() or states[-1] != grinner.move():
			states.append(grinner.move())
			began[grinner.move()] = t
		for what: String in ["winding_up", "striking"]:
			if grinner.call(what):
				if not began.has(what):
					began[what] = t
				ended[what] = t
	var line := "%s%s:" % [move, "".join(cuts.map(func(c: Array) -> String: return " +%s@%.2f" % [c[1], c[0]]))]
	for what: String in began:
		line += "  %s %.2f" % [what, began[what]] + ("-%.2f" % ended[what] if ended.has(what) else "")
	print(line, "  travelled %.2f m  sank %.3f m" % [grinner.position.z, -grinner.position.y])
	grinner.free()

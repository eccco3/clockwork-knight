extends SceneTree
## Dev check (not used at runtime):  godot --headless --fixed-fps 60 --path . --script res://dev/grinner_check.gd
## Plays each of the grinner's moves through its AnimationTree and prints, in seconds since the move was
## asked for, when it wound up, struck, and came back to its gait, and how far its root motion took it.
## Then cuts a flinch into each wind-up, and a death into a pounce.

const STEP := 1.0 / 60.0


func _init() -> void:
	_run()


func _run() -> void:
	await process_frame
	for move: String in ["pounce", "swipe", "flinch", "die"]:
		await _play(move, [])
	for attack: String in ["pounce", "swipe"]:
		await _play(attack, [[0.3, "flinch"]])
	await _play("pounce", [[0.8, "flinch"], [1.0, "die"]])
	quit()


func _play(move: String, cuts: Array) -> void:
	var grinner := Grinner.new()
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

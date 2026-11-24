extends SceneTree
## Dev check (not used at runtime):  godot --headless --path . --script tools/hall_check.gd
## Verifies floor height, wall positions and that a player-sized capsule fits everywhere in the
## declared clear play area (|x| <= 4, |z| <= 7).


func _init() -> void:
	_run()


func _run() -> void:
	await process_frame
	var hall: Node3D = (load("res://scenes/hall.tscn") as PackedScene).instantiate()
	root.add_child(hall)
	await physics_frame
	await physics_frame
	var space := root.world_3d.direct_space_state
	var bad_floor := 0
	var n := 0
	for xi in range(-12, 13):
		for zi in range(-23, 24):
			var x := xi * 0.5
			var z := zi * 0.5
			var q := PhysicsRayQueryParameters3D.create(Vector3(x, 3.0, z), Vector3(x, -3.0, z), Layers.SCENERY)
			var hit := space.intersect_ray(q)
			n += 1
			if hit.is_empty() or (absf(x) <= 4.0 and absf(z) <= 7.0 and absf(hit.position.y) > 0.001):
				bad_floor += 1
	print("floor rays: ", n, "  missing/not-at-zero inside play area: ", bad_floor)
	var cap := CapsuleShape3D.new()
	cap.radius = 0.35
	cap.height = 1.8
	var blocked := 0
	var tested := 0
	for xi in range(-16, 17):
		for zi in range(-28, 29):
			for y in [0.92, 2.2, 3.3]:
				var p := PhysicsShapeQueryParameters3D.new()
				p.shape = cap
				p.transform = Transform3D(Basis.IDENTITY, Vector3(xi * 0.25, y, zi * 0.25))
				p.collision_mask = Layers.SCENERY
				tested += 1
				if not space.intersect_shape(p, 1).is_empty():
					blocked += 1
					if blocked <= 40:
						print("  blocked at ", p.transform.origin)
	print("capsule probes in play area: ", tested, "  blocked: ", blocked)
	for d in [Vector3.RIGHT, Vector3.LEFT, Vector3.FORWARD, Vector3.BACK, Vector3.UP]:
		var q2 := PhysicsRayQueryParameters3D.create(Vector3(0, 1.0, 0), Vector3(0, 1.0, 0) + d * 40.0, Layers.SCENERY)
		var h2 := space.intersect_ray(q2)
		print("ray ", d, " -> ", h2.get("position", "MISS"))
	print("spawn: ", hall.get_node("PlayerSpawn").global_transform)
	var lights := hall.find_children("*", "Light3D", true, false)
	var sh := 0
	for l in lights:
		if l.shadow_enabled:
			sh += 1
	print("lights: ", lights.size(), "  shadowed: ", sh)
	quit()

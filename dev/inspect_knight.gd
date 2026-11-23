extends SceneTree
## godot --headless --path . -s dev/inspect_knight.gd

func _init() -> void:
	var scene: Node = load("res://assets/models/knight.glb").instantiate()
	_walk(scene, 0)
	quit()

func _walk(n: Node, depth: int) -> void:
	var extra := ""
	if n is Skeleton3D:
		extra = " bones=%d" % n.get_bone_count()
	elif n is MeshInstance3D:
		var m: ArrayMesh = n.mesh
		extra = " surfaces=%d skin=%s" % [m.get_surface_count(), n.skin != null]
		for s in m.get_surface_count():
			var arr := m.surface_get_arrays(s)
			var mat := m.surface_get_material(s)
			var have := []
			for k in [[Mesh.ARRAY_NORMAL, "N"], [Mesh.ARRAY_TANGENT, "T"], [Mesh.ARRAY_COLOR, "C"], [Mesh.ARRAY_TEX_UV, "UV"], [Mesh.ARRAY_TEX_UV2, "UV2"], [Mesh.ARRAY_BONES, "B"]]:
				if arr[k[0]] != null and arr[k[0]].size() > 0:
					have.append(k[1])
			var uv: PackedVector2Array = arr[Mesh.ARRAY_TEX_UV]
			var uv2: PackedVector2Array = arr[Mesh.ARRAY_TEX_UV2]
			var lo := Vector2(INF, INF)
			var hi := Vector2(-INF, -INF)
			for v in uv:
				lo = lo.min(v)
				hi = hi.max(v)
			print("    surf %d  mat=%-12s verts=%d  %s  uv[%s..%s]" % [s, mat.resource_name if mat else "-", arr[Mesh.ARRAY_VERTEX].size(), " ".join(have), lo, hi])
	elif n is AnimationPlayer:
		var names: PackedStringArray = n.get_animation_list()
		extra = " anims=%d" % names.size()
		for a in names:
			var an: Animation = n.get_animation(a)
			var pos_tracks := 0
			for t in an.get_track_count():
				if an.track_get_type(t) == Animation.TYPE_POSITION_3D:
					pos_tracks += 1
			print("    anim %-22s len=%.3f tracks=%d pos_tracks=%d loop=%d" % [a, an.length, an.get_track_count(), pos_tracks, an.loop_mode])
	print("  ".repeat(depth), n.name, " [", n.get_class(), "]", extra)
	for c in n.get_children():
		_walk(c, depth + 1)

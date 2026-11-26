extends SceneTree
## Offline builder: assembles scenes/hall.tscn from assets/models/hall.glb, its layout
## hall_layout.json and the materials of builders/hall_materials.gd. The scene's lamps are baked
## into a lightmap afterwards by addons/lightmap_bake.
##
##   godot --headless --path . --script res://builders/hall_scene.gd

const HallMaterials := preload("res://builders/hall_materials.gd")
const SCENE := "res://scenes/hall.tscn"
const BOUNCE := 3.0

var _root: Node3D
var _layout: Dictionary


func _init() -> void:
	_scene()
	quit()


func _add(node: Node, parent: Node = null, n := "") -> Node:
	if n != "":
		node.name = n
	(parent if parent else _root).add_child(node)
	node.owner = _root
	return node


func _v(a: Array) -> Vector3:
	return Vector3(a[0], a[1], a[2])


func _marks(kind: String) -> Array:
	return _layout["marks"].get(kind, [])


func _material(n: String) -> Material:
	return load(HallMaterials.PATH % n)


func _omni(n: String, pos: Vector3, color: Color, energy: float, rng: float, shadow := false, parent: Node = null,
		bake := Light3D.BAKE_STATIC) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = color
	l.light_energy = energy
	l.omni_range = rng
	l.omni_attenuation = 1.0
	l.shadow_enabled = shadow
	l.light_bake_mode = bake
	l.light_indirect_energy = BOUNCE
	_add(l, parent, n)
	return l


func _scene() -> void:
	_layout = JSON.parse_string(FileAccess.get_file_as_string(HallMaterials.LAYOUT))
	_root = Node3D.new()
	_root.name = "Hall"
	_root.set_script(load("res://scripts/hall.gd"))

	# --- geometry -----------------------------------------------------------
	var glb: PackedScene = load("res://assets/models/hall.glb")
	var geo := glb.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
	_add(geo, null, "Geometry")

	# --- collision ----------------------------------------------------------
	var body := StaticBody3D.new()
	body.collision_layer = Layers.SCENERY
	body.collision_mask = 0
	_add(body, null, "Collision")
	var i := 0
	for c in _layout["colliders"]:
		var cs := CollisionShape3D.new()
		var x: Array = c["xf"]
		cs.transform = Transform3D(Basis(Vector3(x[0], x[4], x[8]), Vector3(x[1], x[5], x[9]), Vector3(x[2], x[6], x[10])).orthonormalized(),
			Vector3(x[3], x[7], x[11]))
		var s: Array = c["size"]
		if c["kind"] == "cyl":
			var sh := CylinderShape3D.new()
			sh.radius = s[0] * 0.5
			sh.height = s[1]
			cs.shape = sh
		else:
			var bx := BoxShape3D.new()
			bx.size = Vector3(s[0], s[1], s[2])
			cs.shape = bx
		_add(cs, body, "C%03d" % i)
		i += 1

	# --- environment --------------------------------------------------------
	var env := Environment.new()
	var sky := Sky.new()
	var pano := PanoramaSkyMaterial.new()
	pano.panorama = load("res://assets/hdri/kloppenheim_06_puresky.hdr")
	pano.energy_multiplier = 0.35
	sky.sky_material = pano
	sky.radiance_size = Sky.RADIANCE_SIZE_128
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.36, 0.3, 0.3)
	env.ambient_light_energy = 0.12
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_exposure = 1.0
	env.tonemap_white = 8.0
	env.ssao_enabled = true
	env.ssao_radius = 0.7
	env.ssao_intensity = 2.2
	env.ssao_power = 1.6
	env.ssao_light_affect = 0.15
	env.ssil_enabled = true
	env.ssil_radius = 3.0
	env.ssil_intensity = 0.9
	env.glow_enabled = true
	env.glow_intensity = 0.42
	env.glow_strength = 1.0
	env.glow_bloom = 0.04
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SCREEN
	env.glow_hdr_threshold = 1.1
	env.glow_hdr_scale = 1.6
	env.set_glow_level(0, 0.0)
	env.set_glow_level(1, 0.4)
	env.set_glow_level(2, 0.8)
	env.set_glow_level(3, 1.0)
	env.set_glow_level(4, 0.8)
	env.set_glow_level(5, 0.5)
	env.set_glow_level(6, 0.3)
	env.volumetric_fog_enabled = true
	env.volumetric_fog_density = 0.006
	env.volumetric_fog_albedo = Color(0.95, 0.9, 0.85)
	env.volumetric_fog_anisotropy = 0.45
	env.volumetric_fog_length = 40.0
	env.volumetric_fog_ambient_inject = 0.0
	env.volumetric_fog_temporal_reprojection_enabled = true
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.08
	env.adjustment_saturation = 1.06
	var we := WorldEnvironment.new()
	we.environment = env
	_add(we, null, "WorldEnvironment")

	var lights := Node3D.new()
	_add(lights, null, "Lights")

	# --- windows ------------------------------------------------------------
	var win := Node3D.new()
	_add(win, null, "Windows")
	var gmat := _material("glass")
	i = 0
	for g in _marks("glass"):
		var mi := MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(g["size"][0], g["size"][1])
		var gm: ShaderMaterial = gmat.duplicate()
		gm.set_shader_parameter("size", q.size)
		q.material = gm
		mi.mesh = q
		mi.position = _v(g["pos"])
		mi.rotation.y = g["yaw"]
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		_add(mi, win, "Glass%d" % i)
		_fog_light(win, i, mi.position, Vector3(0, 0, 1).rotated(Vector3.UP, g["yaw"]))
		i += 1

	# --- hearth fire ----------------------------------------------------------
	var fire_marks := _marks("fire")
	if fire_marks.size() > 0:
		_build_fire(_v(fire_marks[0]["pos"]))

	# --- candles ----------------------------------------------------------------
	_build_candles()

	# --- lamps from the layout: the lightmap bakes them; hall.gd keeps those that light or shadow characters live
	i = 0
	for l in _marks("light"):
		var col := Color(l["color"][0], l["color"][1], l["color"][2])
		var o := _omni("%s%d" % [l.get("name", "Light"), i], _v(l["pos"]), col, l["energy"], l["range"], l.get("shadow", false), lights)
		o.light_size = l.get("size", 0.0)
		o.light_specular = l.get("specular", 0.5)
		o.light_volumetric_fog_energy = l.get("fog", 0.6)
		if l.get("shadow", false):
			o.shadow_bias = 0.06
			o.shadow_normal_bias = 1.2
			o.shadow_blur = 1.2
		if l.get("shadows_characters", false):
			o.add_to_group(Hall.SHADOW_LIGHTS, true)
		if l.get("lights_characters", false):
			o.add_to_group(Hall.CHARACTER_LIGHTS, true)
		i += 1

	# --- reflections, one probe a room, + lightmap -----------------------------------------
	# each probe renders once, so it sees only the scenery: figures standing there then would stay in it
	i = 0
	for p in _marks("probe"):
		var probe := ReflectionProbe.new()
		probe.cull_mask = Layers.SCENERY
		probe.position = _v(p["pos"])
		probe.size = _v(p["size"])
		probe.origin_offset = _v(p["offset"])
		probe.box_projection = true
		probe.interior = true
		probe.enable_shadows = false
		probe.update_mode = ReflectionProbe.UPDATE_ONCE
		probe.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
		probe.intensity = 0.8
		probe.max_distance = 40.0
		_add(probe, null, "ReflectionProbe%d" % i)
		i += 1

	var lm := LightmapGI.new()
	lm.quality = LightmapGI.BAKE_QUALITY_HIGH
	lm.bounces = 5
	lm.directional = true
	lm.interior = true
	lm.max_texture_size = 4096
	lm.generate_probes_subdiv = LightmapGI.GENERATE_PROBES_SUBDIV_32  # of the building's length: a probe every 2.2 m
	_add(lm, null, "LightmapGI")

	# --- spawn ---------------------------------------------------------------------
	var sp := Marker3D.new()
	var spm := _marks("spawn")
	sp.position = _v(spm[0]["pos"]) if spm.size() > 0 else Vector3(0, 0, 5.5)
	_add(sp, null, "PlayerSpawn")

	var ps := PackedScene.new()
	var err := ps.pack(_root)
	if err != OK:
		push_error("pack failed: " + error_string(err))
	err = ResourceSaver.save(ps, SCENE)
	print("saved ", SCENE, " -> ", error_string(err), "  colliders=", _layout["colliders"].size())
	_root.free()


## Daylight through one window: fog outside makes the whole pane a soft source with no sunbeam.
func _fog_light(parent: Node, i: int, glass: Vector3, into: Vector3) -> void:
	var l := SpotLight3D.new()
	l.light_color = Color(0.72, 0.84, 1.0)
	l.light_energy = 42.0
	l.light_specular = 0.25
	l.light_size = 1.0
	l.light_volumetric_fog_energy = 0.35
	l.spot_range = 8.0
	l.spot_attenuation = 1.25
	l.spot_angle = 43.0
	l.spot_angle_attenuation = 1.5
	l.light_bake_mode = Light3D.BAKE_STATIC
	l.light_indirect_energy = BOUNCE
	l.add_to_group(Hall.CHARACTER_LIGHTS, true)
	_add(l, parent, "FogLight%d" % i)
	var at := glass + into * 0.1
	l.look_at_from_position(at, at + into + Vector3.DOWN * 1.0, Vector3.UP)


func _build_fire(p: Vector3) -> void:
	var fire := Node3D.new()
	fire.position = p
	_add(fire, null, "Fire")
	# flame cards
	var cards := [
		# x, y, z, w, h, material
		[0.0, 0.2, 0.0, 1.05, 1.15, 0],
		[-0.28, 0.16, 0.08, 0.7, 0.85, 1],
		[0.3, 0.17, -0.06, 0.72, 0.9, 2],
		[0.05, 0.3, -0.14, 0.6, 0.95, 3],
		[-0.12, 0.1, 0.18, 0.5, 0.6, 2],
		[0.2, 0.1, 0.16, 0.45, 0.55, 1],
		[-0.42, 0.12, -0.08, 0.4, 0.5, 3],
		[0.46, 0.12, 0.05, 0.38, 0.48, 0],
	]
	var k := 0
	for c in cards:
		var mi := MeshInstance3D.new()
		var q := QuadMesh.new()
		q.size = Vector2(c[3], c[4])
		q.center_offset = Vector3(0, c[4] * 0.5, 0)
		q.material = _material("flame%d" % c[5])
		mi.mesh = q
		mi.position = Vector3(c[0], c[1], c[2])
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		mi.extra_cull_margin = 1.0
		_add(mi, fire, "Flame%d" % k)
		k += 1
	# sparks
	var pm := ParticleProcessMaterial.new()
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	pm.emission_box_extents = Vector3(0.4, 0.08, 0.2)
	pm.direction = Vector3(0, 1, 0)
	pm.spread = 22.0
	pm.initial_velocity_min = 0.5
	pm.initial_velocity_max = 1.6
	pm.gravity = Vector3(0, 0.35, 0)
	pm.damping_min = 0.2
	pm.damping_max = 0.6
	pm.scale_min = 0.5
	pm.scale_max = 1.3
	pm.turbulence_enabled = true
	pm.turbulence_noise_strength = 0.6
	pm.turbulence_noise_scale = 2.5
	pm.turbulence_influence_min = 0.05
	pm.turbulence_influence_max = 0.2
	var grad := Gradient.new()
	grad.offsets = PackedFloat32Array([0.0, 0.15, 0.7, 1.0])
	grad.colors = PackedColorArray([Color(1, 0.8, 0.4, 0), Color(1, 0.7, 0.3, 1), Color(1, 0.3, 0.05, 0.8), Color(0.6, 0.1, 0.0, 0)])
	var gt := GradientTexture1D.new()
	gt.gradient = grad
	pm.color_ramp = gt
	var sparks := GPUParticles3D.new()
	sparks.amount = 36
	sparks.lifetime = 1.9
	sparks.randomness = 0.6
	sparks.process_material = pm
	sparks.position = Vector3(0, 0.3, 0)
	sparks.visibility_aabb = AABB(Vector3(-1.5, -0.5, -1.5), Vector3(3, 3, 3))
	var sq := QuadMesh.new()
	sq.size = Vector2(0.012, 0.012)
	sq.material = _material("spark")
	sparks.draw_pass_1 = sq
	sparks.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_add(sparks, fire, "Sparks")
	# lights: a shadowed key that swells slowly across the room, and a quick flicker inside the hearth.
	# A point overstates how a broad flame mirrors in the polished floor, hence the key's low specular.
	var key := _omni("FireKey", Vector3(0, 0.85, 0.95), Color(1.0, 0.55, 0.22), 5.5, 17.0, true, fire, Light3D.BAKE_DYNAMIC)
	key.light_specular = 0.15
	key.shadow_bias = 0.05
	key.shadow_normal_bias = 1.5
	key.shadow_blur = 3.0
	key.light_volumetric_fog_energy = 0.03
	key.set_script(load("res://scripts/hall_fire_light.gd"))
	key.set("base_energy", 5.5)
	key.set("flicker", 0.16)
	key.set("speed", 4.0)
	var fill := _omni("FireFill", Vector3(0, 0.45, 0.0), Color(1.0, 0.45, 0.16), 0.5, 2.2, false, fire, Light3D.BAKE_DYNAMIC)
	fill.light_specular = 0.0
	fill.light_volumetric_fog_energy = 0.0
	fill.set_script(load("res://scripts/hall_fire_light.gd"))
	fill.set("base_energy", 0.5)
	fill.set("flicker", 0.15)
	fill.set("speed", 6.0)


func _build_candles() -> void:
	var marks := _marks("candle")
	if marks.is_empty():
		return
	var q := QuadMesh.new()
	q.size = Vector2(0.3, 0.3)
	q.center_offset = Vector3(0, 0.038, 0)
	q.material = _material("candle_flame")
	var pts := PackedVector3Array()
	for m in marks:
		pts.append(_v(m["pos"]))
	var mmi := MultiMeshInstance3D.new()
	mmi.set_script(load("res://scripts/hall_candles.gd"))
	mmi.set("points", pts)
	mmi.set("flame_mesh", q)
	mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	mmi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
	_add(mmi, null, "CandleFlames")

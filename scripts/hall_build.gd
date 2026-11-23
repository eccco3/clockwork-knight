extends SceneTree
## Offline builder for the great hall. Not used at runtime.
##
##   godot --headless --path . --script res://scripts/hall_build.gd -- materials
##   godot --headless --path . --import
##   godot --headless --path . --script res://scripts/hall_build.gd -- scene
##   godot --path . --script res://scripts/hall_build.gd -- bake      (needs a window: GPU voxel bake)
##
## "materials" writes materials/hall_*.tres from the Poly Haven scans, "scene" assembles
## scenes/hall.tscn from assets/models/hall.glb + hall_layout.json, "bake" bakes the VoxelGI
## and stores it in assets/models/hall_voxelgi.res.

const TEX := "res://assets/textures/%s/%s.jpg"
const MAT := "res://materials/hall_%s.tres"
const GI_DATA := "res://assets/models/hall_voxelgi.res"
const SCENE := "res://scenes/hall.tscn"

var _root: Node3D
var _layout: Dictionary


func _init() -> void:
	var mode := "scene"
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		mode = args[0]
	match mode:
		"materials":
			_materials()
			quit()
		"scene":
			_scene()
			quit()
		"bake":
			_bake()
		_:
			push_error("unknown mode " + mode)
			quit(1)


# ---------------------------------------------------------------------------
# materials
# ---------------------------------------------------------------------------

func _std(n: String, tex: String, tint := Color.WHITE, rough := 1.0, o := {}) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.resource_name = "hall_" + n
	m.vertex_color_use_as_albedo = o.get("vcol", true)
	m.albedo_color = tint
	if tex != "":
		if o.get("albedo", true) and ResourceLoader.exists(TEX % [tex, "albedo"]):
			m.albedo_texture = load(TEX % [tex, "albedo"])
		m.normal_enabled = true
		m.normal_texture = load(TEX % [tex, "normal"])
		m.normal_scale = o.get("normal", 1.0)
		var arm: Texture2D = load(TEX % [tex, "arm"])
		m.roughness_texture = arm
		m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_GREEN
		if o.get("ao", true):
			m.ao_enabled = true
			m.ao_texture = arm
			m.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED
			m.ao_light_affect = o.get("ao_affect", 0.35)
	m.roughness = rough
	m.metallic = o.get("metallic", 0.0)
	m.metallic_specular = o.get("spec", 0.5)
	if o.get("vsrgb", false):
		m.vertex_color_is_srgb = true
	if o.has("uv"):
		m.uv1_scale = Vector3(o["uv"], o["uv"], 1.0)
	if o.has("emission"):
		m.emission_enabled = true
		m.emission = o["emission"]
		m.emission_energy_multiplier = o.get("emission_energy", 1.0)
	if o.get("two_sided", false):
		m.cull_mode = BaseMaterial3D.CULL_DISABLED
	if o.has("rim"):
		m.rim_enabled = true
		m.rim = o["rim"]
		m.rim_tint = 0.6
	if o.has("clearcoat"):
		m.clearcoat_enabled = true
		m.clearcoat = o["clearcoat"]
		m.clearcoat_roughness = 0.25
	if o.has("backlight"):
		m.backlight_enabled = true
		m.backlight = o["backlight"]
	if o.has("height"):
		m.heightmap_enabled = true
		m.heightmap_texture = load(TEX % [tex, "height"])
		m.heightmap_scale = o["height"]
		m.heightmap_deep_parallax = true
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	_save(m, MAT % n)
	return m


func _shader(n: String, shader: String, params := {}) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.resource_name = "hall_" + n
	m.shader = load("res://shaders/%s.gdshader" % shader)
	for k in params:
		m.set_shader_parameter(k, params[k])
	_save(m, MAT % n)
	return m


func _save(res: Resource, path: String) -> void:
	var err := ResourceSaver.save(res, path)
	if err != OK:
		push_error("save failed %s: %s" % [path, error_string(err)])
	res.take_over_path(path)


func _noise(n: String, type: int, freq: float, octaves := 4, size := 256) -> NoiseTexture2D:
	var fn := FastNoiseLite.new()
	fn.noise_type = type
	fn.frequency = freq
	fn.fractal_octaves = octaves
	fn.seed = n.hash() % 10000
	var t := NoiseTexture2D.new()
	t.width = size
	t.height = size
	t.seamless = true
	t.noise = fn
	t.generate_mipmaps = true
	_save(t, "res://materials/hall_noise_%s.tres" % n)
	return t


func _tex(id: String, map: String) -> Texture2D:
	return load(TEX % [id, map])


func _gen(n: String) -> Texture2D:
	var p := "res://assets/textures/hall_gen/%s.png" % n
	if ResourceLoader.exists(p):
		return load(p)
	return null


func _materials() -> void:
	DirAccess.make_dir_recursive_absolute("res://materials")
	var soft := _noise("soft", FastNoiseLite.TYPE_SIMPLEX_SMOOTH, 0.012, 5)
	var flame := _noise("flame", FastNoiseLite.TYPE_SIMPLEX_SMOOTH, 0.02, 4)
	var cell := _noise("cell", FastNoiseLite.TYPE_SIMPLEX_SMOOTH, 0.03, 5)

	# --- timber -------------------------------------------------------------
	_std("wood_beam", "rough_wood", Color(0.98, 0.86, 0.76), 0.92, {"normal": 1.3, "ao_affect": 0.5})
	_shader("wood_floor", "hall_surface", {
		"albedo_tex": _tex("wood_table_worn", "albedo"), "normal_tex": _tex("wood_table_worn", "normal"),
		"orm_tex": _tex("wood_table_worn", "arm"), "macro_tex": soft,
		"tint": Vector3(1.08, 1.0, 0.9), "normal_strength": 0.9, "macro_strength": 0.2, "macro_scale": 0.13,
		"roughness_scale": 0.62, "saturation": 0.8,
	})
	_shader("wood_panel", "hall_surface", {
		"albedo_tex": _tex("wood_cabinet_worn_long", "albedo"), "normal_tex": _tex("wood_cabinet_worn_long", "normal"),
		"orm_tex": _tex("wood_cabinet_worn_long", "arm"), "macro_tex": soft,
		"tint": Vector3(0.9, 0.86, 0.8), "normal_strength": 1.0, "macro_strength": 0.15, "macro_scale": 0.3,
		"roughness_scale": 0.8, "saturation": 0.7,
	})
	_std("wood_dark", "fine_grained_wood", Color(1.1, 1.0, 0.92), 0.7)
	_std("wood_red", "dark_wood", Color(0.85, 0.8, 0.78), 0.6)
	_std("wood_oak", "oak_veneer_01", Color(0.62, 0.48, 0.36), 0.75)
	_std("wood_table", "fine_grained_wood", Color(1.5, 1.3, 1.08), 0.55)
	_std("wood_roof", "planks_brown_10", Color(0.56, 0.47, 0.39), 0.95, {"normal": 1.2})
	_std("bark", "bark_brown_02", Color(0.8, 0.72, 0.62), 1.0, {"normal": 1.5})
	var eg := _std("endgrain", "", Color(1, 1, 1), 0.9)
	if _gen("endgrain"):
		eg.albedo_texture = _gen("endgrain")
		_save(eg, MAT % "endgrain")
	# --- masonry / plaster --------------------------------------------------
	_shader("plaster", "hall_surface", {
		"albedo_tex": _tex("painted_plaster_wall", "albedo"), "normal_tex": _tex("white_rough_plaster", "normal"),
		"orm_tex": _tex("painted_plaster_wall", "arm"), "macro_tex": soft,
		"tint": Vector3(1.32, 1.2, 0.98), "normal_strength": 0.55, "macro_strength": 0.22, "macro_scale": 0.11,
		"roughness_scale": 1.0, "grime_height": 2.2, "grime_strength": 0.12,
	})
	_shader("stone", "hall_surface", {
		"albedo_tex": _tex("rough_concrete", "albedo"), "normal_tex": _tex("rough_concrete", "normal"),
		"orm_tex": _tex("rough_concrete", "arm"), "macro_tex": soft,
		"tint": Vector3(0.9, 0.83, 0.74), "normal_strength": 1.4, "macro_strength": 0.3, "macro_scale": 0.45,
		"roughness_scale": 1.0, "grime_height": 0.0, "grime_strength": 0.0,
	})
	_std("stone_flag", "rock_surface", Color(1.25, 1.18, 1.1), 0.85, {"normal": 1.2})
	_std("mortar", "", Color(0.36, 0.33, 0.29), 1.0)
	# --- metal --------------------------------------------------------------
	_std("iron", "rusty_metal_02", Color(0.075, 0.07, 0.068), 0.75, {"albedo": false, "metallic": 0.8, "normal": 0.5, "ao": false})
	_std("pewter", "", Color(0.5, 0.5, 0.49), 0.42, {"metallic": 0.65})
	_std("brass", "", Color(0.85, 0.62, 0.28), 0.4, {"metallic": 1.0})
	# --- misc ---------------------------------------------------------------
	_std("wax", "", Color(0.95, 0.9, 0.78), 0.45, {"emission": Color(1.0, 0.62, 0.3), "emission_energy": 0.22})
	_std("ceramic", "", Color(1, 1, 1), 0.28, {"clearcoat": 0.6, "vsrgb": true})
	_std("leather", "brown_leather", Color(1, 1, 1), 0.8, {"albedo": false, "normal": 1.2, "vsrgb": true})
	_std("paper", "", Color(0.86, 0.8, 0.66), 0.9)
	_std("velvet", "floral_jacquard", Color(1, 1, 1), 1.0, {"albedo": false, "rim": 0.15, "vsrgb": true, "uv": 1.6, "normal": 1.6, "spec": 0.25})
	_std("linen", "rough_linen", Color(1, 1, 1), 1.0, {"albedo": false, "vsrgb": true})
	_std("wool", "wool_boucle", Color(1, 1, 1), 1.0, {"albedo": false, "vsrgb": true})
	_std("hessian", "hessian_230", Color(1, 1, 1), 1.0, {"uv": 2.0, "normal": 1.5})
	_std("paint", "", Color(1, 1, 1), 0.6)
	_std("food", "", Color(1, 1, 1), 0.5, {"vsrgb": true})
	_std("rope", "hessian_230", Color(0.9, 0.8, 0.6), 1.0, {"uv": 3.0})
	var rug := _gen("rug")
	_shader("rug", "hall_cloth", {"pattern_tex": rug, "weave_normal": _tex("wool_boucle", "normal"), "weave_orm": _tex("wool_boucle", "arm"),
		"weave_scale": Vector2(14, 24), "normal_strength": 1.0, "fuzz": 0.3, "saturation": 0.78, "brightness": 0.55})
	_shader("banner", "hall_cloth_2s", {"pattern_tex": _gen("banners"), "weave_normal": _tex("rough_linen", "normal"), "weave_orm": _tex("rough_linen", "arm"),
		"weave_scale": Vector2(5, 9), "normal_strength": 0.8, "fuzz": 0.2})
	_shader("tapestry", "hall_cloth_2s", {"pattern_tex": _gen("tapestry"), "weave_normal": _tex("hessian_230", "normal"), "weave_orm": _tex("hessian_230", "arm"),
		"weave_scale": Vector2(9, 9), "normal_strength": 0.7, "fuzz": 0.25})
	var shd := _std("shield", "", Color(1, 1, 1), 0.55, {"vcol": false})
	if _gen("shields"):
		shd.albedo_texture = _gen("shields")
		_save(shd, MAT % "shield")
	var cf := _std("clockface", "", Color(1, 1, 1), 0.5, {"vcol": false})
	if _gen("clockface"):
		cf.albedo_texture = _gen("clockface")
		_save(cf, MAT % "clockface")
	# --- fire ---------------------------------------------------------------
	_shader("ember", "hall_ember", {"noise_tex": cell, "glow": 1.7, "coverage": 0.55, "scale": 1.3})
	_shader("log_burn", "hall_ember", {"noise_tex": cell, "glow": 1.6, "coverage": 0.3, "scale": 0.4, "ash_amount": 0.25, "char_color": Color(0.03, 0.024, 0.02)})
	for i in 4:
		_shader("flame%d" % i, "hall_flame", {"noise_tex": flame, "seed": float(i) * 1.37 + 0.4, "speed": 0.85 + 0.12 * i,
			"intensity": 0.6, "lean": (i - 1.5) * 0.12})
	_shader("candle_flame", "hall_candle_flame", {"intensity": 6.0})
	_shader("glass", "hall_glass", {})
	var spark := StandardMaterial3D.new()
	spark.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	spark.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	spark.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	spark.albedo_color = Color(1.0, 0.55, 0.15)
	spark.vertex_color_use_as_albedo = true
	spark.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	spark.billboard_keep_scale = true
	spark.emission_enabled = true
	spark.emission = Color(1.0, 0.45, 0.1)
	spark.emission_energy_multiplier = 6.0
	_save(spark, MAT % "spark")
	print("materials written")


# ---------------------------------------------------------------------------
# scene
# ---------------------------------------------------------------------------

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


func _omni(n: String, pos: Vector3, color: Color, energy: float, rng: float, shadow := false, parent: Node = null) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = pos
	l.light_color = color
	l.light_energy = energy
	l.omni_range = rng
	l.omni_attenuation = 1.0
	l.shadow_enabled = shadow
	l.light_bake_mode = Light3D.BAKE_DYNAMIC
	_add(l, parent, n)
	return l


func _scene() -> void:
	_layout = JSON.parse_string(FileAccess.get_file_as_string("res://assets/models/hall_layout.json"))
	var dims: Dictionary = _layout["dims"]
	var hw: float = dims["hw"]
	var hl: float = dims["hl"]
	var apex: float = dims["apex"]
	_root = Node3D.new()
	_root.name = "Hall"

	# --- geometry -----------------------------------------------------------
	var glb: PackedScene = load("res://assets/models/hall.glb")
	var geo := glb.instantiate(PackedScene.GEN_EDIT_STATE_INSTANCE)
	_add(geo, null, "Geometry")

	# --- collision ----------------------------------------------------------
	var body := StaticBody3D.new()
	body.collision_layer = 1
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
	env.volumetric_fog_gi_inject = 0.6
	env.volumetric_fog_temporal_reprojection_enabled = true
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.08
	env.adjustment_saturation = 1.06
	var we := WorldEnvironment.new()
	we.environment = env
	_add(we, null, "WorldEnvironment")

	# --- dusk light through the east windows --------------------------------
	var lights := Node3D.new()
	_add(lights, null, "Lights")
	var sun := DirectionalLight3D.new()
	sun.light_color = Color(0.36, 0.52, 1.0)
	sun.light_energy = 2.8
	sun.light_specular = 0.35
	sun.light_angular_distance = 0.0
	sun.shadow_enabled = true
	sun.shadow_bias = 0.04
	sun.shadow_normal_bias = 1.5
	sun.shadow_blur = 2.2
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 34.0
	sun.light_volumetric_fog_energy = 1.0
	sun.light_bake_mode = Light3D.BAKE_DYNAMIC
	_add(sun, lights, "DuskLight")
	sun.look_at_from_position(Vector3(10, 9, 5), Vector3(10, 9, 5) + Vector3(-0.72, -0.5, -0.36), Vector3.UP)

	# --- windows ------------------------------------------------------------
	var win := Node3D.new()
	_add(win, null, "Windows")
	var rot := {"R": -PI / 2, "L": PI / 2, "D": PI, "F": 0.0}
	var gmat: Material = load(MAT % "glass")
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
		mi.rotation.y = rot[g["wall"]]
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.gi_mode = GeometryInstance3D.GI_MODE_DISABLED
		_add(mi, win, "Glass%d" % i)
		# soft cool sky-glow spilling in from each window
		var into := Vector3(0, 0, 1).rotated(Vector3.UP, rot[g["wall"]])
		var sl := _omni("SkyGlow%d" % i, mi.position + into * 0.9 + Vector3(0, 0.3, 0), Color(0.42, 0.56, 1.0), 0.75, 5.0, false, win)
		sl.light_specular = 0.2
		sl.light_volumetric_fog_energy = 0.0
		i += 1

	# --- hearth fire ----------------------------------------------------------
	var fire_marks := _marks("fire")
	if fire_marks.size() > 0:
		_build_fire(_v(fire_marks[0]["pos"]))

	# --- candles ----------------------------------------------------------------
	_build_candles()

	# --- chandelier / misc lights from the layout -------------------------------
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
			o.shadow_blur = 2.4
		i += 1

	# --- reflection + GI ----------------------------------------------------------
	var probe := ReflectionProbe.new()
	probe.position = Vector3(0, 3.0, 0)
	probe.size = Vector3(hw * 2 + 0.4, 6.4, hl * 2 + 0.4)
	probe.origin_offset = Vector3(0, -1.2, 2.0)
	probe.box_projection = true
	probe.interior = true
	probe.enable_shadows = false
	probe.update_mode = ReflectionProbe.UPDATE_ONCE
	probe.ambient_mode = ReflectionProbe.AMBIENT_DISABLED
	probe.intensity = 0.8
	probe.max_distance = 40.0
	_add(probe, null, "ReflectionProbe")

	var gi := VoxelGI.new()
	gi.position = Vector3(0, apex * 0.5 - 0.2, 0)
	gi.size = Vector3(hw * 2 + 1.8, apex + 1.4, hl * 2 + 1.8)
	gi.subdiv = VoxelGI.SUBDIV_128
	if ResourceLoader.exists(GI_DATA):
		gi.data = load(GI_DATA)
	_add(gi, null, "VoxelGI")

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
		q.material = load(MAT % ("flame%d" % c[5]))
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
	sq.material = load(MAT % "spark")
	sparks.draw_pass_1 = sq
	sparks.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_add(sparks, fire, "Sparks")
	# lights: a shadowed key that flickers, and a broad soft fill that carries the warmth
	var key := _omni("FireKey", Vector3(0, 0.85, 0.95), Color(1.0, 0.55, 0.22), 5.5, 17.0, true, fire)
	key.shadow_bias = 0.05
	key.shadow_normal_bias = 1.5
	key.shadow_blur = 2.6
	key.light_volumetric_fog_energy = 0.03
	key.set_script(load("res://scripts/hall_fire_light.gd"))
	key.set("base_energy", 5.5)
	key.set("flicker", 0.22)
	key.set("wander", 0.05)
	var fill := _omni("FireFill", Vector3(0, 0.45, 0.0), Color(1.0, 0.45, 0.16), 0.5, 2.2, false, fire)
	fill.light_specular = 0.0
	fill.light_volumetric_fog_energy = 0.0
	fill.set_script(load("res://scripts/hall_fire_light.gd"))
	fill.set("base_energy", 0.5)
	fill.set("flicker", 0.15)
	fill.set("wander", 0.0)
	fill.set("speed", 6.0)


func _build_candles() -> void:
	var marks := _marks("candle")
	if marks.is_empty():
		return
	var q := QuadMesh.new()
	q.size = Vector2(0.3, 0.3)
	q.center_offset = Vector3(0, 0.038, 0)
	q.material = load(MAT % "candle_flame")
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


# ---------------------------------------------------------------------------
# VoxelGI bake (windowed run)
# ---------------------------------------------------------------------------

func _bake() -> void:
	await process_frame
	var packed: PackedScene = load(SCENE)
	var hall: Node3D = packed.instantiate()
	root.add_child(hall)
	for n in 20:
		await process_frame
	var gi: VoxelGI = hall.get_node("VoxelGI")
	gi.data = null
	print("baking VoxelGI ...")
	gi.bake(hall)
	for n in 10:
		await process_frame
	var data := gi.data
	if data == null:
		push_error("bake produced no data")
		quit(1)
		return
	data.interior = true
	data.energy = 1.0
	data.dynamic_range = 6.0
	data.propagation = 0.55
	data.bias = 1.5
	data.normal_bias = 1.0
	data.use_two_bounces = true
	var err := ResourceSaver.save(data, GI_DATA, ResourceSaver.FLAG_COMPRESS)
	print("saved ", GI_DATA, " -> ", error_string(err))
	quit()

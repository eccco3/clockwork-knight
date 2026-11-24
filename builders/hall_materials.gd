extends SceneTree
## Offline builder: writes materials/hall_*.tres from the Poly Haven scans and the generated
## pattern images. The hall's glb names these materials, and builders/hall_scene.gd uses some.
##
##   godot --headless --path . --script res://builders/hall_materials.gd

const PATH := "res://materials/hall_%s.tres"
const TEX := "res://assets/textures/%s/%s.jpg"


func _init() -> void:
	_materials()
	quit()


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
	_save(m, PATH % n)
	return m


func _shader(n: String, shader: String, params := {}) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.resource_name = "hall_" + n
	m.shader = load("res://shaders/%s.gdshader" % shader)
	for k in params:
		m.set_shader_parameter(k, params[k])
	_save(m, PATH % n)
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
		_save(eg, PATH % "endgrain")
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
		_save(shd, PATH % "shield")
	var cf := _std("clockface", "", Color(1, 1, 1), 0.5, {"vcol": false})
	if _gen("clockface"):
		cf.albedo_texture = _gen("clockface")
		_save(cf, PATH % "clockface")
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
	_save(spark, PATH % "spark")
	print("materials written")

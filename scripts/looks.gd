class_name Looks
## The finishes that carved clockwork figures wear. Each function makes a material in the colours
## it is given, so figures share the looks and bring their own palettes. `dress()` puts them on a
## model, whose materials say by name which part is which.

const WOOD := preload("res://shaders/knight_wood.gdshader")
const SURFACE := preload("res://shaders/knight_surface.gdshader")
const EYE := preload("res://shaders/knight_eye.gdshader")


## Replaces each material of `mesh` whose name is a key of `looks`.
static func dress(mesh: MeshInstance3D, looks: Dictionary[String, Material]) -> void:
	for s in mesh.mesh.get_surface_count():
		var named := mesh.mesh.surface_get_material(s)
		if named and looks.has(named.resource_name):
			mesh.set_surface_override_material(s, looks[named.resource_name])


## Oiled, waxed wood. `early` and `late` colour the two halves of each growth ring.
static func oiled_wood(early: Color, late: Color) -> ShaderMaterial:
	return _wood(early, late, {"ring_density": 135.0, "ring_contrast": 0.55})


## Close-grained wood for a face, under the lacquer that the figure's build baked into `paint`.
## `placement` is the file the build wrote beside that texture, saying where on the head it goes.
static func face_wood(early: Color, late: Color, paint: Texture2D, placement: JSON) -> ShaderMaterial:
	var at: Dictionary = placement.data
	return _wood(early, late, {"ring_density": 170.0, "ring_contrast": 0.30, "pore_strength": 0.12,
		"fiber_strength": 0.12, "figure_strength": 0.10, "bump": 0.05, "paint_tex": paint,
		"paint_origin": Vector3(at.origin[0], at.origin[1], at.origin[2]),
		"paint_size": Vector3(at.half_width, at.bottom, at.top)})


## Wood under a glossy coat of lacquer, as on armour.
static func lacquered_wood(early: Color, late: Color) -> ShaderMaterial:
	return _wood(early, late, {"ring_density": 120.0, "ring_contrast": 0.62, "figure_strength": 0.40,
		"coat": 0.9, "coat_roughness": 0.15, "roughness_min": 0.24, "roughness_max": 0.42, "paint": 0.0})


static func brass(colour: Color) -> ShaderMaterial:
	return _surface(colour, {"roughness": 0.26, "tarnish": 0.30})


## Brass left to dull: rougher and more tarnished.
static func dull_brass(colour: Color) -> ShaderMaterial:
	return _surface(colour, {"roughness": 0.42, "tarnish": 0.5})


## Brushed steel. `tarnish` colours its few stained patches.
static func steel(colour: Color, tarnish: Color) -> ShaderMaterial:
	return _surface(colour, {"roughness": 0.30, "tarnish": 0.10, "tarnish_color": tarnish, "streak": 0.95,
		"roughness_var": 0.12})


## Grained leather. `tarnish` colours its worn patches.
static func leather(colour: Color, tarnish: Color) -> ShaderMaterial:
	return _surface(colour, {"metallic": 0.0, "roughness": 0.60, "tarnish": 0.4, "tarnish_color": tarnish,
		"streak": 0.0, "grain_scale": 520.0, "bump": 1.4})


static func glass_eye() -> ShaderMaterial:
	return _material(EYE, {})


static func _wood(early: Color, late: Color, finish: Dictionary) -> ShaderMaterial:
	return _material(WOOD, finish.merged({"color_early": early, "color_late": late}))


static func _surface(albedo: Color, finish: Dictionary) -> ShaderMaterial:
	return _material(SURFACE, finish.merged({"albedo": albedo}))


static func _material(shader: Shader, parameters: Dictionary) -> ShaderMaterial:
	var material := ShaderMaterial.new()
	material.shader = shader
	for parameter: String in parameters:
		material.set_shader_parameter(parameter, parameters[parameter])
	return material

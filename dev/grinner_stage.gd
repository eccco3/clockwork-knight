extends Node3D
## Bare stage for looking at the grinner: overcast sky light, one soft sun, a grey floor.
## With dev/shot.tscn, call=spread stands its four detail levels side by side.

var _grinner: Node3D

func _ready() -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var pano := PanoramaSkyMaterial.new()
	pano.panorama = load("res://assets/hdri/kloppenheim_06_puresky.hdr")
	sky.sky_material = pano
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_white = 6.0
	env.ssao_enabled = true
	var world := WorldEnvironment.new()
	world.environment = env
	add_child(world)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-38, -150, 0)
	sun.light_energy = 1.2
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 20.0
	add_child(sun)

	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(40, 40)
	floor_mesh.mesh = plane
	var grey := StandardMaterial3D.new()
	grey.albedo_color = Color(0.22, 0.22, 0.21)
	grey.roughness = 0.9
	floor_mesh.material_override = grey
	add_child(floor_mesh)

	_grinner = load("res://assets/models/grinner.glb").instantiate()
	add_child(_grinner)

func spread() -> void:
	for mesh: MeshInstance3D in _grinner.find_children("grinner_lod*", "MeshInstance3D", true, false):
		mesh.visibility_range_begin = 0.0
		mesh.visibility_range_end = 0.0
		mesh.position.x = 1.1 * String(mesh.name).right(1).to_int()

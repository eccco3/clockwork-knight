extends Node3D
## Bare test stage for the knight: a gridded floor (so foot sliding shows), a couple of blocks
## to bump into, sky lighting and a warm key light. With dev/shot.tscn, call=stand:<model path>
## puts a model in the knight's place, call=spread:<model path> its detail levels side by side, and
## call=pose:<clip>:<frame> holds the knight in one frame of a clip, counted as her builder counts them.

const FRAMES_PER_SECOND := 30.0

func _ready() -> void:
	var env := Environment.new()
	var sky := Sky.new()
	var pano := PanoramaSkyMaterial.new()
	pano.panorama = load("res://assets/hdri/kloppenheim_06_puresky.hdr")
	sky.sky_material = pano
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 0.7
	env.tonemap_mode = Environment.TONE_MAPPER_ACES
	env.tonemap_white = 6.0
	env.ssao_enabled = true
	env.ssao_radius = 0.6
	env.ssao_intensity = 1.6
	var we := WorldEnvironment.new()
	we.environment = env
	add_child(we)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-42, -150, 0)
	sun.light_color = Color(1.0, 0.86, 0.68)
	sun.light_energy = 1.6
	sun.shadow_enabled = true
	sun.directional_shadow_max_distance = 30.0
	sun.shadow_blur = 1.5
	add_child(sun)
	var fill := OmniLight3D.new()
	fill.position = Vector3(-3, 2.2, -3)
	fill.light_color = Color(1.0, 0.62, 0.32)
	fill.light_energy = 2.0
	fill.omni_range = 9.0
	add_child(fill)

	_box(Vector3(0, -0.25, 0), Vector3(40, 0.5, 40), _grid())
	var stone := StandardMaterial3D.new()
	stone.albedo_color = Color(0.42, 0.40, 0.38)
	stone.roughness = 0.9
	_box(Vector3(14, 0.5, 3), Vector3(1, 1, 1), stone)
	_box(Vector3(-14, 1.5, 6), Vector3(4, 3, 0.4), stone)
	_box(Vector3(12, 0.15, 12), Vector3(3, 0.3, 2), stone)

	var p := Player.new()
	p.name = "Player"
	add_child(p)


func _box(at: Vector3, size: Vector3, mat: Material) -> void:
	var body := StaticBody3D.new()
	body.position = at
	var m := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	m.mesh = bm
	m.material_override = mat
	body.add_child(m)
	var c := CollisionShape3D.new()
	var s := BoxShape3D.new()
	s.size = size
	c.shape = s
	body.add_child(c)
	add_child(body)


func _grid() -> ShaderMaterial:
	var sh := Shader.new()
	sh.code = """
shader_type spatial;
varying vec3 wp;
void vertex() { wp = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz; }
void fragment() {
	vec2 g = abs(fract(wp.xz) - 0.5);
	vec2 w = fwidth(wp.xz) * 1.5;
	float line = 1.0 - min(smoothstep(0.5 - 0.012 - w.x, 0.5 - 0.012, g.x) + smoothstep(0.5 - 0.012 - w.y, 0.5 - 0.012, g.y), 1.0);
	float chk = mod(floor(wp.x) + floor(wp.z), 2.0);
	ALBEDO = mix(vec3(0.05), mix(vec3(0.13, 0.12, 0.11), vec3(0.17, 0.155, 0.14), chk), line);
	ROUGHNESS = 0.75;
}
"""
	var m := ShaderMaterial.new()
	m.shader = sh
	return m


func pose(at: String) -> void:
	var clip_frame := at.rsplit(":", true, 1)
	$Player.set_physics_process(false)
	$Player.knight.pose_at(clip_frame[0], float(clip_frame[1]) / FRAMES_PER_SECOND)


func stand(path: String) -> Node3D:
	$Player.queue_free()
	var model: Node3D = load(path).instantiate()
	add_child(model)
	return model


func spread(path: String) -> void:
	for mesh: MeshInstance3D in stand(path).find_children("*_lod?", "MeshInstance3D", true, false):
		mesh.visibility_range_begin = 0.0
		mesh.visibility_range_end = 0.0
		mesh.visibility_parent = NodePath()
		mesh.position.x = 1.1 * String(mesh.name).right(1).to_int()

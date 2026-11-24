class_name Outdoors
extends Node3D
## Open rolling ground in heavy daytime fog, where the grinners live: scanned earth with mossy
## patches, sparse grass that thins out with distance, and the flat white daylight the hall's
## windows show. Everything is built on load. The knight spawns in the middle and invisible
## walls keep her where there is ground to see.

const HALF := 160.0
const CHUNK := 32
const WALL := 90.0
const GRASS_HALF := 136.0
const GRASS_CHUNK := 16.0
const GRASS_CELL := 0.8
const GRASS_RANGE := 46.0
const MOSS_EDGE := Vector2(0.42, 0.72)
const FOG_DENSITY := 0.055
const FOG_HIGH := Color(0.86, 0.9, 0.96)
const FOG_LOW := Color(0.6, 0.65, 0.71)
const DAYLIGHT := Color(0.8, 0.87, 1.0)
const BRIGHTNESS := 1.6
const MUD := "brown_mud_02"
const MOSS := "forrest_ground_01"
const TEX := "res://assets/textures/%s/%s.jpg"

## Stand-in grinners until they have behaviour: [position, facing, paces]. Pacers waddle for
## PACE_WALK seconds, then stop and turn round.
const GRINNERS := [[Vector3(4, 0, 11), PI + 0.4, true], [Vector3(-0.5, 0, 8), 0.0, false], [Vector3(-5, 0, 12), PI - 0.9, true]]
const PACE_WALK := 7.0
const PACE_TURN := 3.0

var _pacers: Array[Grinner] = []
var _t := 0.0
var _relief := FastNoiseLite.new()
var _swell := FastNoiseLite.new()
var _moss: PackedByteArray
var _moss_tex: ImageTexture
var _noise_tex: ImageTexture


func _ready() -> void:
	_relief.seed = 11
	_relief.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_relief.frequency = 1.0 / 90.0
	_relief.fractal_octaves = 3
	_swell.seed = 5
	_swell.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_swell.frequency = 1.0 / 11.0
	_swell.fractal_type = FastNoiseLite.FRACTAL_NONE
	_build_maps()
	_build_light()
	_build_ground()
	_build_grass()
	_build_walls()
	_place_grinners()
	var p := Player.new()
	p.name = "Player"
	p.position = Vector3(0, height(0, 0) + 0.02, 0)
	add_child(p)


func _process(dt: float) -> void:
	_t += dt
	for k in _pacers.size():
		var g := _pacers[k]
		var walking := fmod(_t + k * 4.0, PACE_WALK + PACE_TURN) < PACE_WALK
		g.gait = move_toward(g.gait, 1.0 if walking else 0.0, dt * 4.0)
		if not walking:
			g.rotation.y += PI / PACE_TURN * dt
		g.position.y = height(g.position.x, g.position.z)


func _place_grinners() -> void:
	for spec in GRINNERS:
		var g := Grinner.new()
		g.position = spec[0] + Vector3.UP * height(spec[0].x, spec[0].z)
		g.rotation.y = spec[1]
		add_child(g)
		if spec[2]:
			_pacers.append(g)


func height(x: float, z: float) -> float:
	return _relief.get_noise_2d(x, z) * 2.8 + _swell.get_noise_2d(x, z) * 0.15


func moss(x: float, z: float) -> float:
	var size := int(HALF * 2.0)
	var i := clampi(int(x + HALF), 0, size - 1)
	var j := clampi(int(z + HALF), 0, size - 1)
	return smoothstep(MOSS_EDGE.x, MOSS_EDGE.y, _moss[j * size + i] / 255.0)


func _build_maps() -> void:
	var patches := FastNoiseLite.new()
	patches.seed = 3
	patches.frequency = 1.0 / 26.0
	patches.fractal_octaves = 4
	var size := int(HALF * 2.0)
	var img := patches.get_image(size, size, false, false, true)
	_moss = img.get_data()
	_moss_tex = ImageTexture.create_from_image(img)
	var slow := FastNoiseLite.new()
	slow.seed = 9
	slow.frequency = 1.0 / 40.0
	var tile := slow.get_seamless_image(256, 256, false, false, 0.1, true)
	tile.generate_mipmaps()
	_noise_tex = ImageTexture.create_from_image(tile)


func _build_light() -> void:
	var sky_mat := ShaderMaterial.new()
	sky_mat.shader = load("res://shaders/outdoors_sky.gdshader")
	sky_mat.set_shader_parameter("fog_high", FOG_HIGH)
	sky_mat.set_shader_parameter("fog_low", FOG_LOW)
	sky_mat.set_shader_parameter("energy", BRIGHTNESS)
	var sky := Sky.new()
	sky.sky_material = sky_mat
	sky.radiance_size = Sky.RADIANCE_SIZE_64
	var env := Environment.new()
	env.background_mode = Environment.BG_SKY
	env.sky = sky
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.ambient_light_energy = 1.0
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	env.tonemap_mode = Environment.TONE_MAPPER_AGX
	env.tonemap_white = 8.0
	env.glow_enabled = true
	env.glow_intensity = 0.25
	env.glow_bloom = 0.02
	env.glow_blend_mode = Environment.GLOW_BLEND_MODE_SCREEN
	env.glow_hdr_threshold = 1.2
	env.fog_enabled = true
	env.fog_mode = Environment.FOG_MODE_EXPONENTIAL
	env.fog_density = FOG_DENSITY
	env.fog_light_color = FOG_LOW
	env.fog_light_energy = BRIGHTNESS
	env.fog_sky_affect = 1.0
	env.adjustment_enabled = true
	env.adjustment_contrast = 1.05
	var we := WorldEnvironment.new()
	we.name = "WorldEnvironment"
	we.environment = env
	add_child(we)

	# fog hides the sun: it lights and shades from high up, and its highlight is the sky's glow around
	# it, because a light's own specular stays a pinpoint glint on lacquer however large the light.
	# No SSAO: it cost 2 ms here for little visible change in this soft light. A 10-degree sun's softer shadows cost 0.3 ms.
	var sun := DirectionalLight3D.new()
	sun.name = "Daylight"
	sun.rotation_degrees = Vector3(-64, -35, 0)
	sun.light_color = DAYLIGHT
	sun.light_energy = 0.35
	sun.light_specular = 0.0
	sun.light_angular_distance = 7.0
	sun.light_volumetric_fog_energy = 0.0
	sun.shadow_enabled = true
	sun.shadow_opacity = 0.8
	sun.shadow_blur = 1.2
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 40.0
	add_child(sun)


func _build_ground() -> void:
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/outdoors_ground.gdshader")
	for k in ["albedo", "normal", "arm", "height"]:
		mat.set_shader_parameter("mud_" + k, load(TEX % [MUD, k]))
		mat.set_shader_parameter("moss_" + k, load(TEX % [MOSS, k]))
	mat.set_shader_parameter("moss_map", _moss_tex)
	mat.set_shader_parameter("noise", _noise_tex)
	mat.set_shader_parameter("map_size", HALF * 2.0)
	mat.set_shader_parameter("moss_edge", MOSS_EDGE)
	var body := StaticBody3D.new()
	body.name = "Ground"
	add_child(body)
	# heights on a one-metre grid, with a border row so every vertex has neighbours for its normal
	var n := int(HALF * 2.0)
	var w := n + 3
	var hs := PackedFloat32Array()
	hs.resize(w * w)
	for j in w:
		for i in w:
			hs[j * w + i] = height(i - 1 - HALF, j - 1 - HALF)
	for cz in range(0, n, CHUNK):
		for cx in range(0, n, CHUNK):
			var mesh := _ground_chunk(hs, w, cx, cz, mat)
			var mi := MeshInstance3D.new()
			mi.mesh = mesh
			mi.visibility_range_end = 150.0
			body.add_child(mi)
			var near := Vector2(cx, cz) - Vector2.ONE * HALF
			if Rect2(near, Vector2.ONE * CHUNK).intersects(Rect2(-Vector2.ONE * (WALL + 2.0), Vector2.ONE * (WALL + 2.0) * 2.0)):
				var cs := CollisionShape3D.new()
				cs.shape = mesh.create_trimesh_shape()
				body.add_child(cs)


func _ground_chunk(hs: PackedFloat32Array, w: int, cx: int, cz: int, mat: Material) -> ArrayMesh:
	var verts := PackedVector3Array()
	var normals := PackedVector3Array()
	var uvs := PackedVector2Array()
	var idx := PackedInt32Array()
	for j in CHUNK + 1:
		for i in CHUNK + 1:
			var g := (cz + j + 1) * w + cx + i + 1
			var p := Vector3(cx + i - HALF, hs[g], cz + j - HALF)
			verts.append(p)
			normals.append(Vector3(hs[g - 1] - hs[g + 1], 2.0, hs[g - w] - hs[g + w]).normalized())
			uvs.append(Vector2(p.x, p.z))
	for j in CHUNK:
		for i in CHUNK:
			var a := j * (CHUNK + 1) + i
			var c := a + CHUNK + 1
			idx.append_array([a, a + 1, c, a + 1, c + 1, c])
	var arr := []
	arr.resize(Mesh.ARRAY_MAX)
	arr[Mesh.ARRAY_VERTEX] = verts
	arr[Mesh.ARRAY_NORMAL] = normals
	arr[Mesh.ARRAY_TEX_UV] = uvs
	arr[Mesh.ARRAY_INDEX] = idx
	var st := SurfaceTool.new()
	st.create_from_arrays(arr)
	st.generate_tangents()
	st.set_material(mat)
	return st.commit()


func _build_grass() -> void:
	var mesh := _tuft()
	var mat := ShaderMaterial.new()
	mat.shader = load("res://shaders/outdoors_grass.gdshader")
	mat.set_shader_parameter("range", GRASS_RANGE)
	mesh.surface_set_material(0, mat)
	var rng := RandomNumberGenerator.new()
	rng.seed = 21
	var clumps := FastNoiseLite.new()
	clumps.seed = 17
	clumps.frequency = 1.0 / 3.5
	clumps.fractal_type = FastNoiseLite.FRACTAL_NONE
	var grass := Node3D.new()
	grass.name = "Grass"
	add_child(grass)
	var chunks := int(GRASS_HALF * 2.0 / GRASS_CHUNK)
	var steps := int(GRASS_CHUNK / GRASS_CELL)
	for gz in chunks:
		for gx in chunks:
			var corner := Vector2(gx, gz) * GRASS_CHUNK - Vector2.ONE * GRASS_HALF
			var centre := corner + Vector2.ONE * GRASS_CHUNK * 0.5
			var tufts := []
			for j in steps:
				for i in steps:
					var x := corner.x + (i + rng.randf()) * GRASS_CELL
					var z := corner.y + (j + rng.randf()) * GRASS_CELL
					var m := moss(x, z)
					if rng.randf() > (0.05 + 1.3 * m) * clampf(0.6 + 1.8 * clumps.get_noise_2d(x, z), 0.0, 2.0):
						continue
					var s := lerpf(0.4, 1.45, pow(rng.randf(), 1.5))
					var b := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3(s, s * rng.randf_range(0.75, 1.3), s))
					var at := Vector3(x - centre.x, height(x, z) - 0.02, z - centre.y)
					tufts.append([Transform3D(b, at), Color(rng.randf(), rng.randf(), rng.randf() * (0.95 - 0.5 * m), 0.0)])
			if tufts.is_empty():
				continue
			var mm := MultiMesh.new()
			mm.transform_format = MultiMesh.TRANSFORM_3D
			mm.use_custom_data = true
			mm.mesh = mesh
			mm.instance_count = tufts.size()
			for k in tufts.size():
				mm.set_instance_transform(k, tufts[k][0])
				mm.set_instance_custom_data(k, tufts[k][1])
			var mmi := MultiMeshInstance3D.new()
			mmi.multimesh = mm
			mmi.position = Vector3(centre.x, 0.0, centre.y)
			mmi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			mmi.visibility_range_end = GRASS_RANGE + GRASS_CHUNK * 0.75
			grass.add_child(mmi)


## A tuft of curved, tapering blades leaning outward. Normals lean up and out so the tuft shades
## as one soft clump.
func _tuft() -> ArrayMesh:
	const SEG := 4
	var rng := RandomNumberGenerator.new()
	rng.seed = 4
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	var v := 0
	for blade in 30:
		var a := rng.randf() * TAU
		var out := Vector3(cos(a), 0.0, sin(a))
		var base := out * sqrt(rng.randf()) * 0.07
		var h := rng.randf_range(0.14, 0.55) * (1.0 - 0.35 * base.length() / 0.07)
		var lean := rng.randf_range(0.15, 1.0) * h * (0.6 + 0.6 * base.length() / 0.07)
		var side := out.rotated(Vector3.UP, PI * 0.5 + rng.randf_range(-0.6, 0.6))
		var half_w := rng.randf_range(0.004, 0.0075)
		var r := rng.randf()
		for i in SEG + 1:
			var t := float(i) / SEG
			var p := base + out * lean * t * t + Vector3.UP * h * t * (1.0 - 0.25 * lean / h * t)
			var face := side.cross(out * 2.0 * lean * t + Vector3.UP * h).normalized()
			if face.dot(out) < 0.0:
				face = -face
			var n := (face * 0.45 + Vector3.UP * 0.7 + out * 0.25).normalized()
			for e in [-1.0, 1.0]:
				st.set_uv(Vector2(r, t))
				st.set_normal(n)
				st.add_vertex(p + side * half_w * (1.0 - 0.92 * t) * e)
		for i in SEG:
			var k := v + i * 2
			for q in [k, k + 1, k + 2, k + 1, k + 3, k + 2]:
				st.add_index(q)
		v += (SEG + 1) * 2
	return st.commit()


func _build_walls() -> void:
	var body := StaticBody3D.new()
	body.name = "Walls"
	add_child(body)
	for i in 4:
		var box := BoxShape3D.new()
		box.size = Vector3(WALL * 2.0 + 2.0, 40.0, 1.0)
		var cs := CollisionShape3D.new()
		cs.shape = box
		cs.rotation.y = i * PI * 0.5
		cs.position = Vector3(0, 0, WALL + 0.5).rotated(Vector3.UP, i * PI * 0.5)
		body.add_child(cs)

class_name FaceHead
extends Node3D
## A head of the face model that wears any face of its sex live: the root of assets/models/head_<sex>.glb
## (tools/faces/build_head.py), with a blend shape for each of a face's numbers but its brows and for each
## candidate feature the dev keeps, painted, haired and browed as the sheets show faces
## (shaders/face_head.gdshader); and the long hair's fall, which tools/faces/maker.py hangs from each face
## (hang). A face is a dictionary of its "numbers" and its candidates' "strengths", as the face maker saves
## it in assets/faces/.

var extras: Dictionary                          # the head's constants, as build_head.py gives them
var _head: MeshInstance3D
var _fall: MeshInstance3D


func _ready() -> void:
	_head = $head
	_fall = get_node_or_null("fall")
	extras = _head.get_meta("extras")
	var look := _look(preload("res://shaders/face_head.gdshader"))
	var brows: Dictionary = extras["brows"]
	var curve := PackedVector3Array()
	for c in brows["curve"]:
		curve.append(Vector3(c[0], c[1], c[2]))
	look.set_shader_parameter("brow_curve", curve)
	look.set_shader_parameter("brow_units", PackedFloat32Array(brows["units"]))
	for name in ["fade", "density", "rise"]:
		look.set_shader_parameter("brow_" + name, brows[name])
	look.set_shader_parameter("skin_roughness", extras["skin"]["roughness"])
	look.set_shader_parameter("eye_roughness", extras["eyes"]["roughness"])
	_head.material_override = look
	if _fall:
		_fall.material_override = _look(preload("res://shaders/face_fall.gdshader"))
	wear(rest())


## A material of `shader` in the head's hair.
func _look(shader: Shader) -> ShaderMaterial:
	var look := ShaderMaterial.new()
	look.shader = shader
	var hair: Dictionary = extras["hair"]
	var colour: Array = hair["colour"]
	look.set_shader_parameter("hair_colour", Vector3(colour[0], colour[1], colour[2]))
	look.set_shader_parameter("hair_roughness", hair["roughness"])
	look.set_shader_parameter("hair_sheen", hair["sheen"])
	look.set_shader_parameter("streaked", hair["streaked"])
	look.set_shader_parameter("strands", Vector2(hair["strands"][0], hair["strands"][1]))
	look.set_shader_parameter("clumps", Vector2(hair["clumps"][0], hair["clumps"][1]))
	return look


## The face the head was built at: the base face, each kept candidate at his favourite.
func rest() -> Dictionary:
	return extras["rest"].duplicate(true)


## Puts on a face, but for its fall, which stays the last hung until hang() hangs its own.
func wear(face: Dictionary) -> void:
	var numbers: Array = face["numbers"]
	var rest_numbers: Array = extras["rest"]["numbers"]
	var favourites: Dictionary = extras["rest"]["strengths"]
	var keys: Array = extras["candidates"]
	var shapes := _head.get_blend_shape_count() - keys.size()
	for k in shapes:
		_head.set_blend_shape_value(k, numbers[k] - rest_numbers[k])
	for j in keys.size():
		var key: String = keys[j]
		_head.set_blend_shape_value(shapes + j, face["strengths"].get(key, favourites[key]) - favourites[key])
	var brows := PackedFloat32Array(numbers.slice(shapes, shapes + extras["brows"]["units"].size()))
	_head.material_override.set_shader_parameter("brows", brows)


## Hangs the fall tools/faces/maker.py hangs from the face worn: its arrays as var_to_bytes writes them, in
## base64.
func hang(fall: Dictionary) -> void:
	if not _fall:
		return
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	var slots := {"points": Mesh.ARRAY_VERTEX, "normals": Mesh.ARRAY_NORMAL, "across": Mesh.ARRAY_TEX_UV,
			"indices": Mesh.ARRAY_INDEX}
	for name in slots:
		arrays[slots[name]] = bytes_to_var(Marshalls.base64_to_raw(fall[name]))
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	_fall.mesh = mesh

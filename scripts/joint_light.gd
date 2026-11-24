class_name JointLight
extends MeshInstance3D
## Faint streaks of white light across the air gaps between a figure's jointed parts, brighter and
## quicker while a joint turns. They are thin cards on the figure's skeleton, one end riding each
## part, so a bend pulls them across the gap it opens. shaders/joint_light.gdshader draws them. They
## light nothing.
##
## A joint is a bone that carries a rigid piece of the body, and its nearest ancestor that carries
## one. Its streaks bridge the two pieces where they come within REACH and both surfaces face away
## from the bone's pivot: the outside of the gap, where they show. A bone whose piece leaves no
## such gap gets no light.

const SHADER := preload("res://shaders/joint_light.gdshader")
const MAX_JOINTS := 64             ## the length of the shader's `joints`
const REACH := 0.03                ## metres; a wider gap than this gets no light
const TOUCHING := 0.002            ## pieces this close leave no gap
const SPACING := 0.008             ## one streak to about this length of gap
const SLANT := 0.005               ## how far a streak may land from the point straight across
const SAMPLING := 4                ## the body's vertices are read about one in this many
const FULL_SPEED := 7.0            ## radians a second at which a joint glows fully
const RISE := 0.05                 ## seconds for the glow to follow a joint speeding up
const FADE := 0.4                  ## and slowing down
const REST_RATE := 0.6             ## streak cycles a second at rest
const MOVING_RATE := 6.0           ## and glowing fully
const PHASE_WRAP := 4096.0

## The sampled surface of the body's piece on one bone, in the body's own space.
class Piece:
	var bind := -1
	var pivot := Vector3.ZERO
	var points := PackedVector3Array()
	var normals := PackedVector3Array()
	var bounds := AABB()


## The cards under construction.
class Cards:
	var points := PackedVector3Array()
	var normals := PackedVector3Array()
	var uv := PackedVector2Array()
	var uv2 := PackedVector2Array()
	var binds := PackedInt32Array()
	var weights := PackedFloat32Array()
	var indices := PackedInt32Array()

	func add(from: Vector3, from_bind: int, to: Vector3, to_bind: int, joint: int, number: float) -> void:
		var first := points.size()
		var run := from.direction_to(to)
		for corner in 4:
			var far := corner >= 2
			points.append(to if far else from)
			normals.append(run)
			uv.append(Vector2(1.0 if far else 0.0, corner % 2 * 2.0 - 1.0))
			uv2.append(Vector2(joint, number))
			binds.append_array([to_bind if far else from_bind, 0, 0, 0])
			weights.append_array([1.0, 0.0, 0.0, 0.0])
		indices.append_array([first, first + 1, first + 2, first + 2, first + 1, first + 3])

	func mesh() -> ArrayMesh:
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = points
		arrays[Mesh.ARRAY_NORMAL] = normals
		arrays[Mesh.ARRAY_TEX_UV] = uv
		arrays[Mesh.ARRAY_TEX_UV2] = uv2
		arrays[Mesh.ARRAY_BONES] = binds
		arrays[Mesh.ARRAY_WEIGHTS] = weights
		arrays[Mesh.ARRAY_INDEX] = indices
		var made := ArrayMesh.new()
		made.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		return made


var _skeleton: Skeleton3D
## For each lit joint, the bones from the child up to, but not including, the ancestor it turns on.
var _chains: Array[PackedInt32Array] = []
var _turns: Array[Quaternion] = []
## For each lit joint, its glow (0..1) and its count of streak cycles, as the shader reads them.
var _state := PackedVector2Array()


## Lights the joints of `bones` on `body`, a mesh skinned to `skeleton` whose every piece rides one bone.
## Make it once the skeleton is posed, and add it beside `body`: it is laid out in the body's space.
func _init(skeleton: Skeleton3D, body: MeshInstance3D, bones: PackedInt32Array) -> void:
	name = "JointLight"
	_skeleton = skeleton
	skin = body.skin
	layers = body.layers
	cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var material := ShaderMaterial.new()
	material.shader = SHADER
	material_override = material
	var pieces := _pieces(skeleton, body)
	var cards := Cards.new()
	var rng := RandomNumberGenerator.new()
	rng.seed = 1
	for bone in bones:
		var chain := PackedInt32Array([bone])
		var parent := skeleton.get_bone_parent(bone)
		while parent >= 0 and not pieces[parent]:
			chain.append(parent)
			parent = skeleton.get_bone_parent(parent)
		if not pieces[bone] or parent < 0 or _chains.size() == MAX_JOINTS:
			continue
		if _bridge(pieces[parent], pieces[bone], _chains.size(), cards, rng):
			_chains.append(chain)
	if _chains.is_empty():
		return
	mesh = cards.mesh()
	_state.resize(_chains.size())
	for chain in _chains:
		_turns.append(_turn(chain))


func _enter_tree() -> void:
	skeleton = get_path_to(_skeleton)


func _process(dt: float) -> void:
	if dt <= 0.0:
		return
	for joint in _chains.size():
		var turn := _turn(_chains[joint])
		var goal := minf(turn.angle_to(_turns[joint]) / (dt * FULL_SPEED), 1.0)
		_turns[joint] = turn
		var glow := _state[joint].x
		glow += (goal - glow) * (1.0 - exp(-dt / (RISE if goal > glow else FADE)))
		_state[joint] = Vector2(glow, fposmod(_state[joint].y + dt * lerpf(REST_RATE, MOVING_RATE, glow), PHASE_WRAP))
	(material_override as ShaderMaterial).set_shader_parameter("joints", _state)


## How the joint's bone is turned against the ancestor it turns on.
func _turn(chain: PackedInt32Array) -> Quaternion:
	var turn := Quaternion.IDENTITY
	for bone in chain:
		turn = _skeleton.get_bone_pose_rotation(bone) * turn
	return turn


## The body's pieces by bone, null for a bone that carries none. A vertex belongs to its first bone.
static func _pieces(skeleton: Skeleton3D, body: MeshInstance3D) -> Array[Piece]:
	var pieces: Array[Piece] = []
	pieces.resize(skeleton.get_bone_count())
	var by_bind: Array[Piece] = []
	for bind in body.skin.get_bind_count():
		var piece := Piece.new()
		piece.bind = bind
		piece.pivot = body.skin.get_bind_pose(bind).affine_inverse().origin
		by_bind.append(piece)
	var rng := RandomNumberGenerator.new()
	rng.seed = 1
	for surface in body.mesh.get_surface_count():
		var arrays := body.mesh.surface_get_arrays(surface)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var binds: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
		var binds_each := binds.size() / points.size()
		var i := rng.randi() % SAMPLING
		while i < points.size():
			var piece := by_bind[binds[i * binds_each]]
			var point := points[i]
			piece.bounds = piece.bounds.expand(point) if piece.points else AABB(point, Vector3.ZERO)
			piece.points.append(point)
			piece.normals.append(normals[i])
			i += 1 + rng.randi() % (2 * SAMPLING - 1)
	for piece in by_bind:
		if piece.points:
			var named := body.skin.get_bind_name(piece.bind)
			pieces[skeleton.find_bone(named) if named else body.skin.get_bind_bone(piece.bind)] = piece
	return pieces


## Adds the streaks between a bone's piece and its ancestor's; returns whether there were any.
static func _bridge(ancestor: Piece, piece: Piece, joint: int, cards: Cards, rng: RandomNumberGenerator) -> bool:
	var gap := ancestor.bounds.grow(REACH).intersection(piece.bounds.grow(REACH))
	if not gap.has_volume():
		return false
	var pivot := piece.pivot
	var across := AStar3D.new()
	for i in ancestor.points.size():
		var point := ancestor.points[i]
		if gap.has_point(point) and ancestor.normals[i].dot(pivot.direction_to(point)) > -0.2:
			across.add_point(i, point)
	if across.get_point_count() == 0:
		return false
	var taken := {}
	for i in piece.points.size():
		var from := piece.points[i]
		var facing := piece.normals[i]
		if not gap.has_point(from) or facing.dot(pivot.direction_to(from)) < -0.2:
			continue
		var landing := across.get_closest_point(from + Vector3(rng.randfn(), rng.randfn(), rng.randfn()) * SLANT)
		var to := ancestor.points[landing]
		var length := from.distance_to(to)
		if length < TOUCHING or length > REACH:
			continue
		var middle := (from + to) * 0.5
		var outward := pivot.direction_to(middle)
		var run := (to - from) / length
		var met := ancestor.normals[landing]
		# both ends on the outside of the joint, and the streak through air, not into either piece
		if facing.dot(outward) + met.dot(outward) < 0.6 or facing.dot(run) < -0.3 or met.dot(run) > 0.3:
			continue
		var cell := Vector3i((middle / SPACING).floor())
		if taken.has(cell):
			continue
		taken[cell] = true
		cards.add(from, piece.bind, to, ancestor.bind, joint, rng.randf())
	return not taken.is_empty()

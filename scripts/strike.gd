class_name Strike
extends RefCounted
## A blow on its way: the edges of a blade or of claws, followed frame by frame while the hit window is open.
## Each frame the slab every edge swept since the frame before is tested against the hurtboxes of the striker's
## foes, and each foe reached takes the blow once a swing.

var by: Health
var damage := 0.0
var shove := 0.0
var stop := 0.0
## Half the thickness of the slab an edge sweeps.
var thickness := 0.03

var _was := PackedVector3Array()
var _struck: Array[Health] = []
var _shape := ConvexPolygonShape3D.new()
var _query := PhysicsShapeQueryParameters3D.new()


func _init(striker: Health) -> void:
	by = striker
	_query.shape = _shape
	_query.collide_with_areas = true
	_query.collide_with_bodies = false
	_query.collision_mask = Layers.HURTBOXES


## A new swing: the edges start from wherever they are next, and every foe can be struck again.
func begin() -> void:
	_was.clear()
	_struck.clear()


## Follows the edges, pairs of points from base to tip, and lands the blow on each foe they reach for the first
## time this swing. Returns the hits that landed.
func sweep(edges: PackedVector3Array) -> Array[Hit]:
	var landed: Array[Hit] = []
	if _was.size() != edges.size():
		_was = edges
	var space := by.figure().get_world_3d().direct_space_state
	for i in range(0, edges.size(), 2):
		_shape.points = _swept(_was[i], _was[i + 1], edges[i], edges[i + 1])
		for found in space.intersect_shape(_query, 8):
			var box := found.collider as Hurtbox
			if box == null or _struck.has(box.health) or not by.foe(box.health):
				continue
			var hit := Hit.new()
			hit.by = by
			hit.damage = damage
			hit.shove = shove
			hit.stop = stop
			hit.at = box.surface_toward(edges[i], edges[i + 1])
			var way := (box.global_position - by.figure().global_position) * Vector3(1, 0, 1)
			if way.length_squared() < 1e-6:
				way = (edges[i + 1] - _was[i + 1]) * Vector3(1, 0, 1)
			hit.way = way.normalized()
			if box.health.take(hit):
				_struck.append(box.health)
				landed.append(hit)
	_was = edges
	return landed


## The corners of the slab an edge swept from a0-b0 to a1-b1, thickened every way across it.
func _swept(a0: Vector3, b0: Vector3, a1: Vector3, b1: Vector3) -> PackedVector3Array:
	var along := b1 - a1
	var across := along.cross(a1 - a0 + b1 - b0)
	if across.length_squared() < 1e-10:
		across = along.cross(Vector3.RIGHT if absf(along.normalized().y) > 0.9 else Vector3.UP)
	across = across.normalized() * thickness
	var ahead := across.cross(along).normalized() * thickness
	var corners := PackedVector3Array()
	for p in [a0, b0, a1, b1]:
		for side in [across + ahead, across - ahead, ahead - across, -across - ahead]:
			corners.append(p + side)
	return corners

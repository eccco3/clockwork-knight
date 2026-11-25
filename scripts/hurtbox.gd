class_name Hurtbox
extends Area3D
## Where blows can land on a figure: an upright capsule from its feet, on the Hurtboxes physics layer, the child
## of the figure whose Health takes them.

var health: Health
var radius := 0.0
var height := 0.0


func _init(of: Health, girth: float, tall: float) -> void:
	name = "Hurtbox"
	health = of
	radius = girth
	height = tall
	collision_layer = Layers.HURTBOXES
	collision_mask = 0
	monitoring = false
	var capsule := CapsuleShape3D.new()
	capsule.radius = radius
	capsule.height = height
	var shape := CollisionShape3D.new()
	shape.shape = capsule
	shape.position.y = height * 0.5
	add_child(shape)


## The point of the capsule's axis nearest the segment from `a` to `b`, moved out to its skin toward that segment.
func surface_toward(a: Vector3, b: Vector3) -> Vector3:
	var up := global_basis.y
	var points := Geometry3D.get_closest_points_between_segments(a, b,
		global_position + up * radius, global_position + up * (height - radius))
	return points[1] + (points[0] - points[1]).limit_length(radius)

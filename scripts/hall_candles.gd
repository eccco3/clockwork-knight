extends MultiMeshInstance3D
## Candle flames: one billboarded quad per wick, instanced. Points are baked in by hall_build.gd.

@export var points := PackedVector3Array()
@export var flame_mesh: Mesh


func _ready() -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.mesh = flame_mesh
	mm.instance_count = points.size()
	for i in points.size():
		mm.set_instance_transform(i, Transform3D(Basis.IDENTITY, points[i]))
	multimesh = mm

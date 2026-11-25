extends Node3D
## Crowd performance test: the outdoors without grinners of its own, and a crowd around the knight placed by
## spawn("<count>[,<arc degrees>[,<minions>]]"), with dev/drive.tscn the event call:spawn:24,90. They fill outward
## from NEAR metres, SPACE square metres each, within the arc centred on the way she faces (360 surrounds her),
## and waddle round her at their distances, half one way, half the other. The last <minions> of the count are
## minions, standing as built and facing her. Timed with perf:start and perf:stop:
##
##   python -I dev/quiet.py --timing --path . res://dev/drive.tscn --fixed-fps 60 --disable-vsync --max-fps 0
##       --resolution 1920x1080 -- scene=res://dev/crowd.tscn do="0:call:spawn:24;3:perf:start;13:perf:stop;13.1:quit"

const OUTDOORS := preload("res://scenes/outdoors.tscn")
const MINION := preload("res://assets/models/minion.glb")
const NEAR := 2.5
const SPACE := 12.0
const GOLDEN := PI * (3.0 - sqrt(5.0))

var _outdoors: Outdoors
var _centre := Vector3.ZERO
var _crowd: Array[Grinner] = []
var _radius := PackedFloat32Array()


func _ready() -> void:
	_outdoors = OUTDOORS.instantiate()
	_outdoors.grinners = false
	add_child(_outdoors)


func spawn(spec: String) -> void:
	var p := spec.split(",")
	var count := int(p[0])
	var arc := deg_to_rad(float(p[1])) if p.size() > 1 else TAU
	var minions := int(p[2]) if p.size() > 2 else 0
	var player: Player = get_tree().get_first_node_in_group("player")
	var heading := player.facing
	_centre = player.global_position
	for k in count:
		# a sector of the ring from NEAR to r has the area arc / 2 * (r² - NEAR²)
		var r := sqrt(NEAR * NEAR + k * SPACE / (arc / 2.0))
		var a := heading + (fposmod(k * GOLDEN, TAU) / TAU - 0.5) * arc
		var at := _ground(_centre + Vector3(sin(a), 0.0, cos(a)) * r)
		var unit: Node3D
		if k >= count - minions:
			unit = MINION.instantiate()
		else:
			var g := Grinner.new()
			g.gait = 1.0
			_crowd.append(g)
			_radius.append(r * (1.0 if k % 2 == 0 else -1.0))
			unit = g
		add_child(unit)
		unit.position = at
		unit.rotation.y = a + PI
	print("crowd: %d grinners and %d minions from %.1f to %.1f m" % [_crowd.size(), minions, NEAR,
			sqrt(NEAR * NEAR + (count - 1) * SPACE / (arc / 2.0))])


## Keeps each grinner on its circle, facing along it: clockwise for a negative radius.
func _process(_dt: float) -> void:
	for k in _crowd.size():
		var g := _crowd[k]
		var out := ((g.position - _centre) * Vector3(1, 0, 1)).normalized() * absf(_radius[k])
		var along := Vector3.UP.cross(out) * signf(_radius[k])
		g.position = _ground(_centre + out)
		g.rotation.y = atan2(along.x, along.z)


func _ground(at: Vector3) -> Vector3:
	return Vector3(at.x, _outdoors.height(at.x, at.z), at.z)

class_name Cadence
extends RefCounted
## How often a figure's animation advances: every frame while it is near the camera and in view, every second
## frame farther out, and every fourth far away or out of view. Each figure takes the next of four phases, so
## a crowd's updates spread evenly over the frames.

const NEAR := 12.0
const FAR := 22.0
## The sphere about a figure's origin, raised by HEIGHT, that must leave the view before it counts as unseen.
const HEIGHT := 0.8
const RADIUS := 1.2

static var _figures := 0

var _phase := 0
var _owed := 0.0


func _init() -> void:
	_phase = _figures % 4
	_figures += 1


## The time `figure` should advance this frame: all the frames' time owed since it last did, or 0 between.
func step(figure: Node3D, dt: float) -> float:
	_owed += dt
	if (Engine.get_process_frames() + _phase) % every(figure) != 0:
		return 0.0
	var owed := _owed
	_owed = 0.0
	return owed


## Every how many frames `figure` advances, seen from the current camera.
static func every(figure: Node3D) -> int:
	var camera := figure.get_viewport().get_camera_3d()
	if not camera:
		return 1
	var centre := figure.global_position + Vector3.UP * HEIGHT
	var distance := camera.global_position.distance_to(centre)
	if distance > FAR or camera.get_frustum().any(func(p: Plane) -> bool: return p.distance_to(centre) > RADIUS):
		return 4
	return 1 if distance < NEAR else 2

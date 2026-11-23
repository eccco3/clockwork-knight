class_name CameraRig
extends Node3D
## Third-person orbit camera. Mouse or right stick turns it about the character, the wheel
## zooms, and it pulls in smoothly when a wall or beam would come between it and her.

@export var target: Node3D
@export var pivot_height := 1.36
@export var close_pivot_height := 1.56  ## the pivot rises toward her face as the camera comes right in
@export var distance := 3.3
@export var min_distance := 0.55
@export var max_distance := 6.0
@export var mouse_sensitivity := 0.0024
@export var stick_speed := 2.6
@export var shoulder := 0.22            ## sideways offset so she is not dead centre

var yaw := PI
var pitch := -0.16

var camera: Camera3D
var _arm: SpringArm3D
var _cam_dist := 3.3
var _focus := Vector3.ZERO
var _has_focus := false


func _ready() -> void:
	top_level = true
	_arm = SpringArm3D.new()
	var shape := SphereShape3D.new()
	shape.radius = 0.16
	_arm.shape = shape
	_arm.collision_mask = 1
	_arm.margin = 0.02
	add_child(_arm)
	camera = Camera3D.new()
	camera.fov = 58.0
	camera.near = 0.05
	camera.far = 200.0
	add_child(camera)
	camera.make_current()
	_cam_dist = distance
	if target is CollisionObject3D:
		_arm.add_excluded_object(target.get_rid())


func _unhandled_input(e: InputEvent) -> void:
	if e is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		yaw -= e.relative.x * mouse_sensitivity
		pitch = clampf(pitch - e.relative.y * mouse_sensitivity, -1.25, 0.9)
	elif e is InputEventMouseButton and e.pressed:
		if e.button_index == MOUSE_BUTTON_WHEEL_UP:
			distance = maxf(min_distance, distance * 0.9)
		elif e.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			distance = minf(max_distance, distance / 0.9)


func _process(dt: float) -> void:
	if target == null:
		return
	var look := Input.get_vector("look_left", "look_right", "look_up", "look_down", 0.18)
	if look != Vector2.ZERO:
		yaw -= look.x * absf(look.x) * stick_speed * dt * 1.4
		pitch = clampf(pitch - look.y * absf(look.y) * stick_speed * dt, -1.25, 0.9)

	var close := 1.0 - smoothstep(0.9, 2.4, _cam_dist)
	var want := target.get_global_transform_interpolated().origin + Vector3.UP * lerpf(pivot_height, close_pivot_height, close)
	if not _has_focus:
		_focus = want
		_has_focus = true
	# tight horizontally, softer vertically so jumps and rolls do not jerk the frame
	var kh := 1.0 - exp(-dt * 16.0)
	var kv := 1.0 - exp(-dt * 7.0)
	_focus.x = lerpf(_focus.x, want.x, kh)
	_focus.z = lerpf(_focus.z, want.z, kh)
	_focus.y = lerpf(_focus.y, want.y, kv)

	var b := Basis(Vector3.UP, yaw) * Basis(Vector3.RIGHT, pitch)
	var pivot := _focus + b.x * shoulder * clampf((_cam_dist - 1.0) / 1.5, 0.0, 1.0)
	_arm.global_transform = Transform3D(b, pivot)
	_arm.spring_length = distance
	var hit := _arm.get_hit_length()
	if hit < _cam_dist:
		_cam_dist = lerpf(_cam_dist, hit, 1.0 - exp(-dt * 40.0))
	else:
		_cam_dist = lerpf(_cam_dist, hit, 1.0 - exp(-dt * 5.0))
	camera.global_transform = Transform3D(b, pivot + b.z * _cam_dist)


## Turns a 2D stick / key vector into a world direction on the ground, relative to the view.
func ground_direction(input: Vector2) -> Vector3:
	var b := Basis(Vector3.UP, yaw)
	return b.x * input.x + b.z * input.y

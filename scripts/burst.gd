class_name Burst
extends CPUParticles3D
## A spray thrown once where a blow lands, freed when the last of it has settled: dark ichor from a grinner's
## wound, and sparks and splinters off the knight's brass and wood. Each kind's look is made once and shared, and
## every bit shrinks away at the end of its life.

static var _looks := {}


## Dark drops drawn out along their flight, flung on along the blow and falling.
static func ichor(parent: Node, at: Vector3, way: Vector3, much := 1.0) -> void:
	var drop := SphereMesh.new()
	drop.radius = 0.009
	drop.height = 0.05
	drop.radial_segments = 6
	drop.rings = 4
	_throw(parent, at, way + Vector3.UP * 0.5, drop, _look(&"ichor", func() -> Material:
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.16, 0.015, 0.02)
		m.roughness = 0.12
		m.metallic_specular = 0.8
		return m), roundi(22 * much), 0.7, Vector2(1.2, 3.4), 30.0, Vector2(0.5, 1.6), true)


## Hot sparks off brass and steel, and pale splinters off the wood beneath.
static func splinters(parent: Node, at: Vector3, way: Vector3, much := 1.0) -> void:
	var streak := BoxMesh.new()
	streak.size = Vector3(0.004, 0.05, 0.004)
	_throw(parent, at, way + Vector3.UP * 0.3, streak, _look(&"spark", func() -> Material:
		var m := StandardMaterial3D.new()
		m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		m.albedo_color = Color(1.0, 0.62, 0.26)
		m.emission_enabled = true
		m.emission = Color(1.0, 0.55, 0.2)
		m.emission_energy_multiplier = 6.0
		return m), roundi(14 * much), 0.32, Vector2(2.5, 6.0), 50.0, Vector2(0.5, 1.4), true)
	var chip := BoxMesh.new()
	chip.size = Vector3(0.007, 0.03, 0.004)
	_throw(parent, at, way + Vector3.UP * 0.6, chip, _look(&"splinter", func() -> Material:
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(0.72, 0.5, 0.27)
		m.roughness = 0.8
		return m), roundi(8 * much), 0.9, Vector2(1.2, 2.8), 40.0, Vector2(0.6, 1.5), false)


static func _look(kind: StringName, make: Callable) -> Resource:
	if not _looks.has(kind):
		_looks[kind] = make.call()
	return _looks[kind]


## Throws `amount` of `mesh` at once from `at`, `spread` degrees about `way`, drawn out along their flight if
## `along` and tumbling if not. Emitting waits until it stands at `at`.
static func _throw(parent: Node, at: Vector3, way: Vector3, mesh: Mesh, look: Material, amount: int, lifetime: float,
		speed: Vector2, spread: float, size: Vector2, along: bool) -> void:
	var b := Burst.new()
	b.emitting = false
	b.mesh = mesh
	b.material_override = look
	b.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	b.amount = maxi(amount, 1)
	b.lifetime = lifetime
	b.one_shot = true
	b.explosiveness = 1.0
	b.local_coords = false
	b.direction = way.normalized()
	b.spread = spread
	b.initial_velocity_min = speed.x
	b.initial_velocity_max = speed.y
	b.gravity = Vector3(0, -9.8, 0)
	b.damping_min = 0.5
	b.damping_max = 1.5
	b.scale_amount_min = size.x
	b.scale_amount_max = size.y
	b.scale_amount_curve = _look(&"shrink", func() -> Curve:
		var c := Curve.new()
		c.add_point(Vector2(0.0, 1.0))
		c.add_point(Vector2(0.7, 0.85))
		c.add_point(Vector2(1.0, 0.0))
		return c)
	b.particle_flag_align_y = along
	b.particle_flag_rotate_y = not along
	if not along:
		b.angular_velocity_min = -720.0
		b.angular_velocity_max = 720.0
	b.finished.connect(b.queue_free)
	parent.add_child(b)
	b.global_position = at
	b.emitting = true

extends OmniLight3D
## Firelight flicker: layered noise on energy plus a small positional wander so shadows breathe.

@export var base_energy := 8.0
@export var flicker := 0.22
@export var speed := 8.0
@export var wander := 0.04

var _t := 0.0
var _origin := Vector3.ZERO
var _noise := FastNoiseLite.new()


func _ready() -> void:
	_origin = position
	_t = float(hash(get_path()) % 1000)
	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_noise.frequency = 0.35
	_noise.fractal_octaves = 3


func _process(delta: float) -> void:
	_t += delta * speed
	var n := _noise.get_noise_1d(_t)
	light_energy = base_energy * (1.0 + flicker * n * 2.0)
	if wander > 0.0:
		position = _origin + Vector3(_noise.get_noise_1d(_t * 0.6 + 100.0), _noise.get_noise_1d(_t * 0.6 + 200.0),
			_noise.get_noise_1d(_t * 0.6 + 300.0)) * wander * 2.0

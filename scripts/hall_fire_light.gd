extends OmniLight3D
## Firelight flicker: layered noise on energy. The light stays put, because its shadows magnify
## every movement.

@export var base_energy := 8.0
@export var flicker := 0.22
@export var speed := 8.0

var _t := 0.0
var _noise := FastNoiseLite.new()


func _ready() -> void:
	_t = float(hash(get_path()) % 1000)
	_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	_noise.frequency = 0.35
	_noise.fractal_octaves = 3


func _process(delta: float) -> void:
	_t += delta * speed
	light_energy = base_energy * (1.0 + flicker * _noise.get_noise_1d(_t) * 2.0)

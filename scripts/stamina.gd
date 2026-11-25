class_name Stamina
extends RefCounted
## The breath a fighter acts on. Each attack or dodge spends some; any left at all is enough to act, but never
## goes below none. It comes back REGAIN a second, starting DELAY seconds after the last spending, or WINDED
## seconds after one that emptied it.

const REGAIN := 45.0
const DELAY := 0.55
const WINDED := 1.1

var most := 100.0
var left := 100.0
var _rest := 0.0


func _init(full: float) -> void:
	most = full
	left = full


## Spends `cost` if any is left, and says whether it could.
func spend(cost: float) -> bool:
	if left <= 0.0:
		return false
	left = maxf(left - cost, 0.0)
	_rest = WINDED if left <= 0.0 else DELAY
	return true


func tick(dt: float) -> void:
	_rest -= dt
	if _rest <= 0.0:
		left = minf(left + REGAIN * dt, most)

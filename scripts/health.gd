class_name Health
extends Node
## How much harm a figure, the parent of its Health, can take before it dies, and the side it fights on. Fighters
## find one another through the group FIGHTERS, which every Health joins; a Hurtbox says where blows land on the
## figure and a Strike lands them. The figure reacts to `hurt` and `died`.

signal hurt(hit: Hit)
signal died(hit: Hit)

const FIGHTERS := &"fighters"

@export var most := 30.0
@export var side := &""
var left := 0.0
## While true, blows pass through without landing, as they do while the knight dodges.
var dodging := false


func _ready() -> void:
	left = most
	add_to_group(FIGHTERS)


func alive() -> bool:
	return left > 0.0


func figure() -> Node3D:
	return get_parent()


func foe(other: Health) -> bool:
	return other.side != side


## Takes the blow, unless it is dead already or dodging, and says whether it landed.
func take(hit: Hit) -> bool:
	if not alive() or dodging:
		return false
	left = maxf(left - hit.damage, 0.0)
	if alive():
		hurt.emit(hit)
	else:
		died.emit(hit)
	return true

class_name Gaze
extends SkeletonModifier3D
## Turns a figure's head and eyes toward `target`, a point in the world, on top of whatever its animation
## does with them. The head takes `head_share` of the turn, within `head_reach`, and catches up with it
## slowly; the eyes take what is left at once, within `eye_reach`. Turns are measured from the way the
## chest faces, aside to the figure's left and up, in radians. The figure faces +Z at rest, as glTF has it.
## Fade the whole of it in and out by `influence`.

@export var target := Vector3.ZERO
@export var head_share := 0.7
@export var head_reach := Vector2(deg_to_rad(50.0), deg_to_rad(20.0))
@export var eye_reach := Vector2(deg_to_rad(25.0), deg_to_rad(15.0))
@export var neck_share := 0.4  ## of the head's turn, what the neck takes
@export var catch_up := 4.0  ## per second
@export var chest := &"chest"
@export var neck := &"neck"
@export var head := &"head"
@export var eyes: Array[StringName] = [&"eye_l", &"eye_r"]

var _turned := Vector2.ZERO  ## the head's turn now


func _process_modification_with_delta(delta: float) -> void:
	var skeleton := get_skeleton()
	var eye_bones := eyes.map(func(eye: StringName) -> int: return skeleton.find_bone(eye))
	var between := Vector3.ZERO
	for eye: int in eye_bones:
		between += skeleton.get_bone_global_pose(eye).origin / eye_bones.size()
	var body := _turn_from_rest(skeleton, skeleton.find_bone(chest))
	var to := body.inverse() * (skeleton.global_transform.affine_inverse() * target - between)
	var wanted := Vector2(atan2(to.x, to.z), atan2(to.y, Vector2(to.x, to.z).length()))
	_turned = _turned.lerp((wanted * head_share).clamp(-head_reach, head_reach), 1.0 - exp(-catch_up * delta))
	_turn(skeleton, skeleton.find_bone(neck), body, _turned * neck_share)
	_turn(skeleton, skeleton.find_bone(head), body, _turned * (1.0 - neck_share))
	var face := _turn_from_rest(skeleton, skeleton.find_bone(head))
	for eye: int in eye_bones:
		_turn(skeleton, eye, face, (wanted - _turned).clamp(-eye_reach, eye_reach))


## How a bone has turned from its rest, in the skeleton's space.
func _turn_from_rest(skeleton: Skeleton3D, bone: int) -> Basis:
	return skeleton.get_bone_global_pose(bone).basis * skeleton.get_bone_global_rest(bone).basis.inverse()


## Turns a bone about its head, aside and up as `frame`'s axes have it.
func _turn(skeleton: Skeleton3D, bone: int, frame: Basis, by: Vector2) -> void:
	var turn := Basis((frame * Vector3.UP).normalized(), by.x) * Basis((frame * Vector3.RIGHT).normalized(), -by.y)
	var parent := skeleton.get_bone_global_pose(skeleton.get_bone_parent(bone)).basis
	var pose := Basis(skeleton.get_bone_pose_rotation(bone))
	skeleton.set_bone_pose_rotation(bone, (parent.inverse() * turn * parent * pose).get_rotation_quaternion())

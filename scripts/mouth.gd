class_name Mouth
extends SkeletonModifier3D
## A wooden figure's mouth, moving with her voice one of four ways, as `style` says. STILL keeps it shut. JAW
## turns the `jaw` bone a few degrees, parting her carved lips. SWAPPED shows one set of lacquered lip pieces at a
## time, carved in one shape each, as a stop-motion puppet's replacement mouths are swapped. PIVOTED moves one set
## of pieces into each shape on their pivots. JAW keeps her face as carved; the others wear the face cut for lip
## pieces, `inlaid`.
##
## `speak` times the mouth to a voice as it plays, by the visemes the voice tool wrote beside it (tools/voice.ps1).
## Each of the 22 makes one of the figure's `shapes`, which give each its jaw's opening in degrees, as "jaw", and
## where each pivot's piece stands in it.

enum Style { STILL, JAW, SWAPPED, PIVOTED }

const VISEMES: Array[String] = [  ## SAPI's visemes, each as the shape it makes
	"rest", "ah", "ah", "oh", "ee", "oh", "ee", "oo", "oh", "ah", "oh",  # silence; vowels
	"ah", "ee", "oo", "ee", "ee", "oo", "ee", "rest", "ee", "ee", "rest"]  # ai; h, r, l, s, sh, th, f, t, k, p
const LEAD := 0.06  ## seconds the mouth shapes a sound before it is heard
const HOLD := 1.0 / 12.0  ## the least while a swapped mouth stays, as a puppet animated on twos
const EASE := 22.0  ## how fast the jaw and pivots close on the shape, per second

@export var style := Style.STILL:
	set(value):
		style = value
		_dress()
@export var jaw := &"jaw"

var shapes: Dictionary  ## shape -> {"jaw": degrees, piece: its Transform3D in the shape}
var face: Node3D  ## her face with carved lips
var inlaid: Node3D  ## her face cut for lip pieces
var carved: Dictionary  ## shape -> the lip pieces carved in it
var pivots: Dictionary  ## piece -> the piece on its pivot

var _voice: AudioStreamPlayer3D
var _visemes: Array
var _heard := 0.0  ## seconds the voice has played, as the game's clock has it
var _shown := "rest"
var _held := 0.0
var _open := 0.0


## Shape the mouth to `voice`, which has just begun to play, at the visemes [[seconds, viseme], ...].
func speak(voice: AudioStreamPlayer3D, visemes: Array) -> void:
	_voice = voice
	_visemes = visemes
	_heard = 0.0


## The shape the voice makes `ahead` seconds from now: by the game's clock since it began, or by where it is
## playing if that has run ahead.
func shape_at(ahead: float) -> String:
	if not (_voice and _voice.playing) or _visemes.is_empty():
		return "rest"
	var at := maxf(_voice.get_playback_position(), _heard) + ahead
	var shape := "rest"
	for mark: Array in _visemes:
		if mark[0] > at:
			break
		shape = VISEMES[int(mark[1])]
	return shape


func _process_modification_with_delta(delta: float) -> void:
	if _voice and _voice.playing:
		_heard += delta
	var shape := shape_at(LEAD)
	var closing := 1.0 - exp(-EASE * delta)
	_open = lerpf(_open, shapes[shape]["jaw"] if style == Style.JAW else 0.0, closing)
	_turn_jaw(_open)
	match style:
		Style.SWAPPED:
			_held += delta
			if shape != _shown and _held >= HOLD:
				carved[_shown].visible = false
				_shown = shape
				carved[_shown].visible = true
				_held = 0.0
		Style.PIVOTED:
			for piece: String in pivots:
				var at: Node3D = pivots[piece]
				at.transform = at.transform.interpolate_with(shapes[shape][piece], closing)


## Opens the jaw `degrees` from rest, turning it about the figure's x as it stands at rest.
func _turn_jaw(degrees: float) -> void:
	var skeleton := get_skeleton()
	var bone := skeleton.find_bone(jaw)
	var axis := (skeleton.get_bone_global_rest(bone).basis.inverse() * Vector3.RIGHT).normalized()
	var rest := skeleton.get_bone_rest(bone).basis.get_rotation_quaternion()
	skeleton.set_bone_pose_rotation(bone, rest * Quaternion(axis, deg_to_rad(degrees)))


## Shows the face and pieces the style wears, at rest.
func _dress() -> void:
	if not face:
		return
	var pieces := style == Style.SWAPPED or style == Style.PIVOTED
	face.visible = not pieces
	inlaid.visible = pieces
	_shown = "rest"
	_open = 0.0
	for shape: String in carved:
		carved[shape].visible = style == Style.SWAPPED and shape == _shown
	for piece: String in pivots:
		pivots[piece].visible = style == Style.PIVOTED
		pivots[piece].transform = shapes["rest"][piece]

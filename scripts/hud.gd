class_name Hud
extends CanvasLayer
## The knight's health and stamina: two bars at the top left, each as long as the most she can have, so they
## lengthen as she grows. What a blow takes shows pale for a moment before the health bar catches up. While both
## are full and nothing has changed for a few seconds, the bars fade away.

const AT := Vector2(44, 38)
const PER_POINT := 3.0
const HEALTH_HIGH := 9.0
const STAMINA_HIGH := 5.0
const GAP := 7.0
const LINGER := 3.0
const LOSS_WAIT := 0.55
const LOSS_RATE := 60.0
const HEALTH_FILL := Color(0.6, 0.075, 0.06)
const HEALTH_LOSS := Color(0.93, 0.8, 0.62)
const STAMINA_FILL := Color(0.4, 0.58, 0.32)
const BACK := Color(0.02, 0.015, 0.01, 0.55)
const RIM := Color(0.78, 0.62, 0.32, 0.85)

var _health: Health
var _stamina: Stamina
var _box := Control.new()
var _health_fill: ColorRect
var _health_loss: ColorRect
var _stamina_fill: ColorRect
var _loss := 0.0
var _loss_wait := 0.0
var _quiet := 0.0
var _seen := Vector2.ZERO


func _init(health: Health, stamina: Stamina) -> void:
	name = "Hud"
	layer = 10
	_health = health
	_stamina = stamina


func _ready() -> void:
	_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_box.modulate.a = 0.0
	add_child(_box)
	var health := _bar(0.0, HEALTH_HIGH, _health.most, [HEALTH_LOSS, HEALTH_FILL])
	_health_loss = health[0]
	_health_fill = health[1]
	_stamina_fill = _bar(HEALTH_HIGH + GAP, STAMINA_HIGH, _stamina.most, [STAMINA_FILL])[0]
	_loss = _health.left
	_seen = Vector2(_health.left, _stamina.left)


func _bar(top: float, high: float, most: float, colours: Array[Color]) -> Array[ColorRect]:
	var style := StyleBoxFlat.new()
	style.bg_color = BACK
	style.border_color = RIM
	style.set_border_width_all(1)
	var frame := Panel.new()
	frame.add_theme_stylebox_override("panel", style)
	frame.position = AT + Vector2(-2.0, top - 2.0)
	frame.size = Vector2(most * PER_POINT + 4.0, high + 4.0)
	frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_box.add_child(frame)
	var fills: Array[ColorRect] = []
	for colour in colours:
		var fill := ColorRect.new()
		fill.color = colour
		fill.position = AT + Vector2(0.0, top)
		fill.size = Vector2(most * PER_POINT, high)
		fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_box.add_child(fill)
		fills.append(fill)
	return fills


func _process(dt: float) -> void:
	var now := Vector2(_health.left, _stamina.left)
	if now != _seen:
		if now.x < _seen.x:
			_loss_wait = LOSS_WAIT
		_seen = now
		_quiet = 0.0
	_quiet += dt
	_loss_wait -= dt
	if _loss_wait <= 0.0:
		_loss = move_toward(_loss, _health.left, LOSS_RATE * dt)
	_loss = maxf(_loss, _health.left)
	_health_fill.size.x = _health.left * PER_POINT
	_health_loss.size.x = _loss * PER_POINT
	_stamina_fill.size.x = _stamina.left * PER_POINT
	var rested := _health.left >= _health.most and _stamina.left >= _stamina.most and _quiet > LINGER
	_box.modulate.a = move_toward(_box.modulate.a, 0.0 if rested else 1.0, dt * (1.2 if rested else 5.0))

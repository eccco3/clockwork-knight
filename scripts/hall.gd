class_name Hall
extends Node3D
## The great hall. Its lamps exist for the lightmap baker and are removed at runtime, where two
## kinds of live light stand in for them:
## - each chandelier becomes a pair of equal lights, one negative, that cancel everywhere except
##   in a character's shadow, so characters still cast shadows on the baked floor;
## - with `character_lights`, the chandeliers, sconces and windows also light characters directly,
##   so lacquer and brass keep their highlights. Without it, characters get only bounced light.
## Every shadowed light costs GPU time, so a chandelier casts shadows only while it is the nearest
## to some member of the `characters` group. A chandelier up to `SHADOW_HANDOVER` metres further
## away than the nearest keeps a fading shadow, so walking between two hands the shadow over.

const LIGHTMAP := "res://assets/lightmaps/hall.lmbake"
const CHARACTER_LIGHTS := &"character_lights"
const SHADOW_LIGHTS := &"shadow_lights"
const SHADOW_HANDOVER := 2.0

static var character_lights := true

var _shadow_lights: Array[Light3D] = []


func _ready() -> void:
	if ResourceLoader.exists(LIGHTMAP):
		($LightmapGI as LightmapGI).light_data = load(LIGHTMAP)
	else:
		push_warning("No lightmap: run tools/build_models.ps1")
	for l: Light3D in find_children("*", "Light3D", true, false):
		if l.light_bake_mode != Light3D.BAKE_STATIC:
			continue
		var characters := Layers.CHARACTERS if character_lights and l.is_in_group(CHARACTER_LIGHTS) else 0
		if l.is_in_group(SHADOW_LIGHTS):
			var minus := l.duplicate() as Light3D
			minus.light_negative = true
			minus.shadow_enabled = false
			minus.light_volumetric_fog_energy = 0.0
			l.add_sibling(minus)
			_keep_live(minus, Layers.SCENERY)
			_keep_live(l, Layers.SCENERY | characters)
			_shadow_lights.append(l)
		elif characters:
			_keep_live(l, characters)
		else:
			l.queue_free()


func _keep_live(l: Light3D, lit_layers: int) -> void:
	l.light_bake_mode = Light3D.BAKE_DISABLED
	l.light_cull_mask = lit_layers
	l.shadow_caster_mask = Layers.CHARACTERS
	l.light_size = 0.0


func _process(_dt: float) -> void:
	var opacity := PackedFloat32Array()
	opacity.resize(_shadow_lights.size())
	var distance := PackedFloat32Array()
	distance.resize(_shadow_lights.size())
	for c: Node3D in get_tree().get_nodes_in_group(Layers.CHARACTER_GROUP):
		var nearest := INF
		for i in _shadow_lights.size():
			distance[i] = c.global_position.distance_to(_shadow_lights[i].global_position)
			nearest = minf(nearest, distance[i])
		for i in _shadow_lights.size():
			opacity[i] = maxf(opacity[i], 1.0 - smoothstep(0.0, SHADOW_HANDOVER, distance[i] - nearest))
	for i in _shadow_lights.size():
		var l := _shadow_lights[i]
		var casts := opacity[i] > 0.0
		if l.shadow_enabled != casts:
			l.shadow_enabled = casts
		if l.shadow_opacity != opacity[i]:
			l.shadow_opacity = opacity[i]

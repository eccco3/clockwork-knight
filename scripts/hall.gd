class_name Hall
extends Node3D
## The great hall. Its lamps exist for the lightmap baker and are removed at runtime, where two
## kinds of live light stand in for them:
## - each chandelier becomes a pair of equal lights, one negative, that cancel everywhere except
##   in a character's shadow, so characters still cast shadows on the baked floor;
## - with `character_lights`, the chandeliers, sconces and windows also light characters directly,
##   so lacquer and brass keep their highlights. Without it, characters get only bounced light.

const LIGHTMAP := "res://assets/lightmaps/hall.lmbake"
const CHARACTER_LIGHTS := &"character_lights"
const SHADOW_LIGHTS := &"shadow_lights"
const SCENERY_LAYER := 1
const CHARACTER_LAYER := 2

static var character_lights := true


func _ready() -> void:
	if ResourceLoader.exists(LIGHTMAP):
		($LightmapGI as LightmapGI).light_data = load(LIGHTMAP)
	else:
		push_warning("No lightmap: run tools/build_models.ps1")
	for l: Light3D in find_children("*", "Light3D", true, false):
		if l.light_bake_mode != Light3D.BAKE_STATIC:
			continue
		var characters := CHARACTER_LAYER if character_lights and l.is_in_group(CHARACTER_LIGHTS) else 0
		if l.is_in_group(SHADOW_LIGHTS):
			var minus := l.duplicate() as Light3D
			minus.light_negative = true
			minus.shadow_enabled = false
			minus.light_volumetric_fog_energy = 0.0
			l.add_sibling(minus)
			_keep_live(minus, SCENERY_LAYER)
			_keep_live(l, SCENERY_LAYER | characters)
		elif characters:
			_keep_live(l, characters)
		else:
			l.queue_free()


func _keep_live(l: Light3D, lit_layers: int) -> void:
	l.light_bake_mode = Light3D.BAKE_DISABLED
	l.light_cull_mask = lit_layers
	l.shadow_caster_mask = CHARACTER_LAYER
	l.light_size = 0.0

extends Node3D
## The playable scene: the hall, the knight at its spawn marker, and Rosalyn, whom the scene stands by the
## hall's first window on the fire's side, with the subtitles of what she says.

const HALL := preload("res://scenes/hall.tscn")

var player: Player


func _ready() -> void:
	var hall := HALL.instantiate()
	add_child(hall)
	player = Player.new()
	player.name = "Player"
	var spawn := hall.get_node_or_null("PlayerSpawn") as Node3D
	var at := spawn.position if spawn else Vector3.ZERO
	player.position = at
	# face down the hall
	player.rotation.y = atan2(-at.x, -at.z) if Vector2(at.x, at.z).length() > 0.5 else 0.0
	add_child(player)

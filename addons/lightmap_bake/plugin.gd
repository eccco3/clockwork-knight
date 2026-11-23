@tool
extends EditorPlugin
## Godot only bakes lightmaps from the editor's "Bake Lightmaps" button, so this presses it.
##
##   godot --editor --path . res://scenes/hall.tscn -- bake-lightmaps [draft]
##
## "draft" bakes at low quality, several times faster, for judging brightness and colour.
## The data goes to res://assets/lightmaps/<scene name>.lmbake. Needs a window: the baker runs on
## the GPU. Exits 0 on success and 1 on failure.

const FLAG := "bake-lightmaps"
const DRAFT := "draft"
const OUT := "res://assets/lightmaps/%s.lmbake"
const BUTTON := "Bake Lightmaps"
const TIMEOUT_S := 300.0
const QUIET_MS := 3000


func _enter_tree() -> void:
	if FLAG in OS.get_cmdline_user_args():
		_run.call_deferred()


func _run() -> void:
	var scene := await _settled_scene()
	if scene == null:
		return _fail("no scene was opened")
	var found := scene.find_children("*", "LightmapGI", true, false)
	if found.is_empty():
		return _fail("%s has no LightmapGI" % scene.scene_file_path)
	var lightmap: LightmapGI = found[0]
	var path := OUT % scene.scene_file_path.get_file().get_basename()
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var data := LightmapGIData.new()
	ResourceSaver.save(data, path)
	data.take_over_path(path)
	lightmap.light_data = data
	if DRAFT in OS.get_cmdline_user_args():
		lightmap.quality = LightmapGI.BAKE_QUALITY_LOW
	EditorInterface.get_resource_filesystem().scan()
	await _settled_scene()

	EditorInterface.get_selection().clear()
	EditorInterface.get_selection().add_node(lightmap)
	EditorInterface.edit_node(lightmap)
	var button := await _bake_button()
	if button == null:
		return _fail("the editor has no \"%s\" button" % BUTTON)
	var started := Time.get_ticks_msec()
	print("lightmap: baking ", scene.scene_file_path)
	button.pressed.emit()

	var baked := lightmap.light_data
	if baked == null or baked.get_user_count() == 0:
		return _fail("the bake wrote nothing")
	print("lightmap: %s  %d meshes  %d s" % [path, baked.get_user_count(), (Time.get_ticks_msec() - started) / 1000])
	get_tree().quit(0)


## Waits until the editor has stopped scanning and importing for a while. Opening a scene makes the
## editor reimport textures it first sees in 3D, and a bake can only import its result into a
## folder the editor has already scanned, and only while nothing else is importing.
func _settled_scene() -> Node:
	var files := EditorInterface.get_resource_filesystem()
	var deadline := Time.get_ticks_msec() + TIMEOUT_S * 1000.0
	var quiet_since := Time.get_ticks_msec()
	while Time.get_ticks_msec() < deadline:
		await get_tree().process_frame
		var now := Time.get_ticks_msec()
		if files.is_scanning() or files.is_importing() or EditorInterface.get_edited_scene_root() == null:
			quiet_since = now
		elif now - quiet_since > QUIET_MS:
			return EditorInterface.get_edited_scene_root()
	return null


func _bake_button() -> Button:
	for attempt in 120:
		await get_tree().process_frame
		for b: Button in EditorInterface.get_base_control().find_children("*", "Button", true, false):
			if b.text == BUTTON and b.is_visible_in_tree():
				return b
	return null


func _fail(why: String) -> void:
	push_error("lightmap: " + why)
	get_tree().quit(1)

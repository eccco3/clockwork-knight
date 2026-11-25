The dev's rules, which bind every session, are in @DEV.md.

## Game

A roguelite: the workshop and hall are the safe hub; enemies appear only outdoors, in MOBA-lane runs of about 12 grinners on screen, 40 units in all.

## Tools

`.gdignore` hides third-party `toolchain/` from Godot.

- Godot 4.7.2: `toolchain\godot\Godot_v4.7.2-stable_win64_console.exe`
- Blender 4.5.16: `toolchain\blender\blender.exe`
- Both are Windows-native: use PowerShell.
- System `python` is a hanging Store stub: use `toolchain\blender\4.5\python\bin\python.exe -I`.

## Build and run

- All models, the Godot import and the lightmap: `tools\build_models.ps1`. Needed after cloning.
- Lightmap alone: `godot --editor --path . res://scenes/hall.tscn -- bake-lightmaps` takes fourteen minutes; `draft` two. Rebake after rebuilding.
- Materials, then scene: `godot --headless --path . --script res://builders/hall_materials.gd`, then `hall_scene.gd`.
- Knight: `blender --background --python tools/knight/build_knight.py -- --out assets/models/knight.glb` (80 s), then `godot --path . --headless --import`. `--seat culet|armour` replaces her tabard.
- Grinner: `blender --background --python tools/grinner/build_grinner.py -- --out assets/models/grinner.glb` (seven minutes), then import; `--kind scuttler` for `scuttler.glb`. `--shots dir` adds turnarounds; `--clay a.png` alone previews the bare mesh.
- Rosalyn and minion: likewise (seven minutes; ten seconds), dressed by their models' roots `scripts/rosalyn.gd` and `minion.gd`; `--detail 0.7` halves Rosalyn's triangles.
- Never combine `--only` with `--out`: it overwrites the full model.
- Run: `godot --path .`. Playtest picker to pin: `tools\playtest\install.ps1` in the main checkout; `playtest.ps1 -DryRun` tests it.
- Scripted play: `dev/drive.tscn` with `--fixed-fps 60`; `dev/shot.tscn` photographs a scene. Their headers list arguments.
- Never open Godot windows on the dev's screen for tests or bakes, unless he is playtesting: replace `godot` with `toolchain\blender\4.5\python\bin\python.exe -I dev\quiet.py`; `--timing` first for GPU timing waits until nothing else runs.
- Clips: `tools\clip.py out.mp4 <drive arguments>` (that Python) records `dev/drive.tscn` hidden.
- Capped at 60 fps. Frame times: `dev/drive.tscn` events `perf:start`, `perf:stop` with `--disable-vsync --max-fps 0`; crowds: `dev/crowd.tscn`.

## Where things are

- The playtest picker shows `metadata/playable` scenes and the dev's `metadata/dev_tool` tools. `scenes/main.tscn` is the hall.
- `project.godot` holds the input map and names the layers; `scripts/layers.gd` gives code the same names.
- The `App` autoload, `scripts/app.gd`, holds the keys Esc, F11 and H, cursor capture and the controls hint for playable scenes.
- `scenes/outdoors.tscn` builds the grinner's foggy ground on load.
- `dev/` tests the game; `builders/` builds in Godot; `tools/`, hidden from Godot, builds and fetches assets.
- `scripts/` holds the player controller, animator and camera rig; `looks.gd` makes each figure's wood, metal and eye materials.
- Lamps are baked. `scripts/hall.gd` turns those marked `lights_characters` into lights for the Characters layer only, and `shadows_characters` into cancelling pairs leaving character shadows on the baked floor. Only the fire is live.
- `addons/lightmap_bake` presses the editor's bake button.
- `tools/sculpt/` is the characters' shared toolkit.
- `tools/knight/` builds the knight, `assets/textures/knight/face_paint.png` and its placement `face_paint.json`; `tools/build_hall.py` and `builders/hall_*.gd` build the hall; `tools/workshop_shell.py`'s constants size the workshop beyond its east doors.
- Only stand-ins such as `KnightShadow` (`tools/knight/shadow.py`) cast figures' shadows.
- `tools/faces/`: ICT-FaceKit model, MakeHuman features, sex labels (`dev/labels.tscn`), taste (`dev/taste_*.tscn`, `--refine` rounds); see `taste.py`.
- `tools/grinner/` builds the grinner and four-legged scuttler, rigged and hand-keyed; `import_grinner.gd` adds its AnimationTree; `scripts/grinner.gd` moves both. `dev/stage.tscn` stands models (see its header), and `dev/waddler.tscn` or `scuttler.tscn` moving.
- `tools/minion/` builds the unrigged minion; `tools/sculpt/levels.gd` chains detail levels, proven by `dev/detail_check.gd -- <model>`.

## Repository

- `tools/check_docs.sh` enforces the four documentation rules in `DEV.md`; `tools/hooks/pre-commit` runs it. After cloning: `git config core.hooksPath tools/hooks`.
- First-party means everything git tracks except `tools/downloads/`.
- Git ignores `toolchain/`, `.godot/`, `dev/shots/` and what `tools/fetch_assets.ps1` and `build_models.ps1` restore.
- Commit with Windows git, not WSL.

## Downloads

CC0: Quaternius Universal Animation Library 1 and 2 (hand-keyed, not mocap); Poly Haven scans and sky; MakeHuman face targets. MIT: ICT-FaceKit heads.

The dev's rules, which bind every session, are in @DEV.md.

## Game

A roguelite: the workshop and hall are the safe hub; enemies appear only outdoors, in MOBA-lane runs of about 12 grinners on screen, 40 units in all.

## Tools

Everything the project needs is here; `.gdignore` hides third-party `toolchain/` from Godot.

- Godot 4.7.2: `toolchain\godot\Godot_v4.7.2-stable_win64_console.exe`
- Blender 4.5.16: `toolchain\blender\blender.exe`
- Both are Windows-native: use PowerShell, not WSL.
- System `python` is a hanging Store stub. Use `toolchain\blender\4.5\python\bin\python.exe -I`.

## Build and run

- All models, the Godot import and the hall's lightmap: `tools\build_models.ps1`. Needed after cloning.
- Lightmap alone: `godot --editor --path . res://scenes/hall.tscn -- bake-lightmaps` takes six minutes; `draft` previews in one. Rebake after changing the hall.
- Hall materials, then scene: `godot --headless --path . --script res://builders/hall_materials.gd`, then `hall_scene.gd`.
- Knight: `blender --background --python tools/knight/build_knight.py -- --out assets/models/knight.glb` (80 s), then `godot --path . --headless --import`.
- Grinner: `blender --background --python tools/grinner/build_grinner.py -- --out assets/models/grinner.glb` (seven minutes), then import. `--shots dir` adds turnarounds; `--clay a.png` alone previews the bare mesh.
- Rosalyn: likewise (`rosalyn`, seven minutes); `--detail 0.7` halves her triangles. Her model's root, `scripts/rosalyn.gd`, dresses her.
- Never combine `--only` with `--out`: it overwrites the full model.
- Run: `godot --path .`. Playtest picker to pin: `tools\playtest\install.ps1` in the main checkout; `playtest.ps1 -DryRun` tests it.
- Scripted play and screenshots: `dev/drive.tscn` with `--fixed-fps 60`; `dev/shot.tscn` photographs a scene. Both list their arguments in their headers; `lamps=baked` drops the live character lights.
- Never open Godot windows on the dev's screen for tests or bakes, unless he is playtesting: replace `godot` with `toolchain\blender\4.5\python\bin\python.exe -I dev\quiet.py`, which runs it on a hidden desktop; `--timing` first for GPU timing waits until nothing else runs.
- The game caps at 60 fps. Frame times: `dev/drive.tscn` events `perf:start` and `perf:stop`, run with `--disable-vsync --max-fps 0`.

## Where things are

- The playtest picker shows `metadata/playable` scenes and the dev's `metadata/dev_tool` tools. `scenes/main.tscn` is the hall.
- `project.godot` holds the input map and names the layers; `scripts/layers.gd` gives code the same names.
- The `App` autoload, `scripts/app.gd`, holds the keys Esc, F11 and H, cursor capture and the controls hint for playable scenes.
- `scenes/outdoors.tscn` builds the grinner's foggy ground on load.
- `dev/` tests the game; `builders/` builds in Godot; `tools/`, hidden from Godot, builds and fetches assets.
- `scripts/` holds the player controller, animator and camera rig; `looks.gd` makes the wood, metal and eye materials in each figure's colours.
- The hall's lamps are baked. `scripts/hall.gd` turns lamps marked `lights_characters` into lights for the Characters layer only, and `shadows_characters` into cancelling pairs leaving character shadows on the baked floor. Only the fire lights the hall live.
- `addons/lightmap_bake` presses the editor's bake button.
- `tools/sculpt/` is the characters' shared toolkit.
- `tools/knight/` builds the knight, `assets/textures/knight/face_paint.png` and its placement `face_paint.json`; `tools/build_hall.py` and `builders/hall_*.gd` build the hall.
- Only `KnightShadow`, a 4,700-triangle copy from `tools/knight/shadow.py`, casts the knight's shadows.
- `tools/faces/`: the ICT-FaceKit face model, the dev's taste per sex (`dev/taste_*.tscn`); see `build_faces.py`.
- `tools/grinner/` builds the first enemy, its rig and hand-keyed clips; `import_grinner.gd` sets its detail distances and adds the AnimationTree. `scripts/grinner.gd` walks it. Shot shows it on `dev/stage.tscn`: `call=stand:res://assets/models/grinner.glb`, `stand:res://dev/waddler.tscn` waddling, or `spread:` its detail levels.

## Repository

- `tools/check_docs.sh` enforces the four documentation rules in `DEV.md`; `tools/hooks/pre-commit` runs it. After cloning: `git config core.hooksPath tools/hooks`.
- First-party means everything git tracks except `tools/downloads/`.
- Git ignores `toolchain/`, `.godot/`, `dev/shots/`, fetched files (`tools/fetch_assets.ps1`) and built models and lightmap (`tools/build_models.ps1`).
- Commit with Windows git, not WSL.

## Downloads

CC0: Quaternius Universal Animation Library 1 and 2 (hand-keyed, not mocap); Poly Haven scans and sky. MIT: ICT-FaceKit heads.

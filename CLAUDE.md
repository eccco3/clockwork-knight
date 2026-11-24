The dev's rules, which bind every session, are in @DEV.md.

<Claude's notes>

## Tools

Everything the project needs is in this folder. `toolchain/` is third-party and hidden from Godot by `.gdignore`.

- Godot 4.7.2: `toolchain\godot\Godot_v4.7.2-stable_win64_console.exe`
- Blender 4.5.16: `toolchain\blender\blender.exe`
- Both are Windows-native: use PowerShell, not WSL.
- System `python` is a hanging Store stub. Use `toolchain\blender\4.5\python\bin\python.exe -I`.

## Build and run

- Both models, the Godot import and the hall's lightmap: `tools\build_models.ps1`. Needed after cloning.
- Lightmap alone: `godot --editor --path . res://scenes/hall.tscn -- bake-lightmaps` runs the editor for about six minutes; add `draft` for a one-minute preview. Rebake after changing the hall's geometry or lamps.
- Hall scene after editing `scripts/hall_build.gd`: `godot --headless --path . --script res://scripts/hall_build.gd -- scene`.
- Knight: `blender --background --python tools/knight/build_knight.py -- --out assets/models/knight.glb` (80 s), then `godot --path . --headless --import`.
- Grinner: `blender --background --python tools/grinner/build_grinner.py -- --out assets/models/grinner.glb` (seven minutes), then import. `--shots dev/shots/grinner` adds turnarounds; `--clay a.png` alone previews the bare mesh.
- Never combine `--only` with `--out`: it overwrites the full model.
- Run: `godot --path .`. Playtest picker to pin: `tools\playtest\install.ps1` in the main checkout; `playtest.ps1 -DryRun` tests it.
- Scripted play and screenshots: `dev/drive.tscn` with `--fixed-fps 60`; `dev/shot.tscn` photographs a scene. Both take `lamps=baked` to drop the live character lights, and list their arguments in their headers.
- Never open Godot windows on the dev's screen for tests or bakes, unless he is playtesting: replace `godot` with `toolchain\blender\4.5\python\bin\python.exe -I dev\quiet.py`, which runs it on a hidden desktop. Put `--timing` first for GPU timing runs: it waits until no other Godot or Blender runs and holds other launches off.
- The game caps at 60 fps (`run/max_fps`). Frame times: `dev/drive.tscn` events `perf:start` and `perf:stop`, run with `--disable-vsync --max-fps 0`.
- Fast sculpt iteration: `tools/knight/preview_head.py` renders clay turnarounds.

## Where things are

- Playable scenes carry `metadata/playable`, their playtest picker title; `scenes/main.tscn` adds the hall and player (`scripts/main.gd`).
- `project.godot` holds the input map and names the layers; `scripts/layers.gd` gives code the same names.
- The `App` autoload, `scripts/app.gd`, holds the keys Esc, F11 and H, cursor capture and the controls hint for playable scenes.
- `scenes/outdoors.tscn` builds the grinner's foggy ground on load; drive and shot take `scene=res://scenes/outdoors.tscn`.
- `dev/` runs the game to test it; `tools/`, hidden from Godot, builds and fetches assets.
- `scripts/` holds the player controller, animator and camera rig; `shaders/` the wood, metal and eye shaders.
- The hall's lamps are baked. `scripts/hall.gd` replaces them at runtime with lights that reach only the Characters layer and with cancelling pairs that leave character shadows on the baked floor. Only the fire lights the hall live.
- `addons/lightmap_bake` presses the editor's bake button, the only way Godot bakes lightmaps.
- `tools/sculpt/` is the characters' shared toolkit: shapes, meshers, unwrapping, baking, turnarounds, GLB export.
- `tools/knight/` builds the knight; `tools/build_hall.py` and `scripts/hall_build.gd` build the hall.
- `assets/textures/knight/face_paint.png` is baked from `head.py` by the knight build.
- Only `KnightShadow`, a 4,700-triangle copy from `tools/knight/shadow.py`, casts the knight's shadows.
- `tools/grinner/` builds the first enemy and bakes its textures into the GLB; `import_lods.gd` sets the distances of its four detail levels. Shot shows it on `dev/stage.tscn` with `call=stand:res://assets/models/grinner.glb`, or `spread:` for the detail levels.

## Repository

- `tools/check_docs.sh` enforces the four documentation rules in `DEV.md`; `tools/hooks/pre-commit` runs it. After cloning: `git config core.hooksPath tools/hooks`.
- First-party means everything git tracks except `tools/downloads/`.
- Git ignores `toolchain/`, `.godot/`, `dev/shots/`, the Poly Haven files (`tools/fetch_assets.ps1`) and the built models and lightmap (`tools/build_models.ps1`).
- Commit with Windows git, not WSL.

## Downloads

All CC0: Quaternius Universal Animation Library 1 and 2 (hand-keyed, not mocap); Poly Haven scans and sky (`tools/fetch_assets.ps1` lists ids).

</Claude's notes>

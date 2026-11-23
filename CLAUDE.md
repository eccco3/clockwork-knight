The dev's rules, which bind every session, are in @DEV.md.

<Claude's notes>

## Tools

Everything the project needs is in this folder. `toolchain/` is third-party and hidden from Godot by `.gdignore`.

- Godot 4.7.2: `toolchain\godot\Godot_v4.7.2-stable_win64_console.exe`
- Blender 4.5.16: `toolchain\blender\blender.exe`
- Both are Windows-native: run them from PowerShell, not WSL.
- System `python` is a hanging Store stub. Use `toolchain\blender\4.5\python\bin\python.exe -I`.

## Build and run

- Both models, the Godot import and the hall's lightmap: `tools\build_models.ps1`. Needed after cloning.
- Lightmap alone: `godot --editor --path . res://scenes/hall.tscn -- bake-lightmaps` runs the editor for about six minutes; add `draft` for a one-minute preview. Rebake after changing the hall's geometry or lamps.
- Hall scene after editing `scripts/hall_build.gd`: `godot --headless --path . --script res://scripts/hall_build.gd -- scene`.
- Knight: `blender --background --python tools/knight/build_knight.py -- --out assets/models/knight.glb` (about 80 s), then `godot --path . --headless --import`.
- Never combine `--only` with `--out`: it overwrites the full model with a partial one.
- Run: `godot --path .`
- Scripted play and screenshots: `dev/drive.tscn` with `--fixed-fps 60`; `dev/shot.tscn` photographs a scene. Both take `lamps=baked` to drop the live character lights.
- Never open Godot windows on the dev's screen for tests or bakes, unless he is playtesting: replace `godot` with `toolchain\blender\4.5\python\bin\python.exe -I dev\quiet.py`, which runs it on a hidden desktop with the same arguments. Put `--timing` first for GPU timing runs: it waits until no other Godot or Blender runs and holds other launches off.
- The game caps at 60 fps (`run/max_fps`). Frame times: `dev/drive.tscn` events `perf:start` and `perf:stop`, run with `--disable-vsync --max-fps 0`.
- Fast sculpt iteration: `tools/knight/preview_head.py` renders clay turnarounds.

## Where things are

- `scenes/main.tscn` is the playable scene; `scripts/main.gd` adds the hall, player and hint.
- `scenes/outdoors.tscn` builds the grinner's foggy ground on load; drive and shot take `scene=res://scenes/outdoors.tscn`.
- `scripts/` holds the player controller, animator and camera rig; `shaders/` the wood, metal and eye shaders.
- The hall's lamps are baked. `scripts/hall.gd` replaces them at runtime with lights that reach only characters (render layer 2) and with cancelling pairs that leave character shadows on the baked floor. Only the fire lights the hall live.
- `addons/lightmap_bake` presses the editor's bake button, the only way Godot bakes lightmaps.
- `tools/knight/` builds the knight from signed-distance sculpts (`head.py`, `mesher.py`); `tools/build_hall.py` and `scripts/hall_build.gd` build the hall.
- `assets/textures/knight/face_paint.png` is baked from `head.py` by the knight build.
- Only `KnightShadow`, a 4,700-triangle copy from `tools/knight/shadow.py`, casts the knight's shadows.

## Repository

- `tools/check_docs.sh` enforces the four documentation rules in `DEV.md`; `tools/hooks/pre-commit` runs it. After cloning: `git config core.hooksPath tools/hooks`.
- First-party means everything git tracks except `tools/downloads/`.
- Git ignores `toolchain/`, `.godot/`, `dev/shots/`, the Poly Haven files, which `tools/fetch_assets.ps1` restores, and the built models `assets/models/*.glb` and lightmap `assets/lightmaps/`, which `tools/build_models.ps1` restores.
- Commit with Windows git, not WSL.

## Controls

Keyboard and mouse, then gamepad:

- Move: WASD or arrows; left stick. Walk: hold Ctrl or toggle C; L3.
- Jump: Space; A. Dodge-roll: Shift, Q or right mouse; B.
- Attack (three-hit combo): left mouse, J or F; X or RB.
- Look: mouse; right stick. Zoom 0.55 m to 6 m: mouse wheel.
- Esc frees the cursor, F11 is fullscreen, H hides the hint.

## Downloads

All CC0: Quaternius Universal Animation Library 1 and 2 (hand-keyed, not mocap); Poly Haven scans and sky (`tools/fetch_assets.ps1` lists ids).

</Claude's notes>

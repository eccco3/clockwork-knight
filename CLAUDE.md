<immutable without Peter's (the dev) blessing>
In this project you develop a game. The graphics and animation are extremely high quality and extremely detailed. Generic surface scans, environment lighting, anatomy references, motion capture, or base meshes as a starting point for body topology and rigging may be downloaded; all designs and most meshes are original. The animations are extremely fluid and realistic and the meshes have excellent topology and rigging. Be ambitious. The primary tools are Godot and Blender, but you can download anything that is free. The following rules must be enforced deterministically:

1. The only global documentation is the CLAUDE.md and the BACKLOG.md.
2. Claude's notes in the CLAUDE.md do not exceed 600 words.
3. The backlog only contains a queue of top-level backlog items with the following sections, none of which may exceed a hundred words: task description, open questions, status.
4. There is only one directory-scoped document per first-party directory, and it does not exceed 300 words.

The following is not enforced deterministically, but scripts and application files prefer code over comments.

All tasks that would take more than a minute are processed into backlog items, each sized for one session. After completing a backlog item:

1. Clear the backlog item.
2. Commit and push to the remote without asking.
3. If appropriate, recommend Peter to execute /clear or /compact before the next task.

</immutable without Peter's blessing>
<Claude's notes>

## Tools

Everything the project needs is in this folder. `toolchain/` is third-party and hidden from Godot by `.gdignore`.

- Godot 4.7.2: `toolchain\godot\Godot_v4.7.2-stable_win64_console.exe`
- Blender 4.5.16: `toolchain\blender\blender.exe`
- Both are Windows-native: run them from PowerShell, not WSL.
- System `python` is a hanging Store stub. Use `toolchain\blender\4.5\python\bin\python.exe -I`.

## Build and run

- Both models, the Godot import and the hall's lightmap: `tools\build_models.ps1`. Needed after cloning.
- Lightmap alone: `godot --editor --path . res://scenes/hall.tscn -- bake-lightmaps` opens the editor for about seven minutes; add `draft` for a one-minute preview. Rebake after changing the hall's geometry or lamps.
- Hall scene after editing `scripts/hall_build.gd`: `godot --headless --path . --script res://scripts/hall_build.gd -- scene`.
- Knight: `blender --background --python tools/knight/build_knight.py -- --out assets/models/knight.glb` (about 80 s), then `godot --path . --headless --import`.
- Never combine `--only` with `--out`: it overwrites the full model with a partial one.
- Run: `godot --path .`
- Scripted play and screenshots: `dev/drive.tscn` with `--fixed-fps 60`; `dev/shot.tscn` photographs a scene. Both take `lamps=baked` to drop the live character lights.
- So that drive and shot runs open off-screen without focus, add `--main-pack dev/unfocused/pack.zip` before the scene. In that mode `DirAccess` cannot list `res://`. The editor bake still takes focus.
- The game caps at 60 fps (`run/max_fps`). Frame times: `dev/drive.tscn` events `perf:start` and `perf:stop`, run with `--disable-vsync --max-fps 0`.
- Fast sculpt iteration: `tools/knight/preview_head.py` renders clay turnarounds.

## Where things are

- `scenes/main.tscn` is the playable scene; `scripts/main.gd` adds the hall, player and hint.
- `scripts/` holds the player controller, animator and camera rig; `shaders/` the wood, metal and eye shaders.
- The hall's lamps are baked. `scripts/hall.gd` replaces them at runtime with lights that reach only characters (render layer 2) and with cancelling pairs that leave character shadows on the baked floor. Only the fire lights the hall live.
- `addons/lightmap_bake` presses the editor's bake button, the only way Godot bakes lightmaps.
- `tools/knight/` builds the knight from signed-distance sculpts (`head.py`, `mesher.py`); `tools/build_hall.py` and `scripts/hall_build.gd` build the hall.
- `assets/textures/knight/face_paint.png` is baked from `head.py` by the knight build.

## Repository

- `tools/check_docs.sh` enforces the four documentation rules above; `tools/hooks/pre-commit` runs it. After cloning: `git config core.hooksPath tools/hooks`.
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

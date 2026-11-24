# Backlog

## Playtest launcher

### Task description

Give the dev one Windows taskbar button that starts a playtest. A click opens a small picker listing main and each worktree that can run the game, newest commit first, with its branch, commit subject and age; main is preselected, so Enter plays it. Before launching, fast-forward a clean main from `origin/main`, restore missing built models or lightmaps by copying them from the main checkout, and import if needed. Show failures in the picker instead of a vanishing console. Pin it with its own icon.

### Open questions

- None.

### Status

Not started.

## Test lower render scale

### Task description

After baking, measure real play at render scales 100%, 85%, 75%, 67% and 50% with each upscaler Godot offers: plain stretching, FSR 1, and FSR 2 with multisampling off. Record GPU time, power, temperature after five minutes from a cool start, and frame pacing. Save matching screenshots, standing and mid-swing, to `dev/shots/` for the dev to judge. Recommend one setting and apply it only with the dev's agreement.

### Open questions

- Is a softer picture acceptable if baking alone does not reach the cooler range?

### Status

Not started. Real play at the 60 fps cap now takes 6.9 ms of GPU time and 71 W with baked lighting; the live lighting took 8.9 ms and 76 W in the same test. The driver lowers the GPU clock below about 6.5 ms, and earlier tests reached 43 W only near 3.5 ms. Before baking, with plain stretching: 67% gave 72 W and 78 °C; 50% gave 43 W and 70 °C.

## Tech debt: input, layers and app keys

### Task description

`Player.setup_input()` builds the input map in code, so the editor shows none and `dev/drive.gd` must call it first. Define it in `project.godot`, and delete CLAUDE.md's Controls list, which repeats it and already misses K for the roll. Name the physics and render layers there too: replace the bare 1s and 2s in four scripts, and the knight's borrowed `Hall.CHARACTER_LAYER`, with shared constants the grinner's hit layers can join. Move Esc, F11 and cursor capture out of `player.gd` into one place with the H hint. Delete the unused `scenes/player.tscn`. Check play and scripted runs behave as before.

### Open questions

- Should the outdoors scene show the controls hint too?

### Status

Not started. Do it before the grinner's combat adds hit layers. It changes a line or two in files the other tech-debt items edit, so run it first or alone.

## Tech debt: one dev harness

### Task description

`dev/drive.gd` and `dev/shot.gd` both parse arguments, load a scene, apply `lamps=baked`, place a camera and save PNGs. Share that code, keeping their command lines in CLAUDE.md working. Delete `scripts/hall_perf.gd`, a probe among the runtime scripts; drive's `perf`, `set`, `env`, `vp` and `rs` events do its job. Fold `dev/grinner_stage` into `dev/stage`, which sets up the same sky and sun. Update drive's header, which omits `track`, `fps`, `hide`, `call`, `lookh` and `fov`. Prove nothing changed: the same commands give matching shots and perf output before and after.

### Open questions

- What separates `dev/` from `tools/`, and should they merge? Both hold scripts that are not the game: `dev/` the harnesses and stages, `tools/` the builders, but also probes and checks such as `tools/hall_check.gd`.
- Which tools should go, and which merge? For example, `dev/inspect_knight.gd` and `tools/knight/inspect_glb.py` both list a model's meshes, bones and clips, and nothing uses either.
- Delete `screenshots/`: seven unreferenced images, 14 MB, taken before the bake and the waxed wood?

### Status

Not started. Do it before the crowd performance test adds a `dev/` scene.

## Tech debt: hall builders

### Task description

`scripts/hall_build.gd` is an offline builder among the runtime scripts, and does two jobs: about 200 lines write materials, the rest assembles the scene. Split them, and keep them with the hall's import hook and `tools/hall_check.gd` outside `scripts/`, as the grinner's import script is. Let layout marks say which lights reach or shadow characters, instead of matching the names "Chandelier" and "Sconce". Drop the fallback that lets `build_hall.py` build a bare hall when `hall_props` fails to import. Share the two `hall_cloth` shaders, identical but for two lines, through an include. Prove the rebuilt `hall.glb`, `hall.tscn` and materials match the old ones.

### Open questions

- None.

### Status

Not started. Do it before the workshop extends these builders; it cannot run beside other hall or baking work. The `ns_` comments in `hall_import.gd` and `hall_props.py` are stale: four lights cast shadows, not five, and the live chandeliers draw only characters into shadow maps.

## Tech debt: the knight's materials and script

### Task description

`scripts/knight.gd` builds the knight's eight materials in code, beside her clip state, gait blending and clockwork motions. Move the materials out, so that Rosalyn, also lacquered wood and brass, can reuse the looks with her own colours. The face paint's placement is copied by hand from `build_knight.py` and `head.py` into `knight.gd`; let the build write it once. `knight_wood` and `knight_surface` repeat the same noise and vertex code; share it through a shader include. `tick()` and `_locomotion()` work out the same gait weights twice. Prove nothing changed with matching screenshots in the hall and outdoors, close up and full length.

### Open questions

- None.

### Status

Not started. Do it before Rosalyn's sculpt, so her build starts from shared materials. The shared sculpt toolkit, which also changed `build_knight.py`, is on main.

## Enemy: refine the sculpt

### Task description

Fix the grinner's weak spots before it is rigged: ragged geometry where the mouth pinches shut at each corner, which reads as cracks up the cheeks; a rough crease where jaw meets neck; a ragged hairline; and coarse, angular ears. Give the teeth their own texture variety and stop the limbs' paint mirroring. The grin stays fixed, so the mouth needs no cavity. Deliver before and after turnarounds of the head.

### Open questions

- None.

### Status

Not started. The model is merged; see `tools/grinner/`.

## Enemy: rig and waddle

### Task description

Rig the grinner with clean deformation at the reversed knees and hips, the long arms and the claws, in at most 50 bones. The grin is fixed, so the face needs no bones. Animate an idle and a slow waddle by hand in Blender, because the downloaded humanoid clips do not fit these proportions. Play them through Godot's built-in AnimationTree, not the knight's scripted blender, so that many can run cheaply. Deliver turnarounds and a contact sheet of the waddle.

### Open questions

- None. The dev chose original hand-keyed clips over an adapted motion library.

### Status

Not started. Starts once the refined sculpt is merged.

## Enemy: attack animations

### Task description

Animate two attacks with root motion: a pounce that leaps at the knight and rakes with one claw, and a twin-claw swipe made in place. Each has a readable wind-up, a hit window marked in the clip, and a recovery. Add a flinch and a death, and blend all of them with the waddle and idle in the AnimationTree. Deliver contact sheets of each.

### Open questions

- How far does the pounce travel, and how long is the warning before each attack?
- Can a grinner be staggered out of an attack?

### Status

Not started.

## Enemy: behaviour and combat

### Task description

Add `scripts/grinner.gd`: it waddles toward the knight, pounces from mid range and uses the twin-claw swipe up close, with cooldowns. Add the least combat both sides need: health, sword hits that land on grinners, claw hits that land on the knight, and a reaction to each. Place three grinners in the hall and record a scripted fight.

### Open questions

- What happens when the knight's health runs out?
- How many hits does a grinner take?
- Must grinners path around furniture now, or is a straight approach enough?

### Status

Not started.

## Enemy: crowd performance test

### Task description

Add a `dev/` scene that spawns a chosen number of grinners around the knight, and run it with the scripted-play harness at 1, 5, 10, 20 and 40. Record frame time, GPU time, CPU time spent on scripts and animation, triangles and draw calls. Find where 60 fps breaks and where GPU time crosses 6.5 ms. Then cut the largest costs, for example shadows and update rate for distant grinners, and report before and after.

### Open questions

- What is the largest number of enemies that should be on screen at once?

### Status

Not started. For comparison, one knight costs the GPU about 0.25 ms at mid distance.

## Rosalyn: sculpt the model

### Task description

Build a second clockwork woman as `assets/models/rosalyn.glb` from a new `tools/rosalyn/` builder on the shared sculpt toolkit. She is 1.75 m tall with a thin, feminine frame, carved from lacquered light tulipwood with small brass details. Her face is her own, clearly different from the hero's, with attractive features and blonde hair. She wears a modest, off-the-shoulder smocked dress in chartreuse and buttery yellow. Budget: 300,000 triangles if one setting can rebuild her lower later, otherwise 240,000. She tests several entities sharing the hall. Deliver clay and painted turnarounds beside the knight's.

### Open questions

- "Rosalyn" is a working name.

### Status

Not started. The shared toolkit is `tools/sculpt/`; `tools/grinner/build_grinner.py` shows its sculpt, bake and export pipeline in use.

## Rosalyn: rig and standing pose

### Task description

Rig Rosalyn: shoulders and upper body for gesturing, fingers, and a face that can speak, with jaw and lips. Skin the dress so the smocked bodice and skirt deform cleanly. Pose her standing with her hands clasped in front of her, and animate a quiet idle on that pose: breathing and small weight shifts. Deliver turnarounds and a contact sheet of the idle.

### Open questions

- Does the skirt need cloth simulation, or are bones enough while she stands?
- Do her eyes blink and move?

### Status

Not started.

## Rosalyn: speech and gestures

### Task description

Animate Rosalyn speaking: her mouth moves, and she gestures lightly by moving her upper body and shoulders, and with her hands too, though they mostly stay clasped. Make several looping speech clips that blend with the idle and with each other without repeating visibly, played through Godot's AnimationTree. Deliver contact sheets and a close-up capture of her face while speaking.

### Open questions

- Is there recorded or synthesised speech to match the mouth to, or only a generic talking motion?
- Does she turn her head to follow the knight?
- Are her words shown as text?

### Status

Not started.

## Rosalyn: place her and test two entities

### Task description

Stand Rosalyn in the hall and have her speak as the knight comes near. Check that both characters are lit, shadowed and reflected correctly together, and that the knight cannot walk through her. Measure frame time, GPU time and CPU time for animation with one and with both, in real play, and record a scripted approach and conversation.

### Open questions

- Where does she stand?
- Does she speak all the time, or only when the knight is close?

### Status

Not started.

## Plan the Clockmaker with the dev

### Task description

Plan the Clockmaker with the dev in the main chat; this is not a subagent task. She is an ordinary human woman: brilliant, spacey and amnesiac. Her likeness comes from the dev's wife, who will model for reference, aged from about 30 to 55. Decide how her likeness is captured (photo sets, a phone scan or photogrammetry), how she is aged, her build, clothes and voice, and her part in the story. Then split the plan into sculpt, rig, animation and placement items like Rosalyn's.

### Open questions

- Do reference photos and scans stay out of git?
- How does her amnesia show in play?
- What is her name?

### Status

Not started. Needs the dev.

## Plan the opening scene with the dev

### Task description

Plan the game's opening scene with the dev in the main chat; this is not a subagent task. The knight wakes up in the workshop. Decide where she lies, what she sees first, who is there, how control passes to the player, how the scene teaches the controls and how it leads into the hall. Then split the plan into backlog items for the scene, camera, animation and any dialogue.

### Open questions

- Is the waking a cutscene, played, or both?
- Is the Clockmaker there, and does she remember building the knight?
- Does the knight know what she is?

### Status

Not started. Needs the dev; the workshop items build the room.

## Workshop: walls, door and apartment

### Task description

The building is a clockmaker's house and workshop. Build the workshop's structure onto the hall: its width equals the hall's length, it is three times as long as it is wide, and a door in one of the hall's long walls joins them. A studio apartment fills one back corner as a closed room whose interior is not seen yet. Floor, walls, roof, beams and collision, matching the hall's construction, built by the same tools as the hall. Lighting comes later.

### Open questions

- Which long wall gets the door, and where along it?
- How tall is the workshop, and how large is the apartment's corner?
- Does the apartment show a door into the workshop?

### Status

Not started. It changes the hall's walls, so it cannot run beside other hall or baking work.

## Workshop: windows and surfaces

### Task description

Give the workshop windows onto the same foggy day the hall shows, and finish its surfaces: floorboards, plaster, panelling and timber matching the hall's materials, with wear where a craftsman works. Detail the door between the rooms and the apartment's outer walls. Compare screenshots with the hall for consistency.

### Open questions

- How many windows, and on which walls?

### Status

Not started. Needs the workshop's walls.

## Workshop: lamps and bake

### Task description

Light the workshop for close work: bench lamps, hanging lamps and the window daylight. Bake its lighting with the hall's, and give it runtime character lights and shadow handling like the hall's in `scripts/hall.gd`. Check both rooms together through the door. Measure GPU time in each room and looking through the door.

### Open questions

- None.

### Status

Not started. Needs the windows and surfaces; it rebakes the hall, so nothing else may bake at the same time.

## Workshop: research and layout

### Task description

Research real clockmakers' and automaton makers' workshops: benches, machines, tools, storage and how work flows between them. Write the findings into the workshop builder as a layout: where benches, machines, shelves and clutter zones go, with walkable aisles for the knight. Block it out with simple shapes and collision, and deliver overhead and eye-level screenshots.

### Open questions

- Dense clutter with narrow aisles, or open floor around the benches?

### Status

Not started. Needs the workshop's walls.

## Workshop: clocks

### Task description

Model original clocks of many kinds for the workshop: longcase, bracket and wall clocks, skeleton clocks, and bare movements on benches in various stages of assembly. Share parts between them so they instance well, give each detail levels, and place them following the layout.

### Open questions

- Do clocks tick and pendulums swing, or are they still for now?

### Status

Not started. Needs the research and layout.

## Workshop: benches, machines and tools

### Task description

Model original versions of the clockmaker's workbenches, tables, machines and hand tools found in the research, such as lathes, wheel-cutting engines, vises, loupes and parts trays. Place them following the layout, with collision where the knight can touch them, and detail levels throughout.

### Open questions

- None.

### Status

Not started. Needs the research and layout.

## Workshop: automata, trinkets and budget

### Task description

Model unfinished automata at different stages, from bare mechanism to painted figure, and scatter trinkets, parts and works in progress through the clutter zones. Then measure the finished workshop's GPU time, triangles and draw calls, and bring it within budget with instancing, detail levels and culling.

### Open questions

- None.

### Status

Not started. Needs the clocks, benches and tools.

# Backlog

## Test lower render scale

### Task description

After baking, measure real play at render scales 100%, 85%, 75%, 67% and 50% with each upscaler Godot offers: plain stretching, FSR 1, and FSR 2 with multisampling off. Record GPU time, power, temperature after five minutes from a cool start, and frame pacing. Save matching screenshots, standing and mid-swing, to `dev/shots/` for the dev to judge. Recommend one setting and apply it only with the dev's agreement.

### Open questions

- Is a softer picture acceptable if baking alone does not reach the cooler range?

### Status

Not started. Real play at the 60 fps cap now takes 6.9 ms of GPU time and 71 W with baked lighting; the live lighting took 8.9 ms and 76 W in the same test. The driver lowers the GPU clock below about 6.5 ms, and earlier tests reached 43 W only near 3.5 ms. Before baking, with plain stretching: 67% gave 72 W and 78 Ãƒâ€šÃ‚Â°C; 50% gave 43 W and 70 Ãƒâ€šÃ‚Â°C.

## Rosalyn: a moving mouth

### Task description

Try two ways for Rosalyn's wooden mouth to move with her speech, where no wood visibly bends. First, lips that part: a jaw bone turns a few degrees, opening the lip parting onto the dark pocket behind it, moving the skin about a millimetre. Second, stop-motion style shapes: a few rigid lacquered lip pieces, swapped or pivoted. Time both to her voice. Deliver both in motion, with sound, beside her still-mouthed speech: close-up videos from Godot's movie writer and a playable scene that switches between the three. The dev picks; if neither works, she keeps the still mouth.

### Open questions

None. Try both: four or five shapes as swapped meshes, and the same shapes as pieces on pivots.

### Status

Not started. Speech is built: four 12 s clips (Tell, Ask, Muse, Insist) crossed by her AnimationTree, `Rosalyn.say()` with subtitles, brows as decals on brow bones and `scripts/gaze.gd` turning her head to the knight; `dev/talk.tscn` tries it. No voice files yet, so a real voice stream is untested.

## Rosalyn: place her and test two entities

### Task description

Stand Rosalyn in the hall and have her speak as the knight comes near. Check that both characters are lit, shadowed and reflected correctly together, and that the knight cannot walk through her. Measure frame time, GPU time and CPU time for animation with one and with both, in real play, and record a scripted approach and conversation.

### Open questions

None. She stands by one of the windows closer to the first one, between that window and the fire. She speaks only when the knight is close, and idles otherwise.

### Status

Not started. Her scene needs a `Subtitles` node (`scripts/subtitles.gd`) for her lines to show.

## Plan the balance model with the dev

### Task description

Settle how a run stays balanced before combat numbers are built. Within a run she goes from one among equals to hero, starting low each time; her offence and defence upgrades keep pace with growing enemy damage and numbers. The meta loop widens her options and moves, with small number bonuses. Her minions can be chosen, added to or modified. Candidate model: one unit (grinner-equivalents) for threat and power, fixed upgrade axes priced in it, army size as slot points, minions stronger near her, fresh waves per area, and headless simulated runs.

### Open questions

- Do surviving minions carry over to the next area: all, none, or a few veterans?
- Does she order her minions (hold, push, follow), or do they act on their own?
- Can the army win a lane without her?
- Which minion upgrades belong to runs and which to the meta loop?

### Status

Planning with the dev; not for an agent.

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

## Workshop: lamps and bake

### Task description

Light the workshop for close work: bench lamps, hanging lamps and the window daylight. Bake its lighting with the hall's, and give it runtime character lights and shadow handling like the hall's in `scripts/hall.gd`. Check both rooms together through the door. Measure GPU time in each room and looking through the door.

### Open questions

- None.

### Status

Not started. Windows and worn surfaces are built (32 windows with FogLights, about 0.1 ms); the lightmap is a draft, grown to 4096×32768: its import holds about 2 GB, so cut the workshop's texel density or split the lightmap, and the full bake will take longer than 14 minutes. It rebakes the hall, so nothing else may bake at the same time.

## Workshop: research and layout

### Task description

Research real clockmakers' and automaton makers' workshops: benches, machines, tools, storage and how work flows between them. Write the findings into the workshop builder as a layout: where benches, machines, shelves and clutter zones go, with walkable aisles for the knight. Block it out with simple shapes and collision, coarse like the walls (this is for planning, not finish), and deliver overhead and eye-level screenshots.

### Open questions

None. Dense around the edges and the benches, with one or two clear aisles about the knight's width plus a margin.

### Status

Not started. The walls, windows and surfaces are built: 54 m workshop, 12 m apartment. Benches go in `WORK` (`tools/workshop_shell.py`), which the floor wear follows. Two nave posts at the apartment end stand in or half in its walls: move or remove them.

## Workshop: clocks

### Task description

Model original clocks of many kinds for the workshop: longcase, bracket and wall clocks, skeleton clocks, and bare movements on benches in various stages of assembly. Share parts between them so they instance well, give each detail levels, and place them following the layout.

### Open questions

None. Pendulums swing and a few clocks tick audibly: cheap looping animation on a handful of them.

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

## Knight: shoulder sockets and the overhead pauldron

### Task description

Her shoulders now stay out of her chest (`tools/knight/collar.py`, `follow.py`), but the thrusts (Sword_Regular_B, Regular_Combo, Dash) carry the right shoulder up to 9 cm forward, leaving its socket empty behind the ball, and the ball presses up to 8 mm into the socket's front rim in Heavy_Combo and Regular_A. Give the socket a cup carried by the collar bone, or open the chest toward the front. With the arm overhead (Heavy_Combo:32–34, 49–53) the right pauldron still sinks 13 mm into the chest. The death collapse leaves her pauldrons held.

### Open questions

- None.

### Status

Not started. Worst poses: `--gaps` in `build_knight.py`.

## Minion: rig and animation

### Task description

Rig the minion simply, with few bones, and hand-key an idle, a march, a spear thrust, a flinch and a death in Blender, played through Godot's AnimationTree like the grinner's so that dozens can run cheaply. Mark the thrust's hit window in the clip. Deliver contact sheets of each.

### Open questions

- None.

### Status

Not started. Better after the dev picks a clockwork variant (or a flavour) from the contact sheet, `build_minion.py -- --sheet`: 36 designs in six flavours, built with `--works flavour:seed` and adopted in `build_models.ps1`. Their wheels may be worth keying.

## Battles: intelligent multi-unit fights

### Task description

Make fights between groups outdoors, in the shape of a MOBA lane: waves of minions and grinners advance, meet and fight, with the knight among them. Units pick targets sensibly, hold formation, surround without stacking, and retreat or regroup when losing. Keep it cheap enough for 40 units at 60 fps, for example with staggered thinking and simple avoidance. Record a scripted battle and measure its CPU time.

### Open questions

- Which sides exist, and who fights whom?
- Do waves spawn on a timer, and what ends a run?

### Status

Not started. Needs the minion's animation. Grinners fight the knight (fighters carry `Health`, `Hurtbox`, `Strike`), but stand still while their attacks recharge, and their cost at 40 units is unmeasured.

## Combat: tuning from the dev's playtest

### Task description

The grinners and the knight now fight outdoors (`scripts/grinner.gd`, `player.gd`; numbers in the report of commit "Enemy: grinners fight"). Playtest with the dev and tune: the waddle's 0.29 m/s barely closes on her, the swipe has no clear wind-up, ichor and sparks are specks from the game camera, unaimed attacks follow her facing, and corpses stay. Re-key the waddle or add a run in `tools/grinner` if needed.

### Open questions

- Should grinners run at her, or stay slow and dangerous only in numbers?
- Do corpses fade, sink or stay?

### Status

Not started. Needs the dev's playtest.

## Faces: learn the dev's taste

### Task description

Add a `dev/` tool that shows the dev two faces from the morphable model side by side, rendered identically, and records which he prefers in about two seconds per pair. Fit a BradleyÃƒÂ¢Ã¢â€šÂ¬Ã¢â‚¬Å“Terry model over the shape coefficients, picking each next pair where the model is least sure, so 100 to 200 comparisons should be enough. Re-show about 5% of pairs to measure his consistency. Then sample faces along the learned direction, keep the best, and offer them for figures such as Rosalyn and the Clockmaker.

### Open questions

- None. The dev rates in several short sittings, so the tool saves every answer at once and resumes where he left off.

### Status

Built, women and men rated apart: a face is 62 scan components, 22 MakeHuman features and 6 brow numbers, with slight random asymmetry on final faces only. The dev rates in the launcher's two rating tools (his 91 women's answers still count); every 40 answers they render the next refinement round in the background and switch to it, and B shows the best faces.

## Knight: shattering on death

### Task description

When the knight's health runs out, break her apart: armour plates, limbs and clockwork pieces come loose and scatter with simple physics, then settle on the ground before the screen fades. Split her along her existing parts where possible, add a few gears and springs flung from inside, and keep it cheap. Record clips from two angles.

### Open questions

- Does she shatter in place of the collapse, or after kneeling?

### Status

Low priority. Not started. Builds on the collapse and restart from "Enemy: behaviour and combat".

## Rosalyn: blemishes left from her rig

### Task description

Fix what her speech work found but left. A pale streak runs down the skirt's side in Godot: its lighting and normal buffers show wrong normals along the panels' side seam, likely the baked normal map's tangent frame against the exported tangents in `tools/sculpt/bake.py`. Pale jagged slivers show along the lower lids near both corners in close-ups. The palm's edge creases, probably because the arm's lattice is half the palm's thickness (`body.arm_boxes`); recheck the clasp after. A fully overhead raise bulks the sleeve (`rig.py` weights).

### Open questions

- The dark tick at each outer lid corner is the lash paint running into the corner's crack, which the sleeping lid's raised ends carry. Taper the lash band before the crack, or give the lids unpainted wood?

### Status

Not started. Evidence in the speech branch's `dev/shots/speech/diag_*` and `dbg_*`.

## Grinners: flinch when hit

### Task description

Grinners now flinch only when a blow lands during an attack's wind-up, and otherwise just jolt. Turn that around: any blow makes a grinner flinch, cutting into what it was doing, except while it is mid-pounce (in the air) or toward the end of its claw swipe, when it shrugs the blow off with only the jolt. Mark those windows in the clips like the hit windows, in `tools/grinner/moves.py` and `scripts/grinner.gd`. Record clips of each case.

### Open questions

- Does the scuttler's bite follow the same rule as the swipe?

### Status

Not started.

## Sculpt: lid snaps and bake bleed

### Task description

Two faults in the shared `tools/sculpt/` modules, found on the faces' bust (`tools/faces/build_bust.py`). White specks run along the lids in extreme close-ups: a few vertices of the lids' two edge loops land on the wrong side in the mesher's inner snap. Dark streaks show along the bust's UV seams at the throat and crown from about 1 m in Godot: lower mip levels reach past the bake's 12 texels of bleed (`bake.dilate`). Fix both for every figure that uses them, and check the knight, grinner and Rosalyn for changes.

### Open questions

- None.

### Status

Not started. The bust also has about 27 folded quads at the eye corners, no detail levels or shadow stand-in, and always the short crop.

# Backlog

## Test lower render scale

### Task description

After baking, measure real play at render scales 100%, 85%, 75%, 67% and 50% with each upscaler Godot offers: plain stretching, FSR 1, and FSR 2 with multisampling off. Record GPU time, power, temperature after five minutes from a cool start, and frame pacing. Save matching screenshots, standing and mid-swing, to `dev/shots/` for the dev to judge. Recommend one setting and apply it only with the dev's agreement.

### Open questions

- Is a softer picture acceptable if baking alone does not reach the cooler range?

### Status

Not started. Real play at the 60 fps cap now takes 6.9 ms of GPU time and 71 W with baked lighting; the live lighting took 8.9 ms and 76 W in the same test. The driver lowers the GPU clock below about 6.5 ms, and earlier tests reached 43 W only near 3.5 ms. Before baking, with plain stretching: 67% gave 72 W and 78 °C; 50% gave 43 W and 70 °C.

## Grinner: a flatter rump

### Task description

Make the grinner's rump a little flatter, in the sculpt and the shorts over it, in `tools/grinner/body.py`. The shorts' seat still has a fixed bulge shaped for the old, further-back thigh from before the knees were straightened. Keep the hips' width and the shorts' hang, and check the seat in the idle and waddle. Deliver side and back turnarounds before and after.

### Open questions

- None.

### Status

Not started.
## Grinner: a variant on all fours

### Task description

Make a second kind of grinner that moves on all fours, much faster than the walking one. Give it a quick four-legged run, a pounce quicker than the walking grinner's, and a biting attack, each with a readable wind-up, a hit window marked in the clip, and a recovery, plus an idle, a flinch and a death. Blend them in an AnimationTree, and deliver contact sheets of each and a capture of it running beside the walking grinner.

### Open questions

- None. The agent chooses whether it shares the walking grinner's model or has its own sculpt, and sets its speed and wind-ups. Its jaw opens for the bite.

### Status

Not started. Comes after the walking grinner's attack animations.
## Enemy: behaviour and combat

### Task description

Extend `scripts/grinner.gd`, which now only plays the idle and waddle: it waddles straight at the knight, pounces from mid range and swipes up close, with cooldowns. Add the least combat both sides need: health, sword hits that land on grinners, claw hits on the knight, and reactions. A grinner dies to three hits, and flinches only when hit during a wind-up. When the knight's health runs out she collapses, the screen fades and the scene restarts. Replace the stand-in pacing grinners in `scripts/outdoors.gd` with three real ones and record a scripted fight.

### Open questions

- None.

### Status

Not started. Enemies only appear outside; see the crowd item.
## Enemy: crowd performance test

### Task description

Add a `dev/` scene that spawns a chosen number of grinners around the knight outdoors, and run it with the scripted-play harness at 1, 6, 12, 24 and 40. Record frame time, GPU time, CPU time spent on scripts and animation, triangles and draw calls. Find where 60 fps breaks and where GPU time crosses 6.5 ms. Then cut the largest costs, for example shadows and update rate for distant grinners, and report before and after.

### Open questions

- None. Up to 12 grinners on screen; later, up to 40 allies and enemies in all.

### Status

Not started. For comparison, one knight costs the GPU about 0.25 ms at mid distance.
## Rosalyn: rig and standing pose

### Task description

Rig Rosalyn: shoulders and upper body for gesturing, fingers, and her head and neck. Her wooden face does not deform. Skin the dress so the smocked bodice and skirt deform cleanly. Pose her standing with her hands clasped in front of her, and animate a quiet idle on that pose: breathing and small weight shifts. Deliver turnarounds and a contact sheet of the idle.

### Open questions

- Does the skirt need cloth simulation, or are bones enough while she stands?
- Do her eyes blink and move?

### Status

Not started.

## Rosalyn: speech and gestures

### Task description

Rosalyn is voiced. Animate her speaking her lines without moving her mouth, which is wood: she speaks through head tilts, her eyes and brows, and gestures lightly by moving her upper body and shoulders, and with her hands too, though they mostly stay clasped. Make several looping speech clips that blend with the idle and with each other without repeating visibly, played through Godot's AnimationTree. Deliver contact sheets and a close-up capture of her face while speaking.

### Open questions

- Does she turn her head to follow the knight?
- Are her words shown as text?

### Status

Not started.

## Rosalyn: a moving mouth

### Task description

Try two ways for Rosalyn's wooden mouth to move with her speech, where no wood visibly bends. First, lips that part: a jaw bone turns a few degrees, opening the lip parting onto the dark pocket behind it, moving the skin about a millimetre. Second, stop-motion style shapes: a few rigid lacquered lip pieces, swapped or pivoted. Time both to her voice. Deliver both in motion, with sound, beside her still-mouthed speech: close-up videos from Godot's movie writer and a playable scene that switches between the three. The dev picks; if neither works, she keeps the still mouth.

### Open questions

- How many shapes, and are they swapped meshes or pieces on pivots?

### Status

Not started. Comes after speech and gestures.

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

## Knight: cover her seat

### Task description

Cover the knight's seat a little more, standing and in every clip, rolls above all. Try two ways: a short skirt of plates or tassets hanging from her belt, and reshaped hip armour that reaches lower behind. Each must not catch her thighs in the run, roll, jump or attacks; check clearance in every clip. Deliver painted turnarounds and roll contact sheets of both beside the current armour, and the dev picks.

### Open questions

- None. The dev picks between the two.

### Status

Not started. Shares the knight's builder with her shoulder and hand items.
## Knight: shoulder and chest clearance

### Task description

In the sword clips her upper arm sinks up to 30 mm into her chest and passes through the pauldron, and her right arm reaches her face in `Sword_Regular_B:6`. Lift or reshape the pauldron, and fix the collar bone's travel or the chest's pocket, so the arm clears both. Measure with the builder's `--gaps` before and after, over all 21 clips, and deliver close-ups of the worst poses.

### Open questions

- None.

### Status

Not started. Shares the knight's builder with her hand and seat items.

## Knight: a more feminine hand

### Task description

Make the knight's hands a little more feminine in 	ools/knight/build_knight.py: a narrower palm and wrist, slimmer and slightly longer fingers that taper toward the tips, smaller knuckles and softer padding, keeping her wooden jointed construction and her grip on the sword. Check the grip, fist and open hand in her clips, and deliver clay and painted close-ups before and after.

### Open questions

- None.

### Status

Not started. Shares the builder with the natural shoulder, so one runs after the other.
## Minion: sculpt the model

### Task description

Build a small clockwork soldier as `assets/models/minion.glb` from a new `tools/minion/` builder on the shared sculpt toolkit: an adult man, short and stocky, carrying a short spear. He needs far less human likeness than the knight or Rosalyn; a simple, readable, mechanical design is right, since many share the field. Give him detail levels and a cheap shadow stand-in from the start. Deliver clay and painted turnarounds beside the knight's.

### Open questions

- How tall is he, and what is his triangle budget at full detail?
- Is he an ally of the knight, an enemy, or are there both kinds?

### Status

Not started.

## Minion: rig and animation

### Task description

Rig the minion simply, with few bones, and hand-key an idle, a march, a spear thrust, a flinch and a death in Blender, played through Godot's AnimationTree like the grinner's so that dozens can run cheaply. Mark the thrust's hit window in the clip. Deliver contact sheets of each.

### Open questions

- None.

### Status

Not started. Needs the minion's sculpt.

## Battles: intelligent multi-unit fights

### Task description

Make fights between groups outdoors, in the shape of a MOBA lane: waves of minions and grinners advance, meet and fight, with the knight among them. Units pick targets sensibly, hold formation, surround without stacking, spread their attacks over time, and retreat or regroup when losing. Keep it cheap enough for 40 units at 60 fps, for example with staggered thinking and simple avoidance. Record a scripted battle and measure its CPU time.

### Open questions

- Which sides exist, and who fights whom?
- Do waves spawn on a timer, and what ends a run?

### Status

Not started. Needs the minion's animation and the grinner's behaviour and combat.

## Knight: light between her joints

### Task description

Faint streaks of white light sprinkle across the air gaps between the knight's jointed parts. They are translucent and faint at rest, and brighter and more striking while the joint moves. They light nothing around them. Make them cheap, for example a shader on thin cards or particles driven by each joint's angular speed. Deliver captures at rest and mid-swing.

### Open questions

- None.

### Status

Not started.

## Faces: separate ratings for men and women

### Task description

Split the face-rating tool into two: one rates women's faces and one men's, each with its own pool, answers file and learned direction, and its own launcher entry. The face kit has no sex labels, so find a direction in the shape coefficients that separates female from male faces. Use known differences such as brow ridge, jaw and nose size, and confirm it with grids of each end. If that is unclear, add a short labelling pass for the dev. Each pool samples clearly on its side, with the same spread as now.

### Open questions

- None.

### Status

Not started. No ratings exist yet.
## Faces: crisper features and use in a figure

### Task description

The morphable model in `tools/faces/` has ragged ears, slightly jagged nostril edges and outer eye corners, a soft lip groove with no edge loop, and dark smudges under the flat neck cut. Add a lip rail like Rosalyn's, handle the ears' undercuts, and speed up `scan.Solid.field`. Then wire a sampled face into a figure build, with its field for baking and hidden tests and a neck join, and add the model to `build_models.ps1`. Keep each coefficient's meaning, so the dev's ratings stay valid. Deliver the grid again and a figure wearing a sampled face.

### Open questions

- None.

### Status

Not started.

## Faces: learn the dev's taste

### Task description

Add a `dev/` tool that shows the dev two faces from the morphable model side by side, rendered identically, and records which he prefers in about two seconds per pair. Fit a Bradley–Terry model over the shape coefficients, picking each next pair where the model is least sure, so 100 to 200 comparisons should be enough. Re-show about 5% of pairs to measure his consistency. Then sample faces along the learned direction, keep the best, and offer them for figures such as Rosalyn and the Clockmaker.

### Open questions

- None. The dev rates in several short sittings, so the tool saves every answer at once and resumes where he left off.

### Status

The tool is built and its faces rendered: the dev runs `res://dev/taste.tscn` in Godot to rate, commits `tools/faces/taste.jsonl`, then `build_faces.py -- --best` makes the final faces.

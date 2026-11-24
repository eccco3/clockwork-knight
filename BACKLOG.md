# Backlog

## Test lower render scale

### Task description

After baking, measure real play at render scales 100%, 85%, 75%, 67% and 50% with each upscaler Godot offers: plain stretching, FSR 1, and FSR 2 with multisampling off. Record GPU time, power, temperature after five minutes from a cool start, and frame pacing. Save matching screenshots, standing and mid-swing, to `dev/shots/` for the dev to judge. Recommend one setting and apply it only with the dev's agreement.

### Open questions

- Is a softer picture acceptable if baking alone does not reach the cooler range?

### Status

Not started. Real play at the 60 fps cap now takes 6.9 ms of GPU time and 71 W with baked lighting; the live lighting took 8.9 ms and 76 W in the same test. The driver lowers the GPU clock below about 6.5 ms, and earlier tests reached 43 W only near 3.5 ms. Before baking, with plain stretching: 67% gave 72 W and 78 °C; 50% gave 43 W and 70 °C.

## Fewer chandelier shadows

### Task description

The knight's shadows cost about 0.8 ms of GPU time, but not because of her triangles: the 4,700-triangle `KnightShadow` saved nothing measurable over the full mesh. The cost is per shadowed light. Keep the knight's shadow only from the chandelier nearest her, handing it over between chandeliers without a visible pop, and try dual-paraboloid omni shadows. Measure scripted play before and after.

### Open questions

- Should distant chandeliers stop casting her shadow altogether?
- Is a dual-paraboloid shadow's softer, slightly warped shape acceptable?

### Status

Not started. Scripted play: 6.8 ms with three shadowed chandeliers, 6.3 ms with only the middle one, 6.6 ms with dual paraboloids, 6.0 ms with none.

## Enemy: sculpt the model

### Task description

Build the first enemy as `assets/models/grinner.glb` from a new `tools/grinner/` builder that follows the knight's sculpt pipeline. It reads as a ten-year-old boy, wrong in five ways: a smile too wide for the face, pitch-black eyes, arms that reach past the knees, claws, and legs whose knees and hips bend backwards. Budget: 40,000 triangles at full detail (the knight has 303,000), detail levels down to 5,000, at most four materials, and textures baked from the sculpt instead of procedural shaders.

### Open questions

- What does it wear, and what are its skin and colouring?
- Is 40,000 triangles right, or should close views get more?
- "Grinner" is a working name.

### Status

Not started.

## Enemy: rig and waddle

### Task description

Rig the grinner with clean deformation at the reversed knees and hips, the long arms, the claws and the wide jaw, in at most 50 bones. Animate an idle and a slow waddle by hand in Blender, because the downloaded humanoid clips do not fit these proportions. Play them through Godot's built-in AnimationTree, not the knight's scripted blender, so that many can run cheaply. Deliver turnarounds and a contact sheet of the waddle.

### Open questions

- Are original hand-keyed clips acceptable, or should a downloaded motion library be adapted?
- Does the face move, or is the smile fixed?

### Status

Not started.

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

## Shared sculpt toolkit

### Task description

Move the parts of `tools/knight/` that any character uses into a new `tools/sculpt/` package: the signed-distance shapes, mesher, frames, texture baking, Blender helpers and export. Fold in duplicates such as `tools/grinner/sculpt.py`. Leave in `tools/knight/` and `tools/grinner/` only what makes each character itself. Prove the refactor changed nothing: rebuild both models and compare vertex counts, bounds and turnarounds before and after.

### Open questions

- None.

### Status

Not started. Wait for the grinner sculpt to merge; Rosalyn's sculpt should build on this.

## Rosalyn: sculpt the model

### Task description

Build a second clockwork woman as `assets/models/rosalyn.glb` from a new `tools/rosalyn/` builder on the shared sculpt toolkit. She is 1.75 m tall with a thin, feminine frame, carved from lacquered light tulipwood with small brass details. Her face is her own, clearly different from the hero's, with attractive features and blonde hair. She wears a modest, off-the-shoulder smocked dress in chartreuse and buttery yellow. Budget: 300,000 triangles if one setting can rebuild her lower later, otherwise 240,000. She tests several entities sharing the hall. Deliver clay and painted turnarounds beside the knight's.

### Open questions

- "Rosalyn" is a working name.

### Status

Not started. Wait for the shared sculpt toolkit.

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

## Outdoors: soften the light on her helmet

### Task description

In the foggy outdoors scene the knight's helmet catches a hard highlight that overcast light should not make. Her materials are right, since the helmet looks good in the hall, so fix the outdoor lighting instead: the sun's 7° angular size and strength, the sky's reflections and the ambient light in `scripts/outdoors.gd` and `shaders/outdoors_sky.gdshader`. Don't change knight materials. Compare screenshots outdoors before and after, standing and turning, check the hall is unchanged and GPU time is not worse.

### Open questions

- Should any direction of sunlight be visible through the fog, or should it be fully overcast?

### Status

Not started. The outdoors scene is on branch `worktree-agent-a540b2b1af48a3c2d`, not yet merged.

## Workshop: build the shell

### Task description

The building is a clockmaker's house and workshop. Build the workshop onto the hall: its width equals the hall's length, it is three times as long as it is wide, and a door in one of the hall's long walls joins them. A studio apartment fills one back corner of the workshop as a closed room whose interior is not seen yet. Match the hall's construction and materials, give it windows onto the same foggy day, and rebake the lighting. Measure GPU time in both rooms.

### Open questions

- Which long wall gets the door, and where along it?
- How tall is the workshop, and how large is the apartment's corner?
- Does the apartment show a door into the workshop?

### Status

Not started. It changes the hall's walls and lightmap, so it cannot run beside other hall or baking work.

## Workshop: fill it with clutter

### Task description

Fill the workshop with a working clockmaker's clutter: clocks of many kinds, workbenches and tables, trinkets, unfinished automata, and the machines and tools a clockmaker builds with. Research what real clockmakers and automaton makers use, then model original versions. The knight must still move through it with correct collision. Keep GPU time in budget with instancing and detail levels.

### Open questions

- Dense clutter with narrow aisles, or open floor around the benches?
- Do clocks tick and pendulums swing, or are they still for now?

### Status

Not started. Needs the workshop shell.

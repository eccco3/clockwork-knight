# Backlog

## Bake the hall's lighting

### Task description

Bake the hall's static lights and bounce light into lightmaps, replacing VoxelGI and the live cost of about thirty unshadowed lights. Build two variants and compare them with screenshots, GPU time and GPU power: (A) everything baked except the fire and the knight's own shadows; (B) as A, plus live copies of the chandelier and sconce lights that light only characters, to keep highlights on lacquer and brass. Add the bake to `tools/build_models.ps1` and git-ignore its output.

### Open questions

- Godot's lightmap baker may only run inside the editor. If it cannot be scripted, is baking in Blender acceptable?

### Status

Not started. Peter: it is always daytime with heavy fog outdoors, so the time of day is fixed; first change the hall's window light from blue dusk to foggy daylight, then bake. Baseline in real play: 9 ms GPU time, 81 W, 87 °C. The driver lowers the GPU clock below about 6.5 ms; 5 ms gave 72 W and 3.5 ms gave 43 W.

## Test lower render scale

### Task description

After baking, measure real play at render scales 100%, 85%, 75%, 67% and 50% with each upscaler Godot offers: plain stretching, FSR 1, and FSR 2 with multisampling off. Record GPU time, power, temperature after five minutes from a cool start, and frame pacing. Save matching screenshots, standing and mid-swing, to `dev/shots/` for Peter to judge. Recommend one setting and apply it only with his agreement.

### Open questions

- Is a softer picture acceptable if baking alone does not reach the cooler range?

### Status

Not started. Measured before baking, with plain stretching: 67% gave 72 W and 78 °C; 50% gave 43 W and 70 °C.

## Outdoors: foggy ground scene

### Task description

Build `scenes/outdoors.tscn`, the grinner's real environment, so it can be tested there: only ground with sparse grass, and heavy daytime fog. Use a scanned ground material, instanced grass that thins with distance, and the fixed foggy daylight the hall's windows show. Spawn the knight in it, make it loadable by `dev/drive.tscn` and `dev/shot.tscn`, and record GPU time against the hall.

### Open questions

- How far should one see before the fog closes in?
- Is the ground flat or gently rolling?
- Should the hall's exterior stand in the scene?

### Status

Not started.

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

## Lady: sculpt the model

### Task description

Build a second clockwork woman as `assets/models/lady.glb` from a new `tools/lady/` builder that reuses the knight's sculpt pipeline. Her face is her own, clearly different from the hero's, with attractive features. She wears a modest, off-the-shoulder smocked dress. She exists to test several entities sharing the study. Deliver clay and painted turnarounds beside the knight's.

### Open questions

- "Lady" is a working name.
- Is she lacquered wood and brass like the knight, and what colours are the dress and hair?
- What triangle budget: the knight's 303,000, or less?
- Is "the study" the hall, or a new room?

### Status

Not started.

## Lady: rig and standing pose

### Task description

Rig the lady: shoulders and upper body for gesturing, fingers, and a face that can speak, with jaw and lips. Skin the dress so the smocked bodice and skirt deform cleanly. Pose her standing with her hands clasped in front of her, and animate a quiet idle on that pose: breathing and small weight shifts. Deliver turnarounds and a contact sheet of the idle.

### Open questions

- Does the skirt need cloth simulation, or are bones enough while she stands?
- Do her eyes blink and move?

### Status

Not started.

## Lady: speech and gestures

### Task description

Animate the lady speaking: her mouth moves, and she gestures lightly by moving her upper body and shoulders while her hands stay clasped. Make several looping speech clips that blend with the idle and with each other without repeating visibly, played through Godot's AnimationTree. Deliver contact sheets and a close-up capture of her face while speaking.

### Open questions

- Is there recorded or synthesised speech to match the mouth to, or only a generic talking motion?
- Does she turn her head to follow the knight?
- Are her words shown as text?

### Status

Not started.

## Lady: place her and test two entities

### Task description

Stand the lady in the study and have her speak as the knight comes near. Check that both characters are lit, shadowed and reflected correctly together, and that the knight cannot walk through her. Measure frame time, GPU time and CPU time for animation with one and with both, in real play, and record a scripted approach and conversation.

### Open questions

- Where does she stand?
- Does she speak all the time, or only when the knight is close?

### Status

Not started.

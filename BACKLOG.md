# Backlog

## Bake the hall's lighting

### Task description

Bake the hall's static lights and bounce light into lightmaps, replacing VoxelGI and the live cost of about thirty unshadowed lights. Build two variants and compare them with screenshots, GPU time and GPU power: (A) everything baked except the fire and the knight's own shadows; (B) as A, plus live copies of the chandelier and sconce lights that light only characters, to keep highlights on lacquer and brass. Add the bake to `tools/build_models.ps1` and git-ignore its output.

### Open questions

- Godot's lightmap baker may only run inside the editor. If it cannot be scripted, is baking in Blender acceptable?
- The hall's windows are lit as blue dusk today. Change them to foggy daylight before baking?

### Status

Not started. Peter: it is always daytime with heavy fog outdoors, so the time of day is fixed. Baseline in real play: 9 ms GPU time, 81 W, 87 °C. The driver lowers the GPU clock below about 6.5 ms; 5 ms gave 72 W and 3.5 ms gave 43 W.

## Test lower render scale

### Task description

After baking, measure real play at render scales 100%, 85%, 75%, 67% and 50% with each upscaler Godot offers: plain stretching, FSR 1, and FSR 2 with multisampling off. Record GPU time, power, temperature after five minutes from a cool start, and frame pacing. Save matching screenshots, standing and mid-swing, to `dev/shots/` for Peter to judge. Recommend one setting and apply it only with his agreement.

### Open questions

- Is a softer picture acceptable if baking alone does not reach the cooler range?

### Status

Not started. Measured before baking, with plain stretching: 67% gave 72 W and 78 °C; 50% gave 43 W and 70 °C.

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

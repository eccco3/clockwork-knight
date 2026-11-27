# Backlog

## Faces: a face maker for the women, with dials

### Task description

The dev: "a face maker which has dials for the features", for the women; the men finish their track first. A launcher tool, live in Godot: the face model's head as a mesh whose blend shapes are its numbers, painted and lit as the sheets, long hair. A dial per named feature (the 22, brows, kept candidates within his ranges), a few for the scan numbers, Randomize drawing as Face picks does at full spread, a profile turn, and saving faces for characters; sex a parameter. Every sheet face looked fine to him: he wants variety, not narrowing.

### Open questions

- None.

### Status

Paused by the dev, unmerged on branch `worktree-agent-a1328d10d040914ae` (5b634c5): a live head with blend shapes (`build_head.py`, `glb.py`, `face_head.gd`), face, hair and filmic shaders, and the tool's dials and buttons work. Left: undo the shaders' temporary matte calibration edits, then match the Blender sheets: a seam down the face, blocky eyes, striped hair, broken ear edges.

## Faces: the men's track, from the launcher

### Task description

Repeat the women's track for the men with the dev's wife's taste, every step a launcher tool in order: pick favourites from men's pool sheets; base face = their average pushed 2× (preview 1×, 1.5×, 2× and paints); candidate features on it, front and profile, men's own included; picking rounds. Generalise `candidates.py`, the features and picks tools by sex and rater; keep her answers apart. Carry the lessons: scans at 1×, the 22 at 0.5×, procedural eyes, ≥75% scan-covered features dropped unless her favourite is far out, shrinkage spreads, the taste model only once it predicts her picks.

### Open questions

- Skip pairwise rating and start from picks? Recommended: yes. The women's base came from picks, and the taste model is unproven; keep Face rating: men for later, to train a filter.
- Let the men's draws reach toward androgynous? Recommended: yes, to the sex direction's middle and not past it, with no separate androgynous pool; her picks and the shrinkage decide how far.
- Facial hair: out (the dev).
- Men's paint? Recommended: the plain paint, no lash line and the default lips, previewed beside a faint lash line for her to choose.

### Status

Not started. The women's picking rounds are in (`tools/faces/rounds.py`, `pick.py`, `dev/picks.gd`, with a `sex` export). No androgynous pool exists: the labels' androgynous answers only mark the middle of the sex direction, and the men's pool is drawn on the men's side.

## Faces: lines across the women's ears

### Task description

The dev sees horizontal lines running across the women's ears in the rating tool. Find the cause and fix it without changing any face's numbers, so the dev's answers stay valid, then re-render the affected sets with `build_faces.py --again`. Suspects: the long hair's `groom()` and `ears()` tucking it behind the ears (`WOMEN` in `build_faces.py`), and the ears' undercut bridging by `mesher.wrap`'s `slope` from the crisper-features work. Compare a men's face, which wears the short crop.

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

Not started. Real play at the 60 fps cap now takes 6.9 ms of GPU time and 71 W with baked lighting; the live lighting took 8.9 ms and 76 W in the same test. The driver lowers the GPU clock below about 6.5 ms, and earlier tests reached 43 W only near 3.5 ms. Before baking, with plain stretching: 67% gave 72 W and 78 Ãƒâ€šÃ‚Â°C; 50% gave 43 W and 70 Ãƒâ€šÃ‚Â°C.

## Plan the run with the dev

### Task description

Keep settling the run's design with the dev in the main chat; this is not a subagent task. `DESIGN.md` holds the decisions and its own open points. Then split the plan into backlog items: the escort area and payload, the retinue and their AI, the captains, items, level-ups and attributes, the curves, and the headless simulation with its bot playing the knight.

### Open questions

- The open points at the end of `DESIGN.md`.

### Status

Planning with the dev. The run's shape, sides, commands and growth are settled.

## Plan the stats with the dev

### Task description

Develop the attributes and derived stats in `DESIGN.md` into formulas, with the dev. Physical damage first: how strength, dexterity and luck feed physical damage, critical damage, attack speed and critical chance, how they multiply, where the soft ceilings sit, and how abilities scale from several derived stats. Then magic's own multipliers, without strength improving pure magic builds.

### Open questions

- Does critical chance apply to magic, and does magic get a critical damage of its own?
- Is there mana, separate from stamina, which some skills spend and many magic skills multiply by?

### Status

Not started. Needs the dev; physical damage is the focus for now.

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

## Plan the workshop with the dev

### Task description

Plan the workshop with the dev in the main chat; this is not a subagent task. The dev has new ideas for it. Built so far: walls, 32 windows and worn surfaces, a 54 m workshop and a 12 m apartment (`tools/workshop_shell.py`, whose `WORK` the floor wear follows). Two nave posts at the apartment end stand in its walls. Settle the layout and what fills it, then split the plan into backlog items, replacing the clocks, benches and automata items below if they no longer fit.

### Open questions

- What are the dev's new ideas for the workshop?

### Status

Not started. Needs the dev.

## Workshop: clocks

### Task description

Model original clocks of many kinds for the workshop: longcase, bracket and wall clocks, skeleton clocks, and bare movements on benches in various stages of assembly. Share parts between them so they instance well, give each detail levels, and place them following the layout.

### Open questions

None. Pendulums swing and a few clocks tick audibly: cheap looping animation on a handful of them.

### Status

Not started. Needs the workshop plan.

## Workshop: benches, machines and tools

### Task description

Model original versions of the clockmaker's workbenches, tables, machines and hand tools found in the research, such as lathes, wheel-cutting engines, vises, loupes and parts trays. Place them following the layout, with collision where the knight can touch them, and detail levels throughout.

### Open questions

- None.

### Status

Not started. Needs the workshop plan.

## Workshop: automata, trinkets and budget

### Task description

Model unfinished automata at different stages, from bare mechanism to painted figure, and scatter trinkets, parts and works in progress through the clutter zones. Then measure the finished workshop's GPU time, triangles and draw calls, and bring it within budget with instancing, detail levels and culling.

### Open questions

- None.

### Status

Not started. Needs the clocks, benches and tools.

## Minion: rig and animation

### Task description

Rig the minion simply, with few bones, and hand-key an idle, a march, a spear thrust, a flinch and a death in Blender, played through Godot's AnimationTree like the grinner's so that dozens can run cheaply. Mark the thrust's hit window in the clip. Deliver contact sheets of each.

### Open questions

- None.

### Status

Not started. Better after the dev picks a clockwork variant (or a flavour) from the contact sheet, `build_minion.py -- --sheet`: 36 designs in six flavours, built with `--works flavour:seed` and adopted in `build_models.ps1`. Their wheels may be worth keying.

## Battles: intelligent multi-unit fights

### Task description

Make fights between groups outdoors, along an escort route (`DESIGN.md`): waves of minions and grinners advance, meet and fight, with the knight among them. Units pick targets sensibly, hold formation, surround without stacking, and retreat or regroup when losing. Keep it cheap enough for 40 units at 60 fps, for example with staggered thinking and simple avoidance. Record a scripted battle and measure its CPU time.

### Open questions

- None: `DESIGN.md` settles the sides, the waves' periodic spawning and the clock ending a run.

### Status

Not started. Needs the minion's animation. Grinners fight the knight (fighters carry `Health`, `Hurtbox`, `Strike`), but stand still while their attacks recharge, and their cost at 40 units is unmeasured.

## Combat: tuning from the dev's playtest

### Task description

The grinners and the knight now fight outdoors (`scripts/grinner.gd`, `player.gd`; numbers in the report of commit "Enemy: grinners fight"). Playtest with the dev and tune: the waddle's 0.29 m/s barely closes on her, the swipe has no clear wind-up, ichor and sparks are specks from the game camera, unaimed attacks follow her facing, and corpses stay. Re-key the waddle or add a run in `tools/grinner` if needed.

### Open questions

- Should grinners run at her, or stay slow and dangerous only in numbers?
- Do corpses fade, sink or stay?

### Status

Not started. Needs the dev's playtest. Also watch Heavy_Combo's overhead swing: at frame 34 her right pauldron lifts about 48 mm for one frame to clear her chest, which may read as a flick.

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

Fix what her speech work found but left. A pale streak runs down the skirt's side in Godot: its lighting and normal buffers show wrong normals along the panels' side seam, likely the baked normal map's tangent frame against the exported tangents in `tools/sculpt/bake.py`. A bright square shows by one outer eye corner. The palm's edge creases, probably because the arm's lattice is half the palm's thickness (`body.arm_boxes`); recheck the clasp after. A fully overhead raise bulks the sleeve (`rig.py` weights).

### Open questions

- The dark tick at each outer lid corner is the lash paint running into the corner's crack, which the sleeping lid's raised ends carry. Taper the lash band before the crack, or give the lids unpainted wood?

### Status

Deprioritized: her face and skirt will be remodelled, which may remove these. Evidence in the speech branch's `dev/shots/speech/diag_*` and `dbg_*`.

## Rosalyn: a moving mouth

### Task description

Try two ways for Rosalyn's wooden mouth to move with her speech, where no wood visibly bends. First, lips that part: a jaw bone turns a few degrees, opening the lip parting onto the dark pocket behind it, moving the skin about a millimetre. Second, stop-motion style shapes: a few rigid lacquered lip pieces, swapped or pivoted. Time both to her voice. Deliver both in motion, with sound, beside her still-mouthed speech: close-up videos from Godot's movie writer and a playable scene that switches between the three. The dev picks; if neither works, she keeps the still mouth.

### Open questions

None. Try both: four or five shapes as swapped meshes, and the same shapes as pieces on pivots.

### Status

Deprioritized: waits for the change to her model, which may affect it; a first attempt is on branch `worktree-agent-a657b3d97045922cc`. Speech is built: four 12 s clips (Tell, Ask, Muse, Insist) crossed by her AnimationTree, `Rosalyn.say()` with subtitles, brows as decals on brow bones and `scripts/gaze.gd` turning her head to the knight; she speaks in the hall, T saying her next line. No voice files yet, so a real voice stream is untested.

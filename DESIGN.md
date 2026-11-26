# Design

Changes only at the dev's behest.

## The game

A roguelite. The workshop and hall are the safe hub, where the meta loop happens between runs. Enemies appear only outdoors, in runs.

## A run

- A run is an attack-only escort, as in Overwatch: the knight and her side push a payload through grinner country.
- It has about four escort rounds of 5 to 12 minutes, each in its own area. The party does not go back to the workshop between areas.
- The clock ends a run. Sloppy play is punished with lost time.
- The end of each round offers an extra-powerful item choice.

## Sides

- Hers: the knight, whom the player controls; her retinue of three, the allies who are not minions; and minion waves.
- Theirs: four grinner captains and grinner waves.
- Minions spawn periodically and cannot be controlled.
- The retinue are resurrected when they fall.
- Teamfights shift as they go, as in Overwatch or League of Legends: some fighters retreat while others escort them to safety, and the team's goal changes as the fight evolves. The retinue's own intelligence makes this, and the knight is always controlled apart from them.

## Commanding the retinue

- She has four modes: fall back, target, with me, and autopilot (a name still to settle).
- A mode lasts until she sets autopilot. Target also returns to autopilot when its target dies, and a wipe of the retinue or of the captains returns any mode to autopilot.
- A mode changes the retinue's weighing, not their roles: each still chooses its own part in it.

## Growth in a run

- XP is shared and earned during a round. The team levels up together, during rounds, and the level-up is the unit of a run's progression.
- At each level-up she chooses, roguelite-style, an item for herself and an upgrade for her minions. These are her only build choices in a run. The choice waits until she is ready, and choosing pauses the game.
- At each level-up she and each retainer gain attribute points, rolled from the allocations set in the meta loop, and each retainer ranks its skills in the order set there.
- Her skills, basic attacks included, come only from items. The retinue never take items: they grow only in attributes, which modify derived stats, and in skills.
- Each area has two kinds of side objective: sequestered enemies, which give XP, and caches only she can see, born of the magic that is the source of her power.
- Deaths do not feed the captains.

## The meta loop

- Meta currency introduces run upgrades to the pool and upgrades them.
- For the knight and each retainer, the player sets an attribute allocation: a quantity of points to spread, not a ratio or percentage, which each level-up rolls as a probability distribution. For each retainer the player also sets a skill order.
- Damage dealers allocate toward two to four damage multipliers, supports toward utility, and tanks toward defences. Kits reward a mix, so that tanks and supports still want some damage, and damage dealers and supports some toughness.

## Balance

- Numbers derive from target curves, each with a few settings.
- The AI is hand-written rather than learnt, and reasons in quantities derived from the current stats, so that balance changes do not mean retraining it.
- Balance is tested in layers: an analytic model, then a headless simulation of the real game with a bot playing the knight, then human playtests.
- Outdoors holds about 12 grinners on screen and 40 units in all.

## Open

- The story of the clock.
- The autopilot mode's name.
- Where XP comes from besides the sequestered enemies, given that XP for captain kills invites farming.
- What the caches hold.
- How kits make a mix of attributes pay.
- How the areas join without the workshop.
- Whether any of her moves, such as the roll, are hers without items.

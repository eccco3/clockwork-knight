Immutable without dev's permission. If you notice a change, no need to notify the dev — assume they authored it.

## The game

A roguelite. The workshop and hall are the safe hub, where the meta loop happens between runs. Enemies appear only outdoors, in runs.

## A run

- A run is an attack-only escort, as in Overwatch: the knight and her side push a payload through grinner country.
- It has about four escort rounds of 5 to 12 minutes, each in its own area. The party does not go back to the workshop between areas: a short interlude joins each pair, where she chooses the next area from two or three, each showing what it offers.
- The clock ends a run. Each area has its own clock: her reserve, which is magical, running down. What the reserve is waits for the lore. Sloppy play is punished with lost time.
- The player can abandon a run and keep the meta currency it has earned.
- The end of each round offers an extra-powerful item choice.
- Fog covers only one area.

## Sides

- Hers: the knight, whom the player controls; her retinue of three, the allies who are not minions; and minion waves.
- Theirs: four grinner captains and grinner waves.
- Minions spawn periodically and cannot be controlled.
- The retinue are resurrected when they fall, during an area's fight too. Resurrection costs no time.
- Teamfights shift as they go, as in Overwatch or League of Legends: some fighters retreat while others escort them to safety, and the team's goal changes as the fight evolves. The retinue's own intelligence makes this, and the knight is always controlled apart from them.

## Commanding the retinue

- She has four modes: fall back, target, with me, and at will.
- A mode lasts until she sets at will. Target also returns to at will when its target dies, and a wipe of the retinue or of the captains returns any mode to at will.
- A mode changes the retinue's weighing, not their roles: each still chooses its own part in it.

## Growth in a run

- XP is shared, and earned per metre of the payload's progress and from side objectives. The team levels up together, during rounds, and the level-up is the unit of a run's progression.
- The team's experience gain is the sum of its members'.
- At each level-up she chooses, roguelite-style, an item for herself and an upgrade for her minions. These are her only build choices in a run. The choice waits until she is ready, and choosing pauses the game.
- At each level-up she and each retainer gain attribute points, rolled from the allocations set in the meta loop, and each retainer ranks its skills in the order set there.
- Each area has two kinds of side objective: sequestered enemies, which give XP, and caches only she can see, born of the magic that is the source of her power.
- Side objectives cost progress in their area but pay off in later ones. Whether to attempt them should be a real trade-off, depending partly on whether her build and retinue lean to the early or the late game, as early-game champions take dragons in League of Legends.
- A captain's death gives the clockwork resource, scaled by her share of the damage it took, and capped per area so that farming stops paying quickly. Kills give no XP of their own.
- Deaths do not feed the captains.

## Her items

- She walks and runs without items. Everything else she does, basic attacks included, comes from items, which also give derived stats.
- She has five equipment slots: two hands, a head, an upper armour, a lower armour and feet.
  - The hands hold her main offensive abilities.
  - The head and upper armour hold auxiliary abilities: offensive, defensive or utility.
  - The lower armour and feet hold movement abilities, mainly variations of the jump and the dodge roll.
- Her current moves and animations were trials of what can be made, and the game's will differ. Attack speed and movement speed have soft ceilings, and some animation cancelling is acceptable.
- Items have rarities, and offers scale with the level they are found at, so a kept item falls behind unless enchanted.
- Each offer is three items of the same rarity. Accepting one loses the other two.
- She can dismantle an offered item into a clockwork resource, and declining a better offer gives more of it. The resource enchants an item to a higher rarity, which rolls something new for that item.
- Most of the time she should accept the offer, but keeping a favoured piece stays possible. One rarity step of enchanting costs about what two declined offers of that rarity give, and a bot that always takes the better item should accept about 75 to 85% of offers.
- The retinue never take items: they grow only in attributes and skills.

## Attributes

- Attributes modify derived stats, and derived stats multiply one another. Abilities scale from derived stats, several each.
- Diminishing returns come implicitly, from the rising opportunity cost of stacking one attribute. Explicit diminishing returns per attribute are not ruled out, nor committed to.
- Critical chance is scaled so that its cap is rarely reached.
- Strength never improves pure magic builds.
- The attributes, for now:
  - Strength: physical damage, physical critical damage, attack speed (less than dexterity gives) and physical resistance.
  - Endurance: tenacity against crowd control, stamina recovery, maximum stamina and health regeneration.
  - Constitution: health.
  - Dexterity: attack speed, movement speed and critical chance (less than luck gives).
  - Intelligence: magic damage, magic resistance and experience gain (less than luck gives).
  - Luck: critical chance and experience gain.
- Physical damage comes first. Magic's own multipliers wait, perhaps mana, separate from stamina, which only some skills spend (mostly but not only magic ones) and which many magic skills multiply by.

## The meta loop

- Meta currency introduces run upgrades to the pool and upgrades them.
- For the knight and each retainer, the player sets an attribute allocation: a quantity of points to spread, not a ratio or percentage, which each level-up rolls as a probability distribution. For each retainer the player also sets a skill order.
- Damage dealers allocate toward two to four damage multipliers, supports toward utility, and tanks toward defences. Kits reward a mix, so that tanks and supports still want some damage, and damage dealers and supports some toughness.

## Balance

- Numbers derive from target curves, each with a few settings.
- The retinue's and captains' AI is hand-written rather than learnt, and reasons in quantities derived from the current stats, so that balance changes do not mean retraining it.
- Balance is tested in layers: an analytic model, then a headless simulation of the real game with a bot playing the knight, then human playtests.
- The bot playing the knight is measured against the dev's own play, and the gap between them is tracked. It may learn by reinforcement, given up if that becomes too much hassle, so the simulation keeps a clean interface for observing and acting, and steps fast headless.
- Outdoors holds about 12 grinners on screen and 40 units in all.

## Open

- How fast healing is, between League of Legends and Overwatch 2.
- What the caches hold, and the clockwork resource's name.
- How kits make a mix of attributes pay.

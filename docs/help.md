# Hero Companion — User Guide

Hero Companion is a fan-made build planner for City of Heroes: Homecoming. It plans,
optimizes, and walks you through character builds using the game's actual math — to-hit,
resistance, defense, endurance, recharge — not templates or guesswork. It runs entirely
on your own computer, next to (never inside) the game.

## Quick Start

Open the app and pick one of the entry cards:

- **Build a new level 50** — you choose archetype, powersets, the content you'll run,
  and your role on a team; the optimizer designs a complete end-game build with
  enhancement slotting.
- **Start from scratch (level 1)** — same choices, but you get a level-by-level
  leveling companion that walks every pick and slot from 1 to 50.
- **Import from Mids Reborn** — paste a Mids build (or load a .mbd file) and the tool
  evaluates it, then can optimize from there.
- **Import a character you play** — type `/build_save_file` in game, then click
  "Find my characters for me": the tool locates your Homecoming saves itself and
  imports the one you pick. (Unusual install location? Tell it your game folder
  once and it remembers.)

Everything is reversible. Nothing you click is permanent, and in-game a /respec
rewrites any character anyway.

## The Build Panel

Pick your archetype, primary, and secondary. The panel fills with your powers; click a
power to add or remove it, and use the slot controls to place enhancement slots
(the game grants 67 placeable slots across a career; the tool enforces the real limits).

The stat panel updates live: defense by position, resistance by type, recharge,
recovery, damage. Caps are shown — defense soft cap 45%, resistance cap by archetype.

## Reading the Numbers

Every stat is drawn as a bar, and each bar tells you three things at once.

- **The filled portion** is what your build actually has right now.
- **The marked line** is the number that matters for that stat: 45% for defense
  (the soft cap, where most incoming attacks start missing), or your archetype's
  resistance cap, which is 90% for Tankers and Brutes, 85% for Kheldians and the
  Arachnos archetypes, and 75% for everyone else. Past that line the game stops
  counting, so points spent beyond it are wasted.
- **The number itself**, so you never have to estimate from the picture.

Two things on the bars are worth knowing about, because they surprise people:

**"⚔ N%" on a defense row.** Some defense (anything from a Hide-style power)
switches off the moment you attack. When that applies, the row shows both numbers:
the resting one, and the in-combat one after the drop. The in-combat figure is the
one to plan around, because that is what you have when it matters.

**Achieved vs target.** After a solve you get a list comparing what you asked for
against what the build reached. A row that fell short is not the tool failing
quietly — it will also tell you which unpicked powers on your character would help
and roughly how much each would add. If nothing on your character supplies that
stat, it says so plainly, because a goal you cannot reach is worth knowing about
rather than chasing.

**How pet damage is counted.** Pets and henchmen are scored with their real
chance to hit, at their own level — not yours. The game summons lower-tier
henchmen below your level (at full strength, tier 1 fights two levels down,
tier 2 one, tier 3 at your level), so against high-level enemies they miss
more, and the tool counts that honestly instead of pretending every pet always
hits. It also counts what buys the accuracy back: ToHit buffs that reach your
pets (the Mastermind's own Supremacy, Tactics) and accuracy slotted in the
summon power itself. That is why those choices visibly raise pet damage here,
just as they do in the game.

**Hamidon Origins.** A Hamidon Origin enhancement carries two or three aspects
in one slot — accuracy and damage together, or resistance and endurance — which
is more raw enhancement per slot than any set piece. The price is that HOs earn
no set bonuses, and they come from endgame play: Hamidon raids, or merit
conversion. For endgame content (incarnate trials and farms) the optimizer may
propose them where they genuinely beat a set piece, and every HO it places says
where it comes from. You can slot them by hand anywhere, for any content.

## Content and Role

These two dropdowns are the most important choice in the tool:

- **Content** — what you actually run: general play, task forces, incarnate trials,
  fire farms, PvP. It sets what the build must survive and deliver.
- **Role** — what you're there to do: damage, tank, buff/debuff support, control,
  healing. The optimizer maximizes your role output, not a generic score.

A support character is scored on how much its debuffs and buffs actually change fights
(magnitude times uptime), not on its own survival. That's deliberate: the tool builds
characters that are noticed as contributors.

## The Optimizer

The "Optimize" actions run a real search over powers, pools, and slotting:

- It explores every legal add, drop, and swap — including all power pools — and runs
  until no single change improves the build (with honest certificates saying so).
- It respects the game's rules: pool limits (four max), the origin-pool rule (only one
  of Sorcery / Experimentation / Force of Will / Gadgetry / Utility Belt), archetype
  set access, prerequisite tiers, and level availability.
- It learns: strong past results seed future searches as champions.

If a suggestion looks odd, it earned its place in the math — but you always have the
final say. Swap anything; the tool re-evaluates around your choices.

## Locking a Power

Every power card has a padlock: 🔓 open means the optimizer may change it, 🔒 closed
means hands off.

A lock is absolute. A locked power comes out of a re-solve **exactly** as you left
it, down to the individual enhancements. Everything unlocked is re-slotted toward
your goal around it.

Use it when you have already decided something and want the tool to work with that
decision rather than argue with it. Common cases: you have expensive sets already
slotted in game and do not want a plan that assumes you will re-buy them; you have
a favourite proc in a particular power; or you are exploring "what would change if
this part stayed fixed".

Two consequences worth knowing before you lock:

- **An empty slot inside a locked power stays empty.** The lock means untouched,
  not "untouched except the gaps". The tool will tell you when that has happened
  rather than quietly leaving holes.
- **Locking constrains the result.** A locked power that is slotted poorly limits
  how good the rest can be, and the solve is being honest when it comes back lower.
  If a target suddenly cannot be reached, your locks are the first thing to check.

Locks are saved with the character, so resuming later finds everything exactly as
you left it.

If you want most of a build kept rather than specific powers, use **Preserve my IO
sets** instead: that keeps the sets you have already invested in and only re-slots
generic enhancements and empty slots. Locks are the scalpel; preserve is the broad
stroke.

## Leveling from 1 to 50

For from-scratch characters, the leveling walk shows exactly what happens at every
level on the real Homecoming schedule: a power on even levels, slots on odd levels,
pools at 4, epics at 35, respec trials at 24/34/44, and cost-smart enhancement advice
for each stretch (cheap early, common IOs from 7, sets near the end).

You can take every suggestion or none of them. The walk tracks where you've deviated
and offers to re-fit the end-game around your actual choices.

### Kheldians (Peacebringer / Warshade)

Kheldians follow their own rules and the tool knows it: inherent flight from level 1
(no travel pool needed unless you want one), Nova and Dwarf forms inside your own
power sets, and no epic pool at all — the walk and the wizard both reflect that.

### Arachnos Soldiers and Widows

VEATs live a two-phase career and the walk follows it honestly:

- **Levels 1–23**: only your base sets (Arachnos Soldier / Training and Gadgets, or
  Widow Training / Teamwork) — branch powers can't be taken yet, so the walk never
  suggests them.
- **Level 24**: the mandatory respec. You choose your branch — Crab or Bane, Night
  Widow or Fortunata — and re-place every pick from level 1 with all six sets open.
  The walk hands you the complete re-place order right at this step.
- **Levels 24–50**: the walk continues from the respec order, branch powers included.

## Enhancement Converter and Haul Appraiser

The Converter panel answers two questions:

- **"How do I get this IO cheaply?"** — a concrete cheapest path per enhancement:
  which piece to buy or craft, which converters to use, and the converter/merit cost.
  One rule of the game worth knowing: conversions can't jump from cheap pools into
  purples — the tool's paths never pretend otherwise.
- **"Is this drop worth anything?"** — paste your drops (recipes included, straight
  from the game). Each item gets a verdict: keep for your build, craft-then-convert
  for profit, or just sell.

## Saving, Importing, Exporting

- **Save** keeps the character's plan and leveling progress locally so you can resume.
  Auto-save runs in the background.
- **Import/Export** is Mids Reborn compatible — bring builds in, take builds out. Your
  builds are yours; nothing leaves your machine.

## Your alignment

The alignment button in the banner shows your current alignment. Click it and you
get all four: **🦸 Hero**, **🛡️ Vigilante**, **😈 Rogue**, **🦹 Villain**. It
reskins the whole app, and your choice is remembered.

The two middle alignments are not a third side. A Vigilante levels in Paragon City
like a hero and can also visit villain content; a Rogue levels in the Rogue Isles
like a villain and can also visit hero content. That is how the game works, and it
is why they are shown in gold rather than blue or red.

**Your build scores the same either way.** The game counts a Vigilante as
hero-side and a Rogue as villain-side, so Hero and Vigilante give identical
numbers, and so do Villain and Rogue. Changing alignment changes what you *see*,
never what your build is worth.

**Moving between the hero pair and the villain pair can shift your totals
slightly.** Accolades are alignment-specific in game, and the app assumes the
standard set for your side, so a villain build should not be counting Freedom
Phalanx Reserve. Accolades carry real stats, so the numbers move a little. That is
correct behaviour, not a glitch.

**Nothing you ticked is ever thrown away.** An accolade for the other side stays
remembered, greys out, and counts as zero while you are on this side — the game
gates it the same way, so a held off-side accolade does nothing until you switch
back. Switch back and it counts again. Powers, slotting and targets are never
touched by any of this.

**A separate control, easy to confuse with this one:** the Leveling Journey has its
own alignment switch, which additionally offers 🌀 Flashback. That one is a
**preview** of somebody else's route through the game, so you can see where a
villain would level. It changes nothing about your character and resets when you
close the Journey.

## Bugs, Champions, and Updates

Hero Companion is a living tool, and you're part of how it improves. Three buttons,
all strictly opt-in — the app never sends anything on its own:

- **🐞 Report a bug** — opens a pre-filled bug report on the project's GitHub page
  with your app, model, and game-data versions already included (that's usually the
  hard part of a good bug report). Add what happened and post it. Nothing is sent
  until you click submit on GitHub itself.
- **🏆 Submit champion** — think your current build beats the shipped champion for its
  archetype and role? This saves your build as a *champion candidate* file and opens
  the submission queue. The development hub re-scores every candidate with its own
  math — if your build genuinely wins, it becomes the new shipped champion in a future
  update, with credit to you.
- **check for updates** (bottom of the page) — compares your version against the
  latest release on GitHub. On first run the app asks once whether to do this
  check automatically at startup (it contacts github.com to compare version
  numbers and sends nothing else); say yes and new releases greet you with an
  "Update now / Remind me later" banner. Say no and the footer button is the
  only check that ever runs. Updates are never downloaded or installed for you.

A few words the tool uses precisely: a **champion** is the best certified build for an
archetype + powersets + role combination — champions ship with the app and give the
optimizer its head start. A **candidate** is your claim to beat one. The **model
version** (v23 today) stamps which generation of the scoring physics produced a
number, and the **data version** stamps which game database it was computed against —
so scores are always compared apples to apples.

## Frequently Asked

**The tool and the game disagree — who's right?** The game, always. The tool's model is
verified against the Homecoming Wiki and City of Data, but patches happen. When you
find a disagreement, that's a bug worth reporting.

**Why won't it give me a second origin pool / a branch power at level 10 / an epic on
my Peacebringer?** Because the game won't allow it. The tool only suggests choices that
exist for your character at that level.

**Does it play the game for me?** No. It never touches the game client or servers.
It's a planner you read while you play.

**Is it free?** Free and noncommercial, forever (CC BY-NC-SA 4.0). See the Terms of
Use, License, and Credits links at the bottom of the app.

## Credits

Built on the work of the City of Heroes community: NCSoft (the game, all rights
theirs), Homecoming Servers — whose game client this tool now reads its data directly
from — Mids Reborn (the build planner it was built on, and stays `.mbd` import/export
compatible with), the Unofficial Homecoming Wiki, City of Data v2, the Homecoming Forums, the
Paragon Wiki Archive — Guyver [SoV] of the Sovereign supergroup, whose openly
shared master builds were the standard this tool's optimizer had to honestly beat —
and Maelwys, whose expert forum reviews caught what our own tests missed, round
after round.

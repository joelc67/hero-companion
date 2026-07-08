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

## Hero or Villain

The alignment button in the banner reskins the whole app — Hero Companion in blue,
Villain Companion in red. Pure style; your choice is remembered.

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
theirs), Homecoming Servers, Mids Reborn (all game data, parsed from your own
install), the Unofficial Homecoming Wiki, City of Data v2, the Homecoming Forums, the
Paragon Wiki Archive — Guyver [SoV] of the Sovereign supergroup, whose openly
shared master builds were the standard this tool's optimizer had to honestly beat —
and Maelwys, whose expert forum reviews caught what our own tests missed, round
after round.

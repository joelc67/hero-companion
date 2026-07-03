# CoH Build Planner (Homecoming) with AI Assistant

A local, offline web app for City of Heroes (Homecoming) character build planning.
Game data comes from **Mids Reborn**; the AI layer is **Claude Code running
locally**.

## Quick start (Windows 11)

```
install.bat      :: installs Flask deps (one time)
start.bat        :: launches the server and opens http://localhost:5000
```

The app runs fully offline. Only the AI Assistant panel needs Claude Code active.

## Features

- **Slot enforcement** — clicking a slot shows ONLY enhancement sets whose category
  fits that power (a power's accepted categories and a set's category both index
  the same `TypeGrades.json` table).
- **Live stat engine** — real Defense / Resistance / Recharge / Recovery / etc.,
  computed like Mids: base magnitude (`Scale × AttribMod[level 49][archetype
  column]`) × slotted enhancement value (`MultIO`) with **Enhancement
  Diversification** (schedules A–D), summed over active powers + set bonuses.
  Resistance uses the archetype's real hard cap (Tanker/Brute 90 %, Khelds /
  Arachnos 85 %, rest 75 %); Defense's 45 % is a soft cap and shows overcap.
- **Per-power "include in totals"** — each power has a checkbox (on by default for
  toggles/autos, off for click powers). Opt click buffs like Hasten in, or opt a
  toggle you don't run out.
- **Incarnates** — pick one of each of the 7 slots (Alpha … Genesis). Fed to the
  AI and the export. (Incarnate buffs are not summed into the passive totals —
  their values are peak/timed.)
- **"Build this for me"** — describe a goal; Claude generates a full build
  (powers, slot counts, IO sets/pieces, incarnates). The backend resolves every
  name to real data and validates each enhancement against the power's
  categories, then the builder auto-fills. Takes ~2–4 minutes (local generation).
- **Export to Mids Reborn** — downloads a `.mbd` file that Mids opens via
  File → Open (incarnates included). Use Mids' "View Totals" as the authoritative
  cross-check.

## AI Assistant setup (one time)

The AI uses your local Claude Code. If the panel says "not logged in for headless
use," generate a token and store it:

```
claude setup-token                          :: complete the browser sign-in, copy the token
setx CLAUDE_CODE_OAUTH_TOKEN "<token>"      :: persists it (uses your subscription)
```

Then relaunch via the shortcut. `start.bat` reads the token from the registry at
launch (so a stale Explorer environment doesn't matter) and locates the bundled
`claude.exe` automatically. No separate API billing is needed.

## How the data was produced (Step 1 — verified, not assumed)

The Mids Reborn `.mhd` files are **.NET `BinaryWriter` output**, not JSON:

- strings = LEB128 7-bit length prefix + UTF-8
- numbers = little-endian int32 / int64 / float32; bool = 1 byte
- array idiom: a count `N` is written, then `N+1` elements follow

`tools/parse_mids.py` re-implements a .NET `BinaryReader` and transcribes the
field order **1:1 from the MidsReborn C# reader constructors** (`DatabaseAPI.cs`,
`Power.cs`, `Effect.cs`, `Archetype.cs`, `Powerset.cs`, `Enhancement.cs`,
`EnhancementSet.cs`). Re-run it with:

```
python tools/parse_mids.py
```

It reads `MidsReborn/MidsReborn/Databases/Homecoming/` and writes `data/*.json`.
Override the source with the `MIDS_DB_DIR` env var.

### The slot-enforcement linchpin

Each **Power** stores a list of accepted set-category ids; each **EnhancementSet**
stores one set-category id. **Both index into the same `TypeGrades.json` SetTypes
table** (7 = "Defense Sets", 8 = "Resist Damage", …). Matching them is exactly the
rule "only show sets whose category fits this power." The UI calls
`POST /sets/for-power` with a power's accepted category ids and receives only the
sets that match — invalid sets are never sent to the client.

### Data files (`data/`)

| File | Contents |
|------|----------|
| `archetypes.json` | 15 playable ATs + caps (HP, res, recharge, damage) + AttribMod `column` |
| `powersets.json` | primary / secondary / **epic** (resolved via `Requires.ClassName`) per AT, plus shared pools |
| `powers.json` | per power: accepted categories/types, slot defaults, and **`self_effects`** (scale + modifier table + ED schedule for the stat engine) |
| `enhancement_sets.json` | 227 sets: pieces (what each enhances + **`boosts`** = per-aspect enh value), set bonuses with numeric effects |
| `set_bonuses.json` | per-set bonus thresholds with resolved numeric stat effects |
| `incarnates.json` | the 7 incarnate slots and their choices |
| `common_ios.json` | single-aspect Invention IOs (uid + boosts) for generic slotting |
| `modifier_tables.json` | `AttribMod` table rows at level 49 (base-magnitude lookup) |
| `maths.json` | `MultIO` (enhancement values per level) and `MultED` (ED thresholds) from `Maths.mhd` |
| `set_categories.json` | the category and enhancement-class lookup tables |

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /archetypes` | playable archetypes |
| `GET /powersets/<archetype>` | primary, secondary, epic, pools |
| `GET /powers/<powerset_full_name>` | powers with accepted categories/types |
| `GET /sets/<category>` | all sets in a category (id / short / name) |
| `POST /sets/for-power` | **slot enforcement** — only sets matching a power |
| `GET /setbonuses/<setname>` | a set's pieces and bonuses |
| `GET /incarnates` | the 7 incarnate slots and choices |
| `POST /build/validate` | category mismatches, unique dupes, dup pieces |
| `POST /build/calculate` | full defense/resistance/recharge/etc. vs caps |
| `POST /build/export` | a Mids Reborn `.mbd` for the current build |
| `POST /ai/query` | sends build state + question to Claude Code |
| `POST /ai/generate-build` | "Build this for me" — structured build, resolved + validated |

## What the calculator computes (scope & honesty)

Totals = **active-power self-buffs** (base magnitude from the `AttribMod` tables ×
slotted enhancement value with Enhancement Diversification) **+ set bonuses**.
Verified against known values: Weave 5 %, Combat Jumping 2.5 %, Tanker Tough 15 %
S/L resist, Tough + 3 resist IOs = 23.77 % (ED-correct), Hasten +70 % recharge.
Set bonuses also match Mids (LotG 2pc +10 % Regen, 5pc +3.75 % S/L resist).

The validator hardcodes: Defense soft cap **45 %** (exceedable), resistance hard
cap **per archetype** (90 / 85 / 75), rule of five, unique-enhancement limit
(LotG Def/Global Recharge treated as non-unique), and the full ED schedules
(A–D) in `engine.apply_ed_sched`.

**Not auto-included:** click buffs are off by default (toggle them on per power);
**incarnate** buffs are excluded entirely because their values are peak/timed
(e.g. Barrier starts at +57.5 % defense and decays). Cross-check any build with
Mids' "View Totals" after exporting.

## AI Assistant

`ai/claude_bridge.py` formats a structured prompt (archetype, powersets, every
power with its slotted enhancements, set-bonus totals vs caps, open slots and
their available categories, and the question) and invokes the local Claude Code
CLI headless (`claude -p`). The CLI is auto-detected on PATH or under
`%APPDATA%\Claude\claude-code\<version>\claude.exe`; override with `CLAUDE_BIN`.

> The headless CLI must be authenticated. If you see *"Not logged in"*, run
> `claude` once interactively and `/login` (or set `ANTHROPIC_API_KEY`).

## Project layout

```
coh-builder/
  data/                 generated JSON (output of parse_mids.py)
  server/
    server.py           Flask app + routes
    engine.py           validation + full stat calculation (AttribMod + ED + sets)
    ai_build.py         "Build this for me": prompt + resolve/validate structured build
    mids_export.py      build -> Mids Reborn .mbd
  ai/claude_bridge.py   Claude Code bridge (headless claude -p via stdin)
  static/               index.html, style.css, app.js (single-page app)
  tools/parse_mids.py   Mids .mhd/.json -> data JSON parser
  requirements.txt  install.bat  start.bat
```

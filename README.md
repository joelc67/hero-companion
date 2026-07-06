# Hero Companion

### [⬇ Download the latest version](https://github.com/joelc67/hero-companion/releases/latest) — run the installer or unzip the portable build. Free, no account.

**Your City of Heroes sidekick** — a free, offline companion for
[City of Heroes: Homecoming](https://homecomingservers.com) that designs, optimizes,
and levels character builds from the game's actual data, then keeps helping while
you play.

No templates. No cloud. A deterministic first-principles model of the game's combat
physics (to-hit, resistance, the purple patch, proc mechanics, debuff economics,
endurance, recharge) drives a real optimizer that searches powers, pools, and
enhancement slotting until no single change can improve the build — and says so
honestly.

**The data comes from the game itself.** Archetype scalars, power values, set
bonuses, proc rates, converter costs, and critter tables are extracted from the
current game client and continuously reality-checked against it, so the tool can't
quietly drift six months behind a patch.

## What it does today

- **Build a level 50** — pick archetype, powersets, the content you run, and your
  team role; get a complete end-game build with IO-set slotting, verified against
  the game's caps and rules, with plain-language tags explaining *why* each power
  is slotted the way it is (full set, proc hybrid, global mules).
- **Level from 1 to 50** — a per-level walk of the real Homecoming schedule: every
  power pick, every slot, cost-smart enhancement advice, respec trials — including
  the Arachnos Soldier/Widow two-phase career and Kheldian rules.
- **Plan a respec, then work it** — resuming an older character offers a respec
  review: a before/after worksheet per power (old slotting struck through), a
  grocery list of what to craft and what to unslot and sell, checkboxes that
  persist across sessions until you mark the respec complete. It also notices when
  the *optimizer* has improved since your build was made and offers a fresh look.
- **Watch your play (opt-in)** — point it at the game's chat log and it turns your
  sessions into insight: drops appraised against your own build's shopping list
  ("keep — Fire Ball wants this"), influence and merit tallies, per-character
  stat cards across accounts. Everything stays on your machine; the app has no
  telemetry and phones home only when you click.
- **Appraise your drops** — keep / craft-then-convert / sell verdicts with concrete
  converter paths and costs, priced from the game's own conversion data.
- **Import/export Mids Reborn** — `.mbd` files round-trip; Mids' View Totals is the
  authoritative cross-check.
- **Champions** — the best certified build per context gives the optimizer its head
  start. Beat one, and the 🏆 button lets you submit yours.

## Where it's heading

The near-term roadmap, roughly in order:

- **Deeper slotting judgment** — proc-vs-set trades scored per attack, Hamidon
  Origin mixing, −resistance and Force Feedback proc valuation, and henchman damage
  modeled from the game's own critter tables so Mastermind builds are slotted for
  what the pets actually do.
- **In-game integration** — a generated Hero Companion popmenu (one click in-game
  to enable log capture; your respec shopping list as a right-click menu at the
  market). Everything opt-in, everything within Homecoming's modding rules — file
  overlays only, never memory reading or injection.
- **"Alert me when…"** — tray alerts from the live log: an iTrial forming, a Task
  Force recruiting, an event starting that you still need the badge for.
- **CoH Pulse Boards** — an opt-in community intel site: real market prices for a
  blind-bid economy, PvE scorecards (badges, days played, playstyle), League and
  Task Force run pages with leaders and participants, supergroup and coalition
  standings. Think killboards, but for the game we actually play. Every stat is
  individually opt-in and anonymous by default.
- **Companion Lite** — a tiny client whose only job is connecting your characters
  to the boards, for players who want the community layer without the planner.

## Quick start

**PC version (recommended):** run `HeroCompanion-Setup-<version>.exe` (installs,
adds shortcuts, updates in place) or unzip the portable build and run
`HeroCompanion.exe`. The app lives in your system tray — Open, Check for updates,
Quit. Saves live in `%APPDATA%\HeroCompanion`.

**From source (Windows):**

```
install.bat      :: one-time: installs Python deps
start.bat        :: launches the server and opens http://localhost:5000
```

**Build the executable:** `python -m PyInstaller HeroCompanion.spec` (onedir output
in `dist/HeroCompanion/`).

## Where the data comes from

Bulk game data is extracted directly from the installed game client's data files
with the community's open tooling ([Bin Crawler + Pigg
Wrangler](https://github.com/wednesdaywoe/CoH-Planner)) and reconciled by a suite
of reality-check scripts — see [tools/gamedata/README.md](tools/gamedata/README.md)
for the pipeline, the snapshots, and how to refresh after a game patch. Mids Reborn
remains the interchange format and the authoritative UI cross-check.

## Feedback and champions

- **🐞 Report a bug** (in-app) — opens a pre-filled GitHub issue with your app,
  model, and data versions. Nothing is ever sent without your click.
- **🏆 Submit champion** (in-app) — exports your build as a candidate file and opens
  the submission queue. Every candidate is re-scored deterministically before
  promotion; verified wins ship in the next update with credit to the builder.
- **Check for updates** (tray or footer) — compares your version against the latest
  GitHub release. Never automatic.

How all this fits together — including what the words *champion*, *candidate*,
*model version*, and *data pack* mean precisely — is in
[docs/architecture.md](docs/architecture.md).

## Documentation

- [In-app help + release notes (PDF)](static/help/HeroCompanion-Help.pdf) — also the
  ❓ Help button
- [CHANGELOG.md](CHANGELOG.md) — what's new
- [docs/architecture.md](docs/architecture.md) — distribution architecture + glossary
- [TERMS.md](TERMS.md) — terms of use
- [CREDITS.md](CREDITS.md) — the shoulders this stands on

## License

Original work (code, model, docs, UI): **CC BY-NC-SA 4.0** — free and noncommercial,
forever; modify and share under the same terms with credit. See [LICENSE](LICENSE).

*City of Heroes* and all game content © NCSoft Corporation. *City of Heroes:
Homecoming* operates under license from NCSoft. Game data extracted from the game
client with community tooling (see Credits); Mids Reborn is the interchange format.
This is an unofficial fan project — not affiliated with or endorsed by NCSoft,
Homecoming Servers LLC, or the Mids Reborn team.

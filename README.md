# Hero Companion

### [⬇ Download the latest version](https://github.com/joelc67/hero-companion/releases/latest) — unzip, run `HeroCompanion.exe`, done. Free, no account, no install.

**Your City of Heroes sidekick** — a free, offline build planner for
[City of Heroes: Homecoming](https://homecomingservers.com) that designs, optimizes,
and levels character builds from the game's actual math.

No templates. No AI. No cloud. A deterministic first-principles model of the game's
combat physics (to-hit, resistance, the purple patch, debuff economics, endurance,
recharge) drives a real optimizer that searches powers, pools, and enhancement
slotting until no single change can improve the build — and says so honestly.

## What it does

- **Build a level 50** — pick archetype, powersets, the content you run, and your
  team role; get a complete end-game build with IO-set slotting, verified against
  the game's caps and rules.
- **Level from 1 to 50** — a per-level walk of the real Homecoming schedule: every
  power pick, every slot, cost-smart enhancement advice, respec trials — including
  the Arachnos Soldier/Widow two-phase career (base sets → mandatory level-24
  respec → branch) and Kheldian rules (inherent flight, forms, no epic pool).
- **Appraise your drops** — paste recipes and enhancements from the game; get
  keep / craft-then-convert / sell verdicts with concrete converter paths and costs.
- **Import/export Mids Reborn** — `.mbd` files round-trip; Mids' View Totals is the
  authoritative cross-check.
- **Champions** — the best certified build per context ships with the app and gives
  the optimizer its head start. Beat one, and the 🏆 button lets you submit yours.

## Quick start

**PC version (recommended):** download the latest release, unzip, run
`HeroCompanion.exe`. The app opens in your browser; closing the console window
stops it. Saves live in `%APPDATA%\HeroCompanion`.

**From source (Windows):**

```
install.bat      :: one-time: installs Python deps
start.bat        :: launches the server and opens http://localhost:5000
```

Game data is parsed from a [Mids Reborn](https://midsreborn.com) installation
(`tools/parse_mids.py`); a parsed snapshot ships in `data/`.

**Build the executable:** `python -m PyInstaller HeroCompanion.spec` (onedir output
in `dist/HeroCompanion/`).

## Feedback and champions

- **🐞 Report a bug** (in-app) — opens a pre-filled GitHub issue with your app,
  model, and data versions. Nothing is ever sent without your click.
- **🏆 Submit champion** (in-app) — exports your build as a candidate file and opens
  the submission queue. Every candidate is re-scored deterministically by the
  maintainer's hub before promotion; verified wins ship in the next update with
  credit to the builder.
- **Check for updates** (footer) — compares your version against the latest GitHub
  release. Never automatic.

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
Homecoming* operates under license from NCSoft. Game data via the Mids Reborn
team's database compilation. This is an unofficial fan project — not affiliated
with or endorsed by NCSoft, Homecoming Servers LLC, or the Mids Reborn team.

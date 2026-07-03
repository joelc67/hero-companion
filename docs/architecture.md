# Hero Companion — Distribution Architecture

How the PC version, the feedback loop, the champion pipeline, and the online home fit
together. This is the reference for contributors and for future-us.

## The shape: hub and spoke

There is one **hub** (the maintainer's development version) and many **clients** (the
PC installs players run). The hub is where evolution happens; clients are complete,
self-sufficient planners.

```
   players' PCs (clients)                       the hub (dev version)
  ┌────────────────────────┐   bug reports     ┌──────────────────────────┐
  │ Hero Companion.exe     │ ────────────────▶ │ triage + fixes           │
  │  · solver + model      │   champion         │ deterministic re-scoring │
  │  · data snapshot       │   candidates       │ delusion sweeps          │
  │  · champions           │ ────────────────▶ │ champion promotion       │
  │  · NO AI               │                    │ AI-assisted evolution    │
  │                        │ ◀──────────────── │                          │
  └────────────────────────┘  releases + data  └──────────────────────────┘
                               packs (GitHub)
```

Two principles fall out of this shape:

1. **The client is AI-free.** Everything a player uses — the optimizer, the physics
   model, the leveling walk, the converter — is deterministic code. The AI's job is
   evolving the tool (triaging feedback, diagnosing model gaps, retraining champions),
   and that job lives at the hub only. No API keys, no accounts, no cost, no cloud.
2. **The client never phones home on its own.** Every outbound interaction — a bug
   report, a champion submission, an update check — is a user click that opens their
   browser at the project's GitHub home. Builds, saves, and logs stay on the player's
   machine.

## Nomenclature

The words this project uses, precisely:

- **Client** — a player's installed copy of Hero Companion (the PC executable). Fully
  offline-capable; contains the solver, model, data snapshot, and shipped champions.
- **Hub** — the maintainer's development version: the same codebase plus the learning
  stack, the master corpus, the sweep harness, and AI assistance. The only place
  champions are certified and releases are cut.
- **Model** (and **MODEL_VERSION**) — the first-principles encounter physics that
  scores builds (to-hit, resistance, purple patch, debuff economics, role output).
  Every scored artifact is stamped with the MODEL_VERSION that produced it, so scores
  from different model generations are never compared as equals.
- **Data snapshot** (and **DB version**) — the parsed game database (powers, sets,
  archetypes) derived from Mids Reborn's Homecoming database, stamped with its version
  (e.g. 2026.1.1242). Clients ship with one and can receive newer ones as data packs.
- **Champion** — a build that currently holds the top certified score for its context
  (archetype × powersets × role × content) at a given MODEL_VERSION. Champions ship
  with the client and seed the optimizer's warm starts.
- **Champion candidate** — a build a player believes beats the shipped champion,
  exported by the 🏆 button as a portable JSON bundle (build + versions + notes).
  A candidate is a *claim*, not a result.
- **Promotion** — what the hub does to a worthy candidate: re-score deterministically
  with the hub's own physics (client numbers are never trusted), sweep for delusions,
  and if it genuinely wins, crown it the new champion in the next data pack. Because
  the hub recomputes everything, a tampered candidate is harmless noise.
- **Master build** — a hand-crafted build by a top player, used as calibration
  evidence the optimizer must honestly beat. Masters are evidence, never prescriptions
  — and they are NOT redistributed; they stay in the hub's private corpus.
- **Lesson** — a persisted record of what an optimization run learned (what moved the
  score, what didn't), MODEL_VERSION-stamped, used to warm-start future runs.
- **Delusion sweep** — the hub's audit harness that runs every archetype × powerset
  combination through the real pipeline and flags mechanical absurdities (under-cap
  picks, endurance starvation, debuff blindness…). The tool's honesty insurance.
- **Data pack** — a versioned bundle of hot-readable JSONs (game data, champions,
  model constants) published between full releases, so a Homecoming patch can reach
  players without reinstalling.
- **Release** — a full versioned build of the executable (see VERSION / CHANGELOG.md),
  published on GitHub Releases.

## Where it lives online: GitHub

One repository is the project's entire online home. Each GitHub surface has a job:

| Surface | Role |
|---|---|
| **Repository (code)** | The source of truth. Public, CC BY-NC-SA 4.0. |
| **Releases** | The update channel: the packaged .exe per version, plus data packs. The in-app "check for updates" compares its VERSION against the latest release tag. |
| **Issues** | The bug database. The in-app 🐞 button opens a pre-filled issue (versions auto-included, build context attached). Labels triage into model / data / UI / export. |
| **Discussions** | The champion submission queue (a "Champion Builds" category). Players post their candidate JSON; the hub re-scores and replies with the verdict. Doubles as the community's build board — with public credit when a candidate is promoted. |

The client's pointers to all four live in `client_config.json` (shipped next to the
executable). Until the repository exists, the file holds a REPLACE-ME placeholder and
every phone-home button explains itself instead of firing.

What is deliberately NOT in the repository:

- `benchmarks/masters/` — other players' hand-made builds (theirs, not ours to publish).
- Player saves, logs, or any telemetry (none exists in phase 1).
- The AI bridge stays in the tree but ships disabled in clients (bring-your-own-key
  seam, off by default).

## The feedback loop, end to end

1. A player hits a bug → 🐞 opens a GitHub issue pre-filled with app/model/DB versions
   and their build context. They add words and post — nothing is sent silently.
2. A player beats a champion → 🏆 saves a champion-candidate JSON and opens the
   Discussions queue to post it.
3. The hub pulls issues + candidates, re-scores candidates deterministically, sweeps,
   fixes what the bugs teach, promotes what survives.
4. A release (code) or data pack (data/champions) goes up on GitHub Releases.
5. Players click "check for updates" (or just keep playing — nothing is forced),
   download, and the loop closes.

## Update channels

- **Code releases** — new executable, new features/fixes. Manual download in phase 1;
  an in-app downloader can come later.
- **Data packs** — powers/champions/model-constant JSONs. These are hot-readable
  (champions.json is already read per-request), so replacing the files is enough; no
  reinstall. This is how a Homecoming balance patch reaches players the same week.

## Phases

- **Phase 1 (this one)**: PyInstaller executable; 🐞 bug reports via prefilled GitHub
  Issues; 🏆 champion candidates via Discussions; manual update check against Releases;
  AI off in the client.
- **Phase 2**: opt-in, clearly-labeled telemetry (compact artifacts only — validator
  errors, sweep flags, champion diffs); in-app data-pack auto-update.
- **Phase 3**: hub-side automation (issue triage, candidate re-scoring, sweep-on-submit
  as CI).

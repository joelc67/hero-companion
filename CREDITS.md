# Credits & Knowledge Sources

Hero Companion stands on the work of the City of Heroes community. Every mechanic this
tool understands was learned from, or verified against, these sources:

## Game & License Holders
- **NCSoft Corporation** — City of Heroes and all its content: archetypes, powersets,
  powers, enhancements, and the world they live in. © NCSoft. All rights theirs.
- **Homecoming Servers** (https://homecomingservers.com) — the licensed, living home of
  City of Heroes since 2019, operating under official agreement with NCSoft since 2024.

## Data
- **The Homecoming game client** — the authoritative source. Hero Companion reads its
  game data directly from the client files installed on your own machine: powers,
  enhancement sets and their bonuses, archetype modifier tables, enhancement-converter
  costs, badges, and power icons all come from Homecoming's own bins and texture
  archives. That means the tool reflects the live game rather than a second-hand copy,
  and when the client disagrees with any other source, the client wins.
- **Mids Reborn** (https://midsreborn.com) — the community build planner Hero Companion
  was built on. The Mids Reborn team's Homecoming database was this tool's original
  data foundation, and it is why the numbers lined up on day one. The tool has since
  moved to pulling its data straight from the game client (above), but it started here —
  and `.mbd` export/import compatibility with Mids Reborn is intentional and gratefully
  kept, so builds move freely between the two.

## Knowledge & Verification
- **Unofficial Homecoming Wiki** (https://homecoming.wiki) — the mechanics reference
  this tool's physics model was built and verified against: attack mechanics,
  resistance, the purple patch, archvillain resistance, protection tables, enhancement
  converter rules, archetype pages, and more.
- **City of Data v2** (https://cod.uberguy.net) — UberGuy's machine-extracted Homecoming
  power database; the authority used for per-power enhancement rules, pet enhancement
  pass-through, and effect semantics.
- **Homecoming Forums** (https://forums.homecomingservers.com) — the community whose
  guides, testing, and patch notes settled countless mechanics questions.
- **Paragon Wiki Archive** (https://archive.paragonwiki.com) — the preserved record of
  the original game, for historical rules and where Homecoming diverges from live.

## The Master Builder
- **Guyver [SoV]** of the **Sovereign** supergroup — the hand-crafted master builds he
  shares openly with the community were this tool's calibration standard: the bar the
  optimizer was required to beat honestly, and the reality check that exposed a dozen
  flaws in its math along the way. Never copied, always learned from. Sovereign's
  reputation for skill and generosity is well earned.

## The Reviewer
- **Maelwys** (https://forums.homecomingservers.com/profile/30623-maelwys/) — whose
  public expert reviews on the Homecoming forums, round after round, caught what our
  own tests missed: proc and Hamidon Origin mechanics, slotting quality, slot budgets,
  and display accuracy. Many of this tool's fixes exist because Maelwys took the time
  to generate builds, compare them against the real game, and write up exactly what
  was wrong. Feedback of that quality is a gift.

## The Guide Writer
- **Gulbasaur** — author of *The Good Missions Guide: a heroic levelling journey through
  story arcs* (https://forums.homecomingservers.com/topic/13961-the-good-missions-guide-a-heroic-levelling-journey-through-story-arcs/)
  and *The Mean Missions Guide: a villainous levelling journey through story arcs*
  (https://forums.homecomingservers.com/topic/21898-the-mean-missions-guide-a-villainous-levelling-journey-through-story-arcs/).
  The Leveling Journey's story layer — which contacts to see, in which order, in which
  zone, and where to pause your XP so a story arc doesn't slip out from under you — is
  his work, condensed. The game will tell you where you're *allowed* to go; Gulbasaur
  wrote down where it's worth going, and why. That judgement is not in any data file
  we could parse.

## Bundled Software
- **driver.js** by **Kamran Ahmed** (https://driverjs.com) — MIT licensed, vendored at
  version 1.8.0 in `static/vendor/`, with its licence alongside it. It draws the
  spotlight and the explanation card in the app's guided tour, and it handles the
  fiddly parts of that job: placing a card so it never runs off the screen, scrolling
  the right control into view, and keeping the highlight aligned when the window
  changes size. We wrote our own version of this first and it was worse; the honest
  thing is to say so and credit the person who did it properly. No network is involved
  — the copy in this app is local and the tour works fully offline.
- **Anton**, designed by **Vernon Adams** and maintained by the Anton Project
  Authors (https://github.com/googlefonts/AntonFont) — licensed under the SIL
  Open Font License 1.1, vendored as `static/vendor/anton-latin.woff2` with its
  licence alongside it in `anton-OFL.txt`. It is the face of the app's own wordmark, the one that changes
  with your alignment. Vendored rather than linked so the app never has to
  reach the internet to look like itself.

This tool is free and noncommercial, forever. See LICENSE.

# Hero Companion — Session Memory (CLAUDE.md)

Claude Code reads this file automatically at the start of every session.
**Standing rule: when a session establishes a durable fact, workflow, or decision, update this file before the session ends.** Do not let knowledge die with the session.

## Dev preview workflow (do not re-derive this)

- The **installed tray app owns port 5000**. Never kill it, never try to bind 5000.
- The **dev copy runs on port 5080**, launched via `start-dev.bat` at the repo root (Joel also has a desktop shortcut to it). Both copies run side by side.
- To verify UI changes: have Joel run `start-dev.bat` and check http://localhost:5080 (hard-reload after changes).

## Release rules

- Nothing is released without Joel's say-so. Changelog entries are staged under **"Unreleased"** until he approves a version release.
- The repo is public on GitHub — keep raw brainstorms and personal notes out of commits. Ideation notes live in `C:\Users\joelc\code\ideas.md` (outside this repo); when Joel says "read ideas.md", that's the file.

## Credits

- **Maelwys** (https://forums.homecomingservers.com/profile/30623-maelwys/) is to be included in CREDITS for his feedback contributions. ✅ Done 2026-07-08: "The Reviewer" section in CREDITS.md + the help.md credits paragraph.

## Design principles (from Joel)

- One shared pool of game-engineered rules, but **every champion/build is unique unto itself** — the planner must not treat builds as one-size-fits-all within that rule scope.
- Audits/checkmarks are not ground truth — Joel's eyes outrank green audits. Coherence audits must hard-fail on empty slots, icon-less pieces, and validation noise.

## Open work queue (as of 2026-07-08)

- ✅ "How do you play" section (done 2026-07-08, unreleased): `/build/explain_intent` endpoint
  (server.py, after `_off_role_notice`) derives tailored per-choice explanations + a combined
  summary from the SAME presets the solve uses (ai_build.preset_targets/ROLE_PRESETS/
  CONTENT_PRESETS — never drifts). Frontend: `wizExplain()` in app.js, `#wiz-pop` +
  `#wiz-summary` in index.html, styles in style.css. Pop-up fires on each wiz select change;
  character changes re-tailor the open pop-up + summary. Awaiting Joel's 5080 hard-reload check.
- Maelwys post tasks #3–#10: CJ vs Weave/Maneuvers slot placement (needs end-cost + toggle-magnitude modeling; verify henchmen +MaxHP inheritance game-first in client bins), autopick Fighting pool for team-damage MM, enhancement levels/+5 boosters, manual HO/DSync slotting, suppression toggle, attack-card decision-note wording (awaiting card text from Joel).

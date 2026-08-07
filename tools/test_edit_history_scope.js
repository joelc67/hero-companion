// Battery: OPENING A CHARACTER IS NOT AN EDIT (app.js recordEdit / EDIT_HISTORY).
//   node tools/test_edit_history_scope.js        (run from the repo root)
//
// Joel, 2026-08-07: the "What changed" receipt appeared by itself on launch —
// "it now looks terrible". Traced by hooking recordEdit in a live page:
//   recordEdit <- onPoolChange <- onArchetypeChange <- applyImportedBuild <- loadSave
// Every load drives the archetype/pool cascade, and the cascade recorded an edit
// exactly as a user's dropdown change would. Two faults came out of that:
//   * the phantom receipt (recordEdit captured the PREVIOUS build's totals, the
//     load recomputed, and the receipt fired comparing one character to another)
//   * the UNDO STACK filled from loading alone — measured before the fix: open
//     one character then another and Undo is ENABLED having done nothing, with
//     the top differing snapshot holding ZERO powers, so pressing it emptied the
//     build. That is the one that could cost someone their work.
//
// Both halves are checked here, and so is the thing that must NOT change: a real
// edit still records, still enables Undo, and still restores.
//
// argv[2] = an alternative app.js, so this battery is proven against sabotaged
// copies rather than trusted because it went green.
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
const src = fs.readFileSync(process.argv[2] || path.join(root, "static/app.js"), "utf8");

function lift(name, decl) {
  const start = src.indexOf(decl || ("function " + name));
  assert.ok(start > 0, name + " not found in app.js");
  let depth = 0, end = -1;
  for (let j = src.indexOf("{", start); j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}" && --depth === 0) { end = j + 1; break; }
  }
  assert.ok(end > 0, "could not brace-match " + name);
  return src.slice(start, end);
}

// The two functions under test, evaluated together with a tiny harness that
// stands in for the module-level state they touch. Everything else they call is
// stubbed; nothing about the logic under test is re-implemented here.
const harness = `
  let EDIT_HISTORY = [];
  let _PRE_EDIT_TOTALS = null;
  let _LOADING_BUILD = false;
  let LAST_TOTALS = { melee: 1 };
  let build = { powers: [{ full_name: "A" }], pools: [], incarnates: {} };
  let roleFocus = {}; const PREVIEW_BOOSTS = {}; const ACCOLADES_CHECKED = new Set();
  let editBarCalls = 0;
  function updateEditBar() { editBarCalls++; }
  function updateCustomTargetsChip() {}
  function _snapshotBuild() { return JSON.parse(JSON.stringify({ powers: build.powers })); }
`;
const api = `
  return { recordEdit, resetBuildScopedState,
           state: () => ({ hist: EDIT_HISTORY.length, pre: _PRE_EDIT_TOTALS, bar: editBarCalls }),
           setLoading: v => { _LOADING_BUILD = v; },
           addPower: () => build.powers.push({ full_name: "B" }) };
`;
const mod = new Function(harness + lift("recordEdit") + "\n"
  + lift("resetBuildScopedState") + "\n" + api)();

let n = 0;
const check = (label, cond) => { assert.ok(cond, "FAIL: " + label); n++; };

// 1-2. THE FIX: while the app is driving a load, recordEdit does nothing.
mod.setLoading(true);
mod.recordEdit();
mod.recordEdit();
check("a load records no undo entry", mod.state().hist === 0);
check("a load captures no before-totals, so no receipt can fire",
      mod.state().pre === null);

// 3-5. POSITIVE CONTROL: with the guard down, a real edit records normally.
// Without this, a battery would pass just as happily if recordEdit were gutted.
mod.setLoading(false);
mod.recordEdit();
check("a real edit still records an undo entry", mod.state().hist === 1);
check("a real edit still captures the before-totals", mod.state().pre !== null);
mod.addPower();
mod.recordEdit();
check("a second real edit stacks", mod.state().hist === 2);

// 6-7. Swapping characters empties the stack, so Undo can never reach back into
// the character you just closed.
mod.resetBuildScopedState();
check("a swapped-in character starts with an empty undo stack",
      mod.state().hist === 0);
check("...and with no pending receipt", mod.state().pre === null);

// 8. The edit bar is told, or the Undo button stays lit over an empty stack.
const before = mod.state().bar;
mod.resetBuildScopedState();
check("resetBuildScopedState refreshes the edit bar", mod.state().bar > before);

// 9-10. STRUCTURAL: the guard has to wrap the WHOLE load, in a finally — a load
// can throw (loadSave catches exactly that), and a leaked flag would silently
// stop recording every real edit afterwards.
check("applyImportedBuild sets the load guard",
      /_LOADING_BUILD\s*=\s*true/.test(src));
check("...and clears it in a finally, not on the happy path only",
      /finally\s*{[^}]*_LOADING_BUILD\s*=\s*false/.test(src));

console.log(`${n} checks passed`);

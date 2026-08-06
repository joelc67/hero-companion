// Battery for the picker's LEGALITY gate (app.js _uniqueBlockedElsewhere).
//   node tools/test_slot_rules.js        (run from the repo root)
//
// Joel, 2026-08-06: "make sure the end user cannot break rules, like applying a
// unique IO a second time the entire build, or the same IO in the same power
// more than once."
//
// Both were already ERRORS in engine.validate_build; only the same-power repeat
// was PREVENTED. This pins the second half — and, just as important, pins that
// it does NOT over-block: Luck of the Gambler's Def/Global-Recharge is flagged
// unique and is legitimately slotted up to five times, so blocking it would
// refuse a legal build. That is the more expensive mistake of the two, and it is
// the one this project has made before.
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
// argv[2] = an alternative app.js, so the battery is proven against sabotage.
const src = fs.readFileSync(process.argv[2] || path.join(root, "static/app.js"), "utf8");

function lift(name) {
  const start = src.indexOf("function " + name);
  assert.ok(start > 0, name + " not found in app.js");
  let depth = 0, end = -1;
  for (let j = src.indexOf("{", start); j < src.length; j++) {
    if (src[j] === "{") depth++;
    else if (src[j] === "}" && --depth === 0) { end = j + 1; break; }
  }
  assert.ok(end > 0, "could not brace-match " + name);
  return src.slice(start, end);
}

let BUILD = null, META = null, ACTIVE = null;
const make = new Function("B", "M", "A",
  "const build = B(), META = M(), activeSlot = A();"
  + lift("_uniqueBlockedElsewhere")
  + "; return _uniqueBlockedElsewhere;");
const call = (piece, setName, build, meta, active) =>
  make(() => build, () => meta, () => active)(piece, setName);

const LOTG = "luck of the gambler: defense/increased global recharge speed";
const META_OK = { non_unique_overrides: [LOTG] };
// a build holding a Kismet unique in Weave (power 1, slot 0)
const build = () => ({ powers: [
  { full_name: "Pool.Fighting.Tough", display_name: "Tough", slots: [null, null] },
  { full_name: "Pool.Fighting.Weave", display_name: "Weave",
    slots: [{ piece_uid: "kismet_acc", piece_name: "Accuracy" }, null] },
] });
const kismet = { uid: "kismet_acc", name: "Accuracy", unique: true };
const lotg = { uid: "lotg_rech", name: "Defense/Increased Global Recharge Speed", unique: true };
const plain = { uid: "plain_dmg", name: "Damage", unique: false };
const slotInTough = { powerIdx: 0, slotIdx: 0 };

let n = 0;
const check = (label, cond) => { assert.ok(cond, "FAIL: " + label); n++; };

// 1-2: THE RULE. A unique already slotted in ANOTHER power is blocked, and the
// block names where it already is, so the message can teach rather than scold.
{
  const at = call(kismet, "Kismet", build(), META_OK, slotInTough);
  check("a unique held elsewhere is blocked", !!at);
  check("...and it names the power holding it", at === "Weave");
}

// 3: NEGATIVE CONTROL — the SAME slot it already occupies is not "elsewhere",
// or re-picking the piece you are standing on would refuse itself.
check("its own slot does not block it",
  call(kismet, "Kismet", build(), META_OK, { powerIdx: 1, slotIdx: 0 }) === null);

// 4: NEGATIVE CONTROL — a non-unique piece is never blocked by this rule.
check("a non-unique piece is never blocked by uniqueness",
  call({ ...plain, uid: "kismet_acc" }, "Kismet", build(), META_OK, slotInTough) === null);

// 5: NEGATIVE CONTROL — a unique NOT slotted anywhere is free to take.
check("an unslotted unique is takeable",
  call(lotg, "Luck of the Gambler", build(), META_OK, slotInTough) === null);

// 6-7: ⚠ THE OVER-BLOCKING GUARD. LotG's global recharge is flagged unique and
// the game allows up to five. Refusing it would refuse a legal build.
{
  const b = build();
  b.powers[1].slots[0] = { piece_uid: "lotg_rech", piece_name: lotg.name };
  check("LotG global recharge is NOT blocked (the game allows repeats)",
    call(lotg, "Luck of the Gambler", b, META_OK, slotInTough) === null);
  // and the override must be matched case-insensitively on the full label
  check("...matched on the full 'set: piece' label",
    call(lotg, "LUCK OF THE GAMBLER", b, META_OK, slotInTough) === null);
}

// 8: ⚠ FAIL OPEN, NOT SHUT. With no meta loaded we cannot know the overrides,
// and blocking blind would refuse legal builds. The server-side validator is
// still the backstop, so the safe direction here is to allow.
check("no meta → does not block on uniqueness",
  call(kismet, "Kismet", build(), null, slotInTough) === null);

// 9: no active slot means no picker is open — nothing to judge.
check("no active slot → no block", call(kismet, "Kismet", build(), META_OK, null) === null);

console.log(`test_slot_rules: ${n} of 9 checks passed`);
assert.strictEqual(n, 9, "expected 9 checks");

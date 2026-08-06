// Battery for the improvement report's PER-POWER deltas (app.js renderImproveDiff).
//   node tools/test_improve_diff.js        (run from the repo root)
//
// Loads the real function out of app.js and drives it with fixtures shaped like
// engine.calculate_build's totals — offense.attacks[] and offense.pets[].
// Negative-controlled both ways: an unchanged build must produce NO power rows,
// and a debuff row (base magnitudes, unaffected by slotting) must never make one.
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
// argv[2] = an alternative app.js, so the battery can be proven against a
// deliberately sabotaged copy instead of being trusted because it went green.
const src = fs.readFileSync(process.argv[2] || path.join(root, "static/app.js"), "utf8");

// --- pull the function out by brace matching (it only touches escHtml + $) ---
const start = src.indexOf("function renderImproveDiff");
assert.ok(start > 0, "renderImproveDiff not found in app.js");
let i = src.indexOf("{", start), depth = 0, end = -1;
for (let j = i; j < src.length; j++) {
  if (src[j] === "{") depth++;
  else if (src[j] === "}" && --depth === 0) { end = j + 1; break; }
}
assert.ok(end > 0, "could not brace-match renderImproveDiff");

let html = "";
const el = { classList: { remove() {} }, set innerHTML(v) { html = v; } };
const make = new Function("escHtml", "$",
  src.slice(start, end) + "; return renderImproveDiff;");
const renderImproveDiff = make(s => String(s), () => el);

const run = (before, after, opts) => {
  html = "";
  renderImproveDiff({ totals: before, name: "test" },
                    { totals: after, powers: [] }, null, opts);
  return html;
};
const powerTable = h => {
  const m = h.match(/<details open><summary>Power by power[\s\S]*?<\/details>/);
  return m ? m[0] : "";
};

let n = 0;
const check = (label, cond) => { assert.ok(cond, "FAIL: " + label); n++; };

// 1-3: an attack that got better shows its NAME, its cycled DPS move, and per-hit.
{
  const b = { offense: { attacks: [{ name: "Empty Clips", dps_spam: 40, damage: 100 }] } };
  const a = { offense: { attacks: [{ name: "Empty Clips", dps_spam: 58, damage: 120 }] } };
  const t = powerTable(run(b, a));
  check("names the power", t.includes("Empty Clips"));
  check("cycled DPS delta", /▲ 18 DPS/.test(t));
  check("per-hit delta", /damage<\/span> Empty Clips — per hit[\s\S]*?▲ 20/.test(t));
}

// 4-5: a pet is credited to the POWER that summons it (the henchman case).
{
  const row = v => ({ offense: { pets: [{ name: "Ice Elemental", from_power: "Jack Frost",
    dps_total: v, dps_each: v }] } });
  const t = powerTable(run(row(72.4), row(78.3)));
  check("pet named with its power", t.includes("Jack Frost → Ice Elemental"));
  check("pet DPS delta", /▲ 5.9 DPS/.test(t));
}

// 5b: a debuff row must NOT produce per-power rows — its magnitudes are base
// (engine._resolve_mag, no slot boosts), so anything there would be a lie.
{
  const row = v => ({ offense: { debuffs: [{ effect: "Resistance", type: "all", pct: v,
    sources: [{ name: "Envenom", v: v }] }] } });
  check("no per-power debuff rows", !powerTable(run(row(20), row(32))).includes("Envenom"));
}

// 6-7: NEGATIVE CONTROL — nothing changed means no power section at all,
// and the report still says so in words rather than going blank.
{
  const same = { offense: { attacks: [{ name: "Empty Clips", dps_spam: 40, damage: 100 }],
    buffs: [{ effect: "Defense", type: "Melee", pct: 10,
              sources: [{ name: "Weave", v: 10 }] }] } };
  const h = run(same, JSON.parse(JSON.stringify(same)));
  check("no power section when nothing moved", powerTable(h) === "");
  check("says nothing moved", h.includes("Nothing measurable moved"));
}

// 8: a power section renders even when no build-wide stat crossed its threshold
// (the whole point: a per-power move the totals row rounds away).
{
  const b = { offense: { attacks: [{ name: "Gloom", dps_spam: 30 },
                                   { name: "Moonbeam", dps_spam: 30 }] } };
  const a = { offense: { attacks: [{ name: "Gloom", dps_spam: 45 },
                                   { name: "Moonbeam", dps_spam: 15 }] } };
  const h = run(b, a);
  check("per-power section stands alone", powerTable(h).includes("Gloom")
    && !h.includes("Nothing measurable moved"));
}

// 10-13: BARE mode — the per-IO "what is this worth" panel reuses this diff but
// is not a solve. Nothing was changed and there is nothing to export, so the
// solve chrome goes and the columns say what they really hold.
{
  const b = { defense: { melee: 40 } }, a = { defense: { melee: 45 } };
  const solve = run(b, a), worth = run(b, a, { bare: true });
  check("solve mode keeps its heading", /Improvement — test/.test(solve));
  check("bare mode drops the solve heading", !/Improvement — test/.test(worth));
  check("bare mode drops the export nag", !/Export to Mids/.test(worth)
    && /Export to Mids/.test(solve));
  check("bare mode relabels the columns", /Without it/.test(worth)
    && /With it/.test(worth) && !/<th>Before<\/th>/.test(worth));
}

// 14-15: the column labels follow WHO IS ASKING. The per-IO panel compares a
// build with and without a piece; the edit receipt compares before and after a
// change. Calling the receipt's columns "Without it / With it" would
// misdescribe the numbers in it.
{
  const b = { defense: { melee: 40 } }, a = { defense: { melee: 45 } };
  const worth = run(b, a, { bare: true });
  const receipt = run(b, a, { bare: true, labels: ["Before", "After"] });
  check("per-IO panel says Without it / With it",
    /Without it/.test(worth) && /With it/.test(worth));
  check("the receipt says Before / After instead",
    /<th>Before<\/th>/.test(receipt) && /<th>After<\/th>/.test(receipt)
    && !/Without it/.test(receipt));
}

console.log(`test_improve_diff: ${n} of 15 checks passed`);
assert.strictEqual(n, 15, "expected 15 checks");

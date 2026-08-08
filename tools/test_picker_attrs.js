// Every inline handler the enhancement picker writes must survive an apostrophe.
//
// The bug this exists for (field report BasiliskXVIII, 2026-08-07): the picker
// built  onclick='pickPiece("uid", "Gaussian's Synchronized Fire-Control", 3)'
// JSON.stringify escapes the double quote and the newline but NOT the
// apostrophe, so the ' inside Gaussian's closed the HTML attribute. The browser
// kept a truncated handler that could not parse, the row did nothing, and the
// console showed a syntax error about an unterminated string. 40 of our set and
// piece names carry an apostrophe, so none of them could be slotted by hand -
// and it had been that way since the first commit.
//
// Two checks, because either alone can be fooled:
//   (a) BEHAVIOUR - build the real attribute with the real escHtml, extract it
//       the way an HTML parser would, and require the result to still parse as
//       JavaScript. A names-only or regex-only check cannot prove that.
//   (b) SOURCE - no interpolated onclick anywhere in app.js may skip escHtml.
//       (a) only covers the two rows it knows about; (b) covers the next one
//       somebody writes.
//
// Usage: node tools/test_picker_attrs.js [alternative-app.js]
// The alternative path exists so the battery is PROVEN against sabotaged copies
// rather than trusted for going green.

const fs = require("fs");
const path = require("path");

const APP = process.argv[2] || path.join(__dirname, "..", "static", "app.js");
const src = fs.readFileSync(APP, "utf8");

let pass = 0, fail = 0;
const ok = (name, cond, detail) => {
  if (cond) { pass++; console.log(`  PASS  ${name}`); }
  else { fail++; console.log(`  FAIL  ${name}`); }
  if (detail) console.log(`        ${detail}`);
};

// ── lift the REAL escHtml out of app.js (never a re-implementation) ──────────
// ⚠ this repo is CRLF: a `;\n` anchor never matches here.
const m = src.match(/const escHtml = \(s\) =>[\s\S]*?;\r?\n/);
if (!m) { console.error("could not find escHtml in " + APP); process.exit(2); }
const escHtml = eval("(" + m[0].replace(/^const escHtml = /, "").replace(/;\s*$/, "") + ")");

// ── (a) behaviour ───────────────────────────────────────────────────────────
// Read an attribute value back the way an HTML parser does: the value runs to
// the NEXT occurrence of the delimiter, and character references are decoded.
function readAttr(html, name) {
  const at = html.indexOf(name + "=");
  if (at < 0) return null;
  const q = html[at + name.length + 1];
  if (q !== '"' && q !== "'") return null;
  const start = at + name.length + 2;
  const end = html.indexOf(q, start);
  if (end < 0) return null;
  return html.slice(start, end)
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}

const NASTY = [
  ["Gaussian's Synchronized Fire-Control", "the reported set"],
  ["Achilles' Heel", "apostrophe after an s"],
  ['a "quoted" set', "double quotes"],
  ["Cupid's \"odd\" name", "both quote characters at once"],
];

for (const [setName, why] of NASTY) {
  // exactly what the picker writes today
  const html = `<div class="piece" onclick="${escHtml(
    `pickPiece(${JSON.stringify("Some_Uid")}, ${JSON.stringify(setName)}, 3)`)}">x</div>`;
  const handler = readAttr(html, "onclick");
  let parsed = null, threw = null;
  try { new Function(handler); } catch (e) { threw = e.message; }
  // and the handler must still carry the WHOLE name, not a truncated head
  try { parsed = JSON.parse("[" + handler.replace(/^pickPiece\(/, "").replace(/\)$/, "") + "]"); }
  catch (e) { /* reported by the parse check below */ }
  ok(`the handler for ${JSON.stringify(setName)} still parses (${why})`,
     threw === null, threw ? `SyntaxError: ${threw}` : `handler: ${handler}`);
  ok(`...and it carries the whole set name, not a truncated one`,
     !!parsed && parsed[1] === setName,
     parsed ? `arg 1 = ${JSON.stringify(parsed[1])}` : "handler did not parse as arguments");
}

// NEGATIVE CONTROL on the check itself: the OLD construction must be caught.
{
  const bad = `<div onclick='pickPiece("Some_Uid", ${JSON.stringify("Gaussian's Set")}, 3)'>x</div>`;
  const handler = readAttr(bad, "onclick");
  let threw = null;
  try { new Function(handler); } catch (e) { threw = e.message; }
  ok("NEGATIVE CONTROL: the pre-fix construction is caught as broken",
     threw !== null, `truncated handler was ${JSON.stringify(handler)}`);
}

// ── (b) source: no interpolated onclick may skip escHtml ────────────────────
// ⚠ The rule is deliberately narrow, because a check that cries wolf is worse
// than none. It flags exactly the mistake that shipped and is DECIDABLE from the
// source: JSON.stringify inside an inline handler. That call looks like escaping
// and is not - it makes a value JS-safe, never ATTRIBUTE-safe, and it leaves the
// apostrophe alone. The other shape, `onclick="f('${x}')"`, needs to know where
// x came from (an internal key is fine, a set name is not), and no regex can
// answer that; those sites were read by hand instead and route through escHtml
// or carry internal keys only.
const offenders = [];
const re = /on(?:click|change)=(['"])([\s\S]*?)\1/g;
let hit;
while ((hit = re.exec(src)) !== null) {
  const body = hit[2];
  if (!/JSON\.stringify\(/.test(body)) continue;
  if (/^\$\{escHtml\(/.test(body.trim())) continue;   // the whole payload is escaped
  offenders.push(src.slice(0, hit.index).split("\n").length);
}
ok("no inline handler relies on JSON.stringify to be attribute-safe",
   offenders.length === 0,
   offenders.length ? `unescaped JSON.stringify at line(s): ${offenders.join(", ")}`
                    : "every handler carrying stringified text goes through escHtml");

console.log(`\npicker attribute battery: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);

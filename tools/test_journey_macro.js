// Battery for the Leveling Guide's badge MACRO row and the zone-art empty states
// (app.js _tackRow / _praeRange / _noZoneNote / _zoneArtHtml).
//   node tools/test_journey_macro.js        (run from the repo root)
//
// Two fixes from 2026-08-06, both of Joel's reports:
//   1. Badge coordinates are a click-to-copy /thumbtack command — the GAME's own
//      command for dropping the map marker, verified from cityofheroes.exe's
//      command table ("Set the thumbtack location on the minimap. <x> <y> <z>").
//   2. The art slot told the truth about WHICH empty it was in: a zone with no
//      texture is "art pending"; a level with no zone at all is not pending on
//      anything, and on the Flashback view above level 20 it never will be.
//
// Negative-controlled both ways: a badge with no coordinates must emit NO row and
// no command, and an in-range Flashback level must still get its picture.
const fs = require("fs");
const path = require("path");
const assert = require("assert");

const root = path.resolve(__dirname, "..");
// argv[2] = an alternative app.js, so the battery is PROVEN against deliberately
// sabotaged copies rather than trusted because it went green.
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

// The four functions, with the tiny surface they touch stubbed. escHtml is the
// REAL contract (it escapes the double quote — the attribute-XSS fix), so the
// stub escapes too: data-cmd is an attribute and must survive the same way.
const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;")
  .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
let PLACES = {}, ALIGN = "hero", ART = {};
const make = new Function("escHtml", "JOURNEY_PLACES_GET", "ALIGN_GET", "ART_GET",
  "const _journeyAlign = () => ALIGN_GET();"
  + "const _artFileFor = n => ART_GET()[String(n || '').toLowerCase()] || null;"
  + "Object.defineProperty(globalThis, 'JOURNEY_PLACES', { get: JOURNEY_PLACES_GET, configurable: true });"
  + lift("_praeRange") + lift("_noZoneNote") + lift("_zoneArtHtml") + lift("_tackRow")
  + "; return { _praeRange, _noZoneNote, _zoneArtHtml, _tackRow };");
const F = make(esc, () => PLACES, () => ALIGN, () => ART);

let n = 0;
const check = (label, cond) => { assert.ok(cond, "FAIL: " + label); n++; };

// ── the macro row ──────────────────────────────────────────────────────────
// 1-4: real coordinates become the game's command, SPACE separated, in x y z
// order, and carry it in data-cmd for the shipped .cmd-row copy handler.
{
  const h = F._tackRow([172, -59, -2944]);
  check("emits the game's own command name", /\/thumbtack /.test(h));
  check("space separated in x y z order", h.includes("/thumbtack 172 -59 -2944"));
  check("carries data-cmd for the shipped copy handler",
    /data-cmd="\/thumbtack 172 -59 -2944"/.test(h));
  check("reuses the .cmd-row mechanism rather than a second one",
    /class="cmd-row jny-tack"/.test(h));
}

// 5: it must NOT be a comma-joined list — that is what the old display did, and
// pasting it into the game does nothing.
check("no comma form", !/thumbtack[^"<]*,/.test(F._tackRow([1, 2, 3])));

// 6-9: NEGATIVE CONTROLS — anything that is not three real numbers emits nothing
// at all, so a badge without coordinates can never show a command that would
// send someone to 0,0,0.
check("no coords → no row", F._tackRow(null) === "");
check("empty array → no row", F._tackRow([]) === "");
check("two coords → no row", F._tackRow([1, 2]) === "");
check("non-numeric coords → no row", F._tackRow([1, "x", 3]) === "");

// ── the art slot's two different empties ───────────────────────────────────
PLACES = { modern: { zones: [
  { zone: "Nova Praetoria", from: 1, to: 9, alt_start: true },
  { zone: "Imperial City", from: 9, to: 15, alt_start: true },
  { zone: "Neutropolis", from: 15, to: 20, alt_start: true },
  { zone: "Kallisti Wharf", from: 40, to: 50 },
] } };
ART = { "nova praetoria": "nova-praetoria.jpg", "atlas park": "atlas-park.jpg" };

// 10-11: the Flashback range is DERIVED from the data, never typed in.
{
  const r = F._praeRange();
  check("praetorian range derived from the zone data", r && r[0] === 1 && r[1] === 20);
  PLACES = { modern: { zones: [] } };
  check("no alt_start zones → no range claimed", F._praeRange() === null);
  PLACES = { modern: { zones: [
    { zone: "Nova Praetoria", from: 1, to: 9, alt_start: true },
    { zone: "Imperial City", from: 9, to: 15, alt_start: true },
    { zone: "Neutropolis", from: 15, to: 20, alt_start: true },
  ] } };
}

// 12-14: past the range, the note states the real reason and names the range —
// and never claims a picture is coming.
{
  ALIGN = "praetorian";
  const note = F._noZoneNote(50);
  check("names the range it derived", /level 1 to 20/.test(note));
  check("says the stop is past the content", /past/i.test(note));
  check("does NOT promise pending art", !/pending/i.test(note));
}

// 15-17: THE BUG ITSELF — a Flashback stop with no zone must not read
// "zone art pending" (the art for Praetoria's zones is on disk; nothing is
// pending), and an in-range stop must still get its picture.
{
  ALIGN = "praetorian";
  const empty = F._zoneArtHtml([], F._noZoneNote(50));
  check("no zone → not the pending apology", !/zone art pending/.test(empty));
  check("no zone → the honest sentence instead", /jny-art-none/.test(empty));
  // over 26 words, so collapseLongExplanations would eat its tail without this
  check("the sentence is kept whole", /keep-whole/.test(empty));
}
{
  const good = F._zoneArtHtml(["Nova Praetoria"], F._noZoneNote(1));
  check("in-range Flashback level still shows its art", /nova-praetoria\.jpg/.test(good));
  check("and is marked as having art", /jny-art has-art/.test(good));
}

// 18: a zone we genuinely hold no texture for KEEPS the pending wording — that
// case was never wrong and must not be swept up by the fix.
{
  ALIGN = "hero";
  const h = F._zoneArtHtml(["Boomtown"], F._noZoneNote(12));
  check("named zone without a texture still reads as pending",
    /zone art pending/.test(h) && /Boomtown/.test(h));
}

console.log(`journey macro + zone-art battery: ${n} of ${n} checks PASS`);

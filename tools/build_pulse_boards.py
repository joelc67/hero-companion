"""CoH Pulse Boards — ALPHA local generator.

Builds a self-contained pulse_boards.html from THIS machine's captured events
(%APPDATA%\\HeroCompanion\\gamelog\\events.jsonl) — the single-member alpha of the
community boards: server pulse from recruitment sightings, per-character scorecards,
capture coverage. Everything on the page came from the local store; nothing is
uploaded anywhere. When the community layer ships, this same page shape gets fed by
hub data packs instead.

Run:  py tools\\build_pulse_boards.py          (writes %APPDATA%\\HeroCompanion\\pulse_boards.html)
      py tools\\build_pulse_boards.py --open   (build then open in the browser)
"""
import html
import json
import os
import sys
import webbrowser

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import gamelog  # noqa: E402

APPDIR = os.path.join(os.environ.get("APPDATA", ROOT), "HeroCompanion")
gamelog.STATE_DIR = os.path.join(APPDIR, "gamelog")
OUT = os.path.join(APPDIR, "pulse_boards.html")

CSS = """
:root{--ground:#0c1220;--panel:#131c2e;--line:#22304a;--pulse:#3fd2ff;--gold:#f0b93b;
--ink:#dbe4f5;--dim:#8fa0bd;--faint:#5b6c8c}
body{background:var(--ground);color:var(--ink);font-family:'Segoe UI',system-ui,sans-serif;
margin:0;line-height:1.5}
.wrap{max-width:980px;margin:0 auto;padding:0 18px 48px}
.mock{background:var(--gold);color:#20180a;text-align:center;font-size:.72rem;
letter-spacing:.12em;text-transform:uppercase;padding:5px}
.logo{font-family:'Bahnschrift SemiCondensed','Arial Narrow',sans-serif;font-weight:700;
font-size:2.2rem;text-transform:uppercase;margin:26px 0 2px}
.logo b{color:var(--pulse)}
.tag{color:var(--dim);margin-bottom:22px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:6px;
padding:16px 18px;margin:14px 0}
h2{font-family:'Bahnschrift SemiCondensed','Arial Narrow',sans-serif;text-transform:uppercase;
letter-spacing:.08em;font-size:1rem;margin:0 0 10px}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th{font-size:.66rem;text-transform:uppercase;letter-spacing:.1em;color:var(--faint);
text-align:left;padding:5px 8px;border-bottom:1px solid var(--line)}
td{padding:6px 8px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.num{font-family:Consolas,monospace;font-variant-numeric:tabular-nums;text-align:right}
.dim{color:var(--faint);font-size:.78rem}
footer{color:var(--dim);font-size:.8rem;border-top:1px solid var(--line);
padding-top:14px;margin-top:22px}
"""


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def build(state_dir=None):
    # Frozen Lite passes its resolved store explicitly so there's never any doubt which
    # events.jsonl is read (the "empty board" confusion was partly not knowing the source).
    if state_dir:
        gamelog.STATE_DIR = state_dir
    src_path = gamelog._events_path()
    events = gamelog.load_events(limit=200000)
    s = gamelog.summarize(events)
    overall = s.get("overall") or s
    pulse = overall.get("pulse") or {"recruit_seen": 0, "by_content": {}, "recent": []}
    by_char = s.get("by_character") or {}

    rows_pulse = "".join(
        f"<tr><td>{_esc(k)}</td><td class='num'>{v}</td></tr>"
        for k, v in sorted(pulse["by_content"].items(), key=lambda kv: -kv[1])) \
        or "<tr><td class='dim' colspan='2'>No recruitment sightings yet — play with "\
           "/logchat on and pulse capture enabled.</td></tr>"

    def _spots(r):
        if r.get("spots_filled") is not None and r.get("spots_total"):
            return f"{r['spots_filled']}/{r['spots_total']}"
        return r.get("spots_needed") or ""

    rows_recent = "".join(
        f"<tr><td>{_esc(r.get('ts'))}</td><td>{_esc(r.get('content') or '?')}</td>"
        f"<td>{_esc(r.get('channel'))}</td>"
        f"<td class='num'>{_esc(_spots(r))}</td></tr>"
        for r in pulse["recent"]) or "<tr><td class='dim' colspan='4'>—</td></tr>"

    # OVERALL captured card — ALWAYS shown when anything was captured, even before any
    # character can be attributed (a log started mid-session has no "Welcome" marker, so
    # every event lands here, not in a per-character bucket). Without this the page looked
    # empty despite hundreds of captured events.
    dk = overall.get("drop_kinds") or {}
    total_events = (overall.get("kills", 0) + overall.get("deaths", 0)
                    + len(overall.get("drops") or []) + overall.get("merits", 0)
                    + len(overall.get("badges") or []))
    drops_line = ", ".join(f"{v} {k}" for k, v in sorted(dk.items(), key=lambda x: -x[1])) or "—"
    overall_card = f"""
<div class='card'><h2>Captured so far — all characters</h2><table>
<tr><td>Days seen</td><td class='num'>{len(overall.get('days') or [])}</td></tr>
<tr><td>XP earned</td><td class='num'>{overall.get('xp', 0):,}</td></tr>
<tr><td>Influence gained</td><td class='num'>{overall.get('inf_gained', 0):,}</td></tr>
<tr><td>Influence spent</td><td class='num'>{overall.get('inf_spent', 0):,}</td></tr>
<tr><td>Reward merits</td><td class='num'>{overall.get('merits', 0)}</td></tr>
<tr><td>Drops</td><td class='num'>{len(overall.get('drops') or [])}</td></tr>
<tr><td>Defeats dealt / taken</td><td class='num'>{overall.get('kills', 0)} / {overall.get('deaths', 0)}</td></tr>
<tr><td>Badges earned (captured)</td><td class='num'>{len(overall.get('badges') or [])}</td></tr>
</table><div class='dim' style='margin-top:8px'>drop mix: {_esc(drops_line)}</div></div>"""

    char_cards = ""
    for name, cs in sorted(by_char.items()):
        badges = cs.get("badges") or []
        char_cards += f"""
<div class='card'><h2>{_esc(name)}</h2><table>
<tr><td>Days seen</td><td class='num'>{len(cs.get('days') or [])}</td></tr>
<tr><td>XP earned</td><td class='num'>{cs.get('xp', 0):,}</td></tr>
<tr><td>Influence gained</td><td class='num'>{cs.get('inf_gained', 0):,}</td></tr>
<tr><td>Reward merits</td><td class='num'>{cs.get('merits', 0)}</td></tr>
<tr><td>Badges earned (captured)</td><td class='num'>{len(badges)}</td></tr>
<tr><td>Defeats dealt / taken</td><td class='num'>{cs.get('kills', 0)} / {cs.get('deaths', 0)}</td></tr>
</table>{('<div class=dim>latest badges: ' + _esc(', '.join(badges[-5:])) + '</div>') if badges else ''}</div>"""
    if not char_cards:
        char_cards = ("<div class='card'><h2>Per character</h2><div class='dim'>Events "
                      "are attributed to a character once the log shows a \"Welcome to "
                      "City of Heroes\" line — that appears when you next log in with "
                      "logging on. Until then everything counts in the card above.</div></div>")

    page = f"""<!doctype html><html><head><meta charset='utf-8'>
<title>CoH Pulse Boards — alpha (local)</title><style>{CSS}</style></head><body>
<div class='mock'>Your LOCAL board · built from your own game log · nothing uploaded</div>
<div class='wrap'>
<div class='logo'>CoH <b>Pulse</b> Boards <span style='font-size:.9rem;color:#8fa0bd'>(your machine)</span></div>
<div class='tag'>This page is generated on YOUR PC from YOUR game log — it is not the shared
community site (that one lives at
<a href='https://joelc67.github.io/hero-companion/pulse/' style='color:#3fd2ff'>joelc67.github.io/hero-companion/pulse</a>
and is empty until community sharing opens). During the alpha your data stays here.</div>
<div class='card' style='border-color:#3fd2ff'>
<b>Read {len(events)} events</b> from<br><code style='color:#8fa0bd;font-size:.8rem'>{_esc(src_path)}</code>
{"<div class='dim' style='margin-top:6px'>0 events means logging has not written anything yet — run <b>/logchat 1</b> in game (each account) and play a little.</div>" if not events else ""}
</div>
<div class='card'><h2>Server pulse — recruitment seen</h2>
<table><tr><th>Content</th><th style='text-align:right'>Sightings</th></tr>{rows_pulse}</table>
<div class='dim' style='margin-top:8px'>total sightings: {pulse['recruit_seen']}</div></div>
<div class='card'><h2>Recent formations witnessed</h2>
<table><tr><th>When</th><th>Content</th><th>Channel</th><th style='text-align:right'>Spots</th></tr>
{rows_recent}</table></div>
{overall_card}
{char_cards}
<footer>Generated locally by Hero Companion from your own game log. Market pulse arrives
with the price book; league run pages arrive when the league/leader line formats are
learned (the format hunter is watching). When the community layer opens, sharing any of
this is per-stat opt-in — this alpha page never leaves your machine.</footer>
</div></body></html>"""
    os.makedirs(APPDIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    return OUT, len(events)


if __name__ == "__main__":
    out, n = build()
    print(f"built {out} from {n} events")
    if "--publish" in sys.argv:
        # Copy into the repo's GitHub Pages tree — committing + pushing docs/pulse/
        # updates the LIVE boards at https://joelc67.github.io/hero-companion/pulse/.
        # Publishing is a deliberate, owner-driven act (Joel's data, Joel's push) —
        # the community submission gate is unaffected: no one else's data exists here.
        pub = os.path.join(ROOT, "docs", "pulse", "index.html")
        os.makedirs(os.path.dirname(pub), exist_ok=True)
        with open(out, encoding="utf-8") as src, open(pub, "w", encoding="utf-8") as dst:
            dst.write(src.read())
        print(f"published copy -> {pub}  (commit + push to update the live site)")
    if "--open" in sys.argv:
        webbrowser.open("file:///" + out.replace("\\", "/"))

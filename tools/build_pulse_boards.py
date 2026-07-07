"""CoH Pulse Boards — local generator (the full board).

Builds a self-contained pulse_boards.html from THIS machine's captured events
(%APPDATA%\\HeroCompanion\\gamelog\\events.jsonl). Sections: server pulse (what's
forming on the shard), a scorecard per account/character, haul + market activity,
badges, and honest "collecting" placeholders for the boards that need line formats the
capture is still learning (iTrial/TF runs). Everything came from the local store; nothing
is uploaded. When the community layer ships, this same page is fed by hub data packs.

public=True builds the PUBLISH variant — the same boards, minus anything that has no
business on a public page: the machine path to events.jsonl and account LOGIN names
(half of a game login; only character names and anonymous labels go online).

Run:  py tools\\build_pulse_boards.py            (writes %APPDATA%\\HeroCompanion\\pulse_boards.html)
      py tools\\build_pulse_boards.py --open     (build then open)
      py tools\\build_pulse_boards.py --publish   (public variant into docs/pulse for the live site)
"""
import datetime
import html
import json
import os
import sys
import webbrowser

if sys.stdout is not None:                    # None in a windowed (--noconsole) exe
    sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "server"))
import gamelog  # noqa: E402

APPDIR = os.path.join(os.environ.get("APPDATA", ROOT), "HeroCompanion")
gamelog.STATE_DIR = os.path.join(APPDIR, "gamelog")
OUT = os.path.join(APPDIR, "pulse_boards.html")

CSS = """
:root{--ground:#0c1220;--panel:#131c2e;--panel2:#182338;--line:#22304a;--pulse:#3fd2ff;
--gold:#f0b93b;--green:#4cc38a;--ink:#dbe4f5;--dim:#8fa0bd;--faint:#5b6c8c}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:'Segoe UI',system-ui,sans-serif;
margin:0;line-height:1.5}
.wrap{max-width:1000px;margin:0 auto;padding:0 18px 52px}
.mock{background:var(--gold);color:#20180a;text-align:center;font-size:.72rem;
letter-spacing:.12em;text-transform:uppercase;padding:5px}
.logo{font-family:'Bahnschrift SemiCondensed','Arial Narrow',sans-serif;font-weight:700;
font-size:2.2rem;text-transform:uppercase;margin:26px 0 2px}
.logo b{color:var(--pulse)}
.tag{color:var(--dim);margin-bottom:18px;font-size:.92rem}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:720px){.grid{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:7px;
padding:16px 18px;margin:14px 0}
.card.full{grid-column:1/-1}
h2{font-family:'Bahnschrift SemiCondensed','Arial Narrow',sans-serif;text-transform:uppercase;
letter-spacing:.07em;font-size:1.02rem;margin:0 0 4px}
.sub{color:var(--faint);font-size:.78rem;margin:0 0 12px}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th{font-size:.64rem;text-transform:uppercase;letter-spacing:.1em;color:var(--faint);
text-align:left;padding:5px 8px;border-bottom:1px solid var(--line)}
td{padding:6px 8px;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:none}
.num{font-family:Consolas,monospace;font-variant-numeric:tabular-nums;text-align:right}
.dim{color:var(--faint);font-size:.8rem}
.bar{height:7px;background:var(--line);border-radius:4px;overflow:hidden;margin-top:3px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--pulse),#7fe3ff)}
.pill{display:inline-block;background:var(--panel2);border:1px solid var(--line);
border-radius:3px;padding:2px 9px;font-size:.78rem;margin:2px 3px 2px 0}
.chartrow td:first-child{width:44%}
.soon{border-style:dashed;opacity:.85}
.soon .tagline{color:var(--gold);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}
.kpi{display:flex;gap:22px;flex-wrap:wrap;margin:4px 0 2px}
.kpi div{min-width:70px}
.kpi .v{font-family:Consolas,monospace;font-size:1.35rem}
.kpi .k{color:var(--faint);font-size:.66rem;text-transform:uppercase;letter-spacing:.09em}
footer{color:var(--dim);font-size:.8rem;border-top:1px solid var(--line);
padding-top:14px;margin-top:24px}
a{color:var(--pulse)}
"""


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def _n(x):
    return f"{x:,}" if isinstance(x, (int, float)) else _esc(x)


def _card(title, sub, body, cls=""):
    subhtml = f"<p class='sub'>{sub}</p>" if sub else ""
    return f"<div class='card {cls}'><h2>{_esc(title)}</h2>{subhtml}{body}</div>"


def _scorecard(label, cs, public=False):
    """A character/account card. public=True shows FLOW since capture began only —
    achievement STATE (level, badges, merits) and money stay off the public page:
    partial badge/level counts misrepresent a multi-year character (until the one-time
    character sync exists), and how much influence someone makes is nobody's business."""
    badges = cs.get("badges") or []
    lvl = cs.get("max_level")
    if public:
        kpi = (f"<div class='kpi'>"
               f"<div><div class='v'>{len(cs.get('days') or [])}</div><div class='k'>Days seen</div></div>"
               f"<div><div class='v'>{cs.get('kills', 0)}</div><div class='k'>Defeats</div></div>"
               f"</div>")
        tbl = (f"<table>"
               f"<tr><td>XP earned</td><td class='num'>{_n(cs.get('xp', 0))}</td></tr>"
               f"<tr><td>Drops</td><td class='num'>{len(cs.get('drops') or [])}</td></tr>"
               f"<tr><td>Defeats dealt / taken</td><td class='num'>{cs.get('kills', 0)} / {cs.get('deaths', 0)}</td></tr>"
               f"</table>")
        return _card(label, "since capture began", kpi + tbl)
    kpi = (f"<div class='kpi'>"
           f"<div><div class='v'>{len(cs.get('days') or [])}</div><div class='k'>Days</div></div>"
           f"<div><div class='v'>{('L' + str(lvl)) if lvl else '—'}</div><div class='k'>Top level</div></div>"
           f"<div><div class='v'>{len(badges)}</div><div class='k'>Badges</div></div>"
           f"<div><div class='v'>{cs.get('merits', 0)}</div><div class='k'>Merits</div></div>"
           f"</div>")
    tbl = (f"<table>"
           f"<tr><td>XP earned</td><td class='num'>{_n(cs.get('xp', 0))}</td></tr>"
           f"<tr><td>Influence in / out</td><td class='num'>{_n(cs.get('inf_gained', 0))} / {_n(cs.get('inf_spent', 0))}</td></tr>"
           f"<tr><td>Drops</td><td class='num'>{len(cs.get('drops') or [])}</td></tr>"
           f"<tr><td>Defeats dealt / taken</td><td class='num'>{cs.get('kills', 0)} / {cs.get('deaths', 0)}</td></tr>"
           f"</table>")
    tail = (f"<div class='dim' style='margin-top:8px'>latest badges: "
            f"{_esc(', '.join(badges[-6:]))}</div>") if badges else ""
    return _card(label, None, kpi + tbl + tail)


def build(state_dir=None, public=False):
    if state_dir:
        gamelog.STATE_DIR = state_dir
    src_path = gamelog._events_path()
    events = gamelog.load_events(limit=300000)
    s = gamelog.summarize(events)
    overall = s.get("overall") or s
    pulse = overall.get("pulse") or {"recruit_seen": 0, "by_content": {}, "recent": []}
    state = gamelog.load_state()
    known_char = state.get("characters") or {}       # account -> last character seen

    # ---- Server pulse: what's forming on the shard, as a bar chart by content ----------
    by_content = pulse.get("by_content") or {}
    top = sorted(by_content.items(), key=lambda kv: -kv[1])
    peak = top[0][1] if top else 1
    pulse_rows = "".join(
        f"<tr class='chartrow'><td>{_esc(k)}</td>"
        f"<td><div class='bar'><i style='width:{max(6, int(100 * v / peak))}%'></i></div></td>"
        f"<td class='num'>{v}</td></tr>" for k, v in top[:16])
    if not pulse_rows:
        pulse_rows = ("<tr><td class='dim' colspan='3'>No recruitment captured yet. This "
                      "fills as your shard's LFG / Broadcast / Coalition channels scroll by "
                      "while logging is on.</td></tr>")
    pulse_card = _card(
        "Server pulse — what's forming",
        f"live recruitment activity across public channels · {pulse.get('recruit_seen', 0)} sightings",
        f"<table><tr><th>Content</th><th>Activity</th><th class='num'>Seen</th></tr>{pulse_rows}</table>",
        cls="full")

    def _spots(r):
        if r.get("spots_filled") is not None and r.get("spots_total"):
            return f"{r['spots_filled']}/{r['spots_total']}"
        return r.get("spots_needed") or ""
    recent_rows = "".join(
        f"<tr><td class='dim'>{_esc((r.get('ts') or '')[11:16])}</td>"
        f"<td>{_esc(r.get('content') or '?')}</td><td>{_esc(r.get('channel'))}</td>"
        f"<td class='num'>{_esc(_spots(r))}</td></tr>" for r in (pulse.get("recent") or []))
    recent_card = _card(
        "Recent formations witnessed", None,
        "<table><tr><th>Time</th><th>Content</th><th>Channel</th><th class='num'>Spots</th></tr>"
        + (recent_rows or "<tr><td class='dim' colspan='4'>—</td></tr>") + "</table>")

    # ---- Scorecards: ONE per account (fixes "only Lime Juice") -------------------------
    accounts = sorted({e.get("account") for e in events if e.get("account")})
    cards = []
    for i, acct in enumerate(accounts, 1):
        asum = gamelog.summarize(events, accounts=[acct])
        per = asum.get("by_character") or {}
        # prefer the named character; else the account's known character; else the account
        # — but an account LOGIN name never goes on the public page, only an anon label.
        if per:
            for nm, cs in sorted(per.items()):
                cards.append(_scorecard(nm, cs, public=public))
        else:
            label = known_char.get(acct) or (
                f"Unnamed character #{i}" if public else f"Account: {acct}")
            cards.append(_scorecard(label, asum, public=public))
    if not cards:
        cards = ["<div class='card'><h2>Characters</h2><div class='dim'>Nothing captured "
                 "yet.</div></div>"]
    scorecards = "<div class='grid'>" + "".join(cards) + "</div>"

    # ---- Haul + market -----------------------------------------------------------------
    dk = overall.get("drop_kinds") or {}
    haul_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td class='num'>{v}</td></tr>"
        for k, v in sorted(dk.items(), key=lambda x: -x[1])) or \
        "<tr><td class='dim' colspan='2'>no drops captured yet</td></tr>"
    haul_card = _card(
        "Haul", "everything picked up, by kind",
        f"<table><tr><th>Kind</th><th class='num'>Count</th></tr>{haul_rows}</table>")
    # Money is LOCAL ONLY (Joel: how much people make is not for the public board — the
    # future price board needs per-item prices, never personal wealth).
    market_card = "" if public else _card(
        "Market activity", "your own auction-house flow (a seed for the price board)",
        f"<table>"
        f"<tr><td>Influence earned</td><td class='num'>{_n(overall.get('inf_gained', 0))}</td></tr>"
        f"<tr><td>Influence spent</td><td class='num'>{_n(overall.get('inf_spent', 0))}</td></tr>"
        f"<tr><td>Items sold</td><td class='num'>{overall.get('ah_sold', 0)}</td></tr>"
        f"</table>")

    # ---- Badges (LOCAL ONLY — a partial badge count misrepresents a veteran character;
    # badges/levels/accolades go public only via the one-time character sync, task #38) ---
    badges = overall.get("badges") or []
    badge_pills = "".join(f"<span class='pill'>{_esc(b)}</span>" for b in badges[-40:]) or \
        "<div class='dim'>No badge lines captured yet. Badge earns show here as they land " \
        "(the exact in-game line format is still being confirmed from real logs).</div>"
    badge_card = "" if public else _card(
        "Badges earned", f"{len(badges)} captured", badge_pills, cls="full")

    # ---- Boards still collecting (the vision pieces that need more log parsing) ---------
    sync_note = ("<p class='dim'>Character pages (level, badges, accolades, vet levels) "
                 "join the boards when the one-time character sync ships — so a "
                 "multi-year character arrives whole, not as the sliver a fresh capture "
                 "happens to see.</p>" if public else "")
    soon = _card(
        "iTrials · Task Forces · League runs", None,
        "<p class='dim'>Per-run pages (leader, participants, time, badges earned, ranked "
        "against every recorded run) appear here once the run start/finish and league "
        "join/leader line formats are confirmed from real logs. Capture is watching for "
        "them now — the format hunter flags each new shape it sees.</p>" + sync_note
        + "<p class='tagline'>collecting</p>", cls="full soon")

    # ---- Diagnostic banner (public: no machine path, no account login names) ------------
    if public:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        diag = (f"<div class='card' style='border-color:var(--pulse)'>"
                f"<b>Built from {len(events):,} captured events</b>"
                f"<div class='dim' style='margin-top:6px'>{len(accounts)} account(s) · "
                f"published {stamp}</div></div>")
    else:
        diag = (f"<div class='card' style='border-color:var(--pulse)'>"
                f"<b>Read {len(events):,} events</b> from "
                f"<code style='color:#8fa0bd;font-size:.8rem'>{_esc(src_path)}</code>"
                + ("<div class='dim' style='margin-top:6px'>0 events — logging hasn't written "
                   "anything yet. Run <b>/logchat 1</b> in game (each account) and play a "
                   "little.</div>" if not events else
                   f"<div class='dim' style='margin-top:6px'>{len(accounts)} account(s): "
                   f"{_esc(', '.join(accounts))}</div>") + "</div>")

    if public:
        mock = "Alpha · published by the board owner from their own game log"
        logo_note = "(live)"
        tag = ("This is the owner's own capture, published to their own page — no one "
               "else's data is collected here. Want a board of your own? "
               "<a href='https://github.com/joelc67/hero-companion/releases'>Companion "
               "Lite</a> builds one privately from your game logs.")
        foot = ("Published by Companion Lite from the board owner's own game log. Sections "
                "marked \"collecting\" fill in as capture learns the line formats from real "
                "sessions. When the community layer opens, sharing stays a separate, "
                "per-stat choice for every player.")
    else:
        mock = "Your LOCAL board · built from your own game log · nothing uploaded"
        logo_note = "(your machine)"
        tag = ("Generated on your PC from your game log — not the shared community site "
               "(<a href='https://joelc67.github.io/hero-companion/pulse/'>the online "
               "board</a> shows what its owner last published). Publish your own with the "
               "tray → \"Publish my board\".")
        foot = ("Companion Lite built this from your own game log. Sections marked "
                "\"collecting\" fill in as capture learns the line formats from your real "
                "sessions. When the community layer opens, sharing any of this stays a "
                "separate, per-stat choice.")

    page = f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>CoH Pulse Boards</title><style>{CSS}</style></head><body>
<div class='mock'>{mock}</div>
<div class='wrap'>
<div class='logo'>CoH <b>Pulse</b> Boards <span style='font-size:.9rem;color:#8fa0bd'>{logo_note}</span></div>
<div class='tag'>{tag}</div>
{diag}
{pulse_card}
{recent_card}
<h2 style='margin-top:24px'>Your characters</h2>
{scorecards}
<div class='grid'>{haul_card}{market_card}</div>
{badge_card}
{soon}
<footer>{foot}</footer>
</div></body></html>"""
    os.makedirs(APPDIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)
    return OUT, len(events)


if __name__ == "__main__":
    out, n = build()
    print(f"built {out} from {n} events")
    if "--publish" in sys.argv:
        pub = os.path.join(ROOT, "docs", "pulse", "index.html")
        os.makedirs(os.path.dirname(pub), exist_ok=True)
        OUT = pub
        build(public=True)
        print(f"published copy -> {pub}  (commit + push to update the live site)")
    if "--open" in sys.argv:
        webbrowser.open("file:///" + out.replace("\\", "/"))

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
.banner{display:block;width:calc(100% + 36px);height:56px;margin:-16px -18px 14px}
.hours{display:flex;gap:2px;align-items:flex-end;height:92px;margin-top:10px}
.hours div{flex:1;background:linear-gradient(180deg,#7fe3ff,var(--pulse));
border-radius:2px 2px 0 0;min-height:2px}
.hourlbl{display:flex;gap:2px;color:var(--faint);font-size:.62rem;margin-top:4px}
.hourlbl span{flex:1;text-align:center}
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


# ── event categories (Joel's board design): the content→category map ships in the
# hub-updatable lexicon pack; unmapped/learned content falls back to name heuristics ──
CATEGORIES = [
    ("itrial", "Incarnate Trials"),
    ("hero_tf", "Hero & Co-op Task Forces"),
    ("villain_sf", "Villain Strike Forces"),
    ("raid", "Raids, Monsters & Zone Events"),
    ("trial", "Trials & Special Events"),
    ("team", "Teams, Radios & Farms"),
    ("other", "Other Recruiting"),
]


def _categorize(content, lx_map):
    c = lx_map.get(content)
    if c:
        return c
    low = (content or "").lower()
    if "(itrial)" in low:
        return "itrial"
    if "strike force" in low:
        return "villain_sf"
    if "task force" in low:
        return "hero_tf"
    if "raid" in low or "giant monster" in low:
        return "raid"
    if "trial" in low or "event" in low:
        return "trial"
    if any(w in low for w in ("radio", "scanner", "farm", "mission", "team")):
        return "team"
    return "other"


def _banner(key, label):
    """A familiar-feeling graphic banner per category — self-contained inline SVG
    (the page must load with zero external assets)."""
    grad = {"itrial": ("#2a1548", "#7b4fe0"), "hero_tf": ("#14335e", "#2e7fd6"),
            "villain_sf": ("#3d0a12", "#b3202e"), "raid": ("#0f3018", "#3fae6e"),
            "trial": ("#0a333c", "#26a6a0"), "team": ("#3d2c08", "#c79a2e"),
            "other": ("#242c3c", "#5b6c8c")}[key]
    motifs = {
        # incarnate radiance: a ten-point star burst
        "itrial": ("<g fill='#ffffff22'><path d='M700 28 l6 16 16 6 -16 6 -6 16 -6 -16"
                   " -16 -6 16 -6z'/><circle cx='700' cy='50' r='7' fill='#ffffff55'/>"
                   "<path d='M640 10 l3 9 9 3 -9 3 -3 9 -3 -9 -9 -3 9 -3z'/>"
                   "<path d='M755 16 l3 9 9 3 -9 3 -3 9 -3 -9 -9 -3 9 -3z'/></g>"),
        # hero shield
        "hero_tf": ("<g fill='#ffffff22'><path d='M690 8 l26 8 v18 c0 14 -12 24 -26 30"
                    " c-14 -6 -26 -16 -26 -30 v-18 z'/>"
                    "<path d='M745 14 l18 6 v12 c0 10 -8 17 -18 21 c-10 -4 -18 -11 -18"
                    " -21 v-12 z' fill='#ffffff15'/></g>"),
        # arachnos spikes
        "villain_sf": ("<g stroke='#ffffff22' stroke-width='5' fill='none'>"
                       "<path d='M660 62 q20 -34 44 -46'/><path d='M690 64 q16 -26 36"
                       " -34'/><path d='M720 64 q14 -18 30 -22'/>"
                       "<path d='M786 62 q-20 -34 -44 -46'/></g>"
                       "<circle cx='726' cy='18' r='8' fill='#ffffff2a'/>"),
        # hamidon blob + mitos
        "raid": ("<g><circle cx='700' cy='36' r='22' fill='#ffffff1d'/>"
                 "<circle cx='700' cy='36' r='11' fill='#ffffff2a'/>"
                 "<circle cx='745' cy='20' r='5' fill='#ffffff30'/>"
                 "<circle cx='752' cy='48' r='4' fill='#ffffff30'/>"
                 "<circle cx='660' cy='14' r='4' fill='#ffffff30'/></g>"),
        # sewer waves
        "trial": ("<g stroke='#ffffff22' stroke-width='5' fill='none'>"
                  "<path d='M620 44 q20 -14 40 0 t40 0 t40 0 t40 0'/>"
                  "<path d='M640 24 q20 -14 40 0 t40 0 t40 0'/></g>"),
        # radio arcs
        "team": ("<g stroke='#ffffff22' stroke-width='5' fill='none'>"
                 "<circle cx='716' cy='40' r='10'/><path d='M732 24 a24 24 0 0 1 0 32'/>"
                 "<path d='M744 12 a40 40 0 0 1 0 56'/></g>"
                 "<circle cx='716' cy='40' r='4' fill='#ffffff40'/>"),
        # chat bubble
        "other": ("<g fill='#ffffff1d'><rect x='680' y='14' rx='8' width='70' height='30'/>"
                  "<path d='M694 44 l0 12 14 -12z'/></g>"),
    }[key]
    return (f"<svg class='banner' viewBox='0 0 800 56' preserveAspectRatio='xMidYMid"
            f" slice' xmlns='http://www.w3.org/2000/svg'>"
            f"<defs><linearGradient id='g_{key}' x1='0' y1='0' x2='1' y2='0'>"
            f"<stop offset='0' stop-color='{grad[0]}'/>"
            f"<stop offset='1' stop-color='{grad[1]}'/></linearGradient></defs>"
            f"<rect width='800' height='56' fill='url(#g_{key})'/>{motifs}"
            f"<text x='18' y='37' fill='#fff' font-family='Bahnschrift SemiCondensed,"
            f"Arial Narrow,sans-serif' font-size='24' font-weight='700'"
            f" letter-spacing='2' style='text-transform:uppercase'>"
            f"{_esc(label.upper())}</text></svg>")


def _hour_chart(by_hour):
    """24-bar busiest-times histogram (hours are the players' local log clocks)."""
    counts = [int(by_hour.get(h) or by_hour.get(str(h)) or 0) for h in range(24)]
    peak = max(counts) or 1
    bars = "".join(
        f"<div style='height:{max(2, int(100 * c / peak))}%' "
        f"title='{(h % 12 or 12)}{'a' if h < 12 else 'p'}m — {c} formations'></div>"
        for h, c in enumerate(counts))
    lbls = "".join(f"<span>{((h % 12) or 12)}{'a' if h < 12 else 'p'}</span>"
                   if h % 3 == 0 else "<span></span>" for h in range(24))
    return (f"<div class='hours'>{bars}</div><div class='hourlbl'>{lbls}</div>")


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

    # ---- Server pulse: busiest times + activity broken out by event category -----------
    by_content = pulse.get("by_content") or {}
    pulse_card = _card(
        "Server pulse — what's forming",
        f"formations witnessed on public channels · {pulse.get('recruit_seen', 0)} "
        "(a recruiter's repeated asks for the same run count once)",
        ("<div class='dim' style='font-size:.78rem'>Busiest times of day "
         "(players' local clocks)</div>" + _hour_chart(pulse.get("by_hour") or {}))
        if by_content else
        "<div class='dim'>No recruitment captured yet. This fills as the shard's "
        "LFG / Broadcast / Coalition channels scroll by while logging is on.</div>",
        cls="full")

    lx_map = (gamelog._lexicon() or {}).get("categories") or {}
    groups = {}
    for content, n in by_content.items():
        groups.setdefault(_categorize(content, lx_map), []).append((content, n))
    cat_cards = ""
    for key, label in CATEGORIES:
        rows = sorted(groups.get(key) or [], key=lambda kv: -kv[1])
        if not rows:
            continue
        peak = rows[0][1]
        body = "".join(
            f"<tr class='chartrow'><td>{_esc(k)}</td>"
            f"<td><div class='bar'><i style='width:{max(6, int(100 * v / peak))}%'></i></div></td>"
            f"<td class='num'>{v}</td></tr>" for k, v in rows[:12])
        cat_cards += (f"<div class='card full'>{_banner(key, label)}"
                      f"<p class='sub'>{sum(v for _k, v in rows)} formations · "
                      f"{len(rows)} distinct</p>"
                      f"<table><tr><th>Content</th><th>Activity</th>"
                      f"<th class='num'>Seen</th></tr>{body}</table></div>")

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
{cat_cards}
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

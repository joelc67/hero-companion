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
import calendar
import datetime
import html
import json
import os
import sys
import time
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
.hours{display:flex;gap:2px;align-items:flex-end;height:96px;margin-top:10px;
background:var(--panel2);border:1px solid var(--line);border-radius:6px;
padding:8px 8px 4px}
.hours div{flex:1;background:linear-gradient(180deg,#d8f6ff,#5fdcff);
border-radius:2px 2px 0 0;min-height:2px}
.hours div.z{background:#2c3b5c}
.hours div.hb{display:flex;flex-direction:column-reverse;overflow:hidden;
background:none}
.hours .hb b{display:block;min-height:1px}
.hours.mini{height:52px;margin-top:6px;padding:5px 6px 3px}
.hourlbl{display:flex;gap:2px;color:var(--dim);font-size:.66rem;margin-top:4px;
padding:0 8px}
.hourlbl span{flex:1;text-align:center}
.tzline{color:var(--dim);font-size:.78rem}
#nowstrip td{vertical-align:top}
.week{display:grid;grid-template-columns:34px repeat(24,1fr);gap:2px;margin-top:10px;
background:var(--panel2);border:1px solid var(--line);border-radius:6px;padding:8px}
.week span{font-size:.62rem;color:var(--dim);align-self:center}
.week i{display:block;height:13px;border-radius:2px;background:#232f4a}
.week .dlbl{cursor:pointer}
.week .dlbl:hover{color:var(--pulse);text-decoration:underline}
#daydetail{display:none;margin-top:10px;background:var(--panel2);
border:1px solid var(--line);border-radius:6px;padding:10px 12px;font-size:.88rem}
#daydetail .pill i{display:inline-block;width:9px;height:9px;border-radius:2px;
margin-right:6px;vertical-align:-1px}
#catlegend{margin-top:8px}
#catlegend .pill{cursor:default}
#catlegend .pill i{display:inline-block;width:10px;height:10px;border-radius:2px;
margin-right:6px;vertical-align:-1px}
tr[data-content]{cursor:default}
tr[data-content]:hover td{background:#1b2740}
"""


def _esc(s):
    return html.escape(str(s if s is not None else ""))


def _n(x):
    return f"{x:,}" if isinstance(x, (int, float)) else _esc(x)


def _pair_sales(events):
    """Single-claim price pairing (0.1.16 — the pricing layer #31 proving
    ground). The game logs a sale ("You have sold X") and its influence credit
    ("You got N influence from the Consignment House") as SEPARATE lines with
    no link, and credits can also arrive for older stored sales. So: a credit
    claims the single most recent unpaired sale within the window before it;
    zero or two-plus candidates = no pair, and the ledger says "unconfirmed"
    rather than guessing (a wrong price is worse than no price)."""
    window = 180  # seconds
    def _t(ev):
        try:
            return calendar.timegm(time.strptime(ev.get("ts") or "",
                                                 "%Y-%m-%d %H:%M:%S"))
        except Exception:  # noqa: BLE001
            return None
    sales = [dict(e, _t=_t(e)) for e in events if e.get("type") == "ah_sold"]
    for cred in (e for e in events if e.get("type") == "influence_ah"):
        ct = _t(cred)
        if ct is None:
            continue
        cands = [s for s in sales if s["_t"] is not None and "price" not in s
                 and 0 <= ct - s["_t"] <= window]
        if len(cands) == 1:
            cands[0]["price"] = cred.get("inf")
    return sales


def _market_ledger_html(events, overall):
    """The local-only per-item sales ledger. Prices appear only where the
    single-claim pairing is unambiguous."""
    sales = _pair_sales(events)
    priced = sum(1 for s in sales if s.get("price"))
    rows = "".join(
        f"<tr><td>{_esc(s.get('item') or '?')}</td>"
        + ("<td class='num'>" + _n(s["price"]) + "</td>" if s.get("price")
           else "<td class='num dim'>unconfirmed</td>")
        + f"<td class='dim'>{_esc(s.get('ts') or '')}</td></tr>"
        for s in sales[-20:][::-1]) or \
        "<tr><td class='dim' colspan='3'>no sales captured yet</td></tr>"
    return (
        f"<table><tr><td>Influence earned</td><td class='num'>{_n(overall.get('inf_gained', 0))}</td></tr>"
        f"<tr><td>Influence spent</td><td class='num'>{_n(overall.get('inf_spent', 0))}</td></tr>"
        f"<tr><td>Items listed</td><td class='num'>{overall.get('ah_listed', 0)}</td></tr>"
        f"<tr><td>Items sold</td><td class='num'>{overall.get('ah_sold', 0)}"
        f" <span class='dim'>({priced} with a confirmed price)</span></td></tr></table>"
        "<table style='margin-top:8px'><tr><th>Sold</th><th class='num'>Price</th>"
        f"<th>When</th></tr>{rows}</table>"
        "<p class='dim'>A price shows only when exactly one sale sits within 3 minutes "
        "before its Consignment House credit — the game logs them as separate lines, "
        "so an ambiguous match stays unconfirmed rather than guessed.</p>")


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


# Viewer-time-zone renderer for the PUBLIC board: all embedded data is UTC; this
# shifts every hour chart into the browser's zone (named in the header line) and fills
# the "happening right now" strip against the browser's own clock. The main chart is
# STACKED by category color (legend hover brightens a category); hovering any content
# row lights up exactly where that content lives in the chart above it (Joel's design).
# Plain vanilla JS, zero external assets.
_PULSE_JS = """
(function(){
var D=window.PULSE||{};var tz='UTC',s=0;
try{tz=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';
s=Math.round(-new Date().getTimezoneOffset()/60);}catch(e){}
var COL={itrial:'#8e5bff',hero_tf:'#3fa0ff',villain_sf:'#e04a56',raid:'#4cc38a',
trial:'#2ec4b6',team:'#f0b93b',other:'#8fa0bd'};
var ORDER=['itrial','hero_tf','villain_sf','raid','trial','team','other'];
var NAME={itrial:'Incarnate Trials',hero_tf:'Hero & Co-op TFs',
villain_sf:'Villain SFs',raid:'Raids & Events',trial:'Trials & Specials',
team:'Teams & Farms',other:'Other'};
function lab(h){return (h%12||12)+(h<12?'a':'p');}
function esc(x){return String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;');}
function rot(a){var o=[];for(var h=0;h<24;h++){o[(h+s+24)%24]=(a||[])[h]||0;}return o;}
var CATS={};ORDER.forEach(function(k){if((D.cats||{})[k])CATS[k]=rot(D.cats[k]);});
var main=document.querySelector("[data-hours='all']");
function drawMain(hot){
 if(!main)return;var tot=[],h;
 for(h=0;h<24;h++){tot[h]=0;for(var k in CATS){tot[h]+=CATS[k][h];}}
 var p=Math.max.apply(null,tot)||1,cells='';
 for(h=0;h<24;h++){
  if(!tot[h]){cells+="<div class='z' title='"+lab(h)+" \\u2014 0'></div>";continue;}
  var segs='';ORDER.forEach(function(k){var c=(CATS[k]||[])[h]||0;if(!c)return;
   var col=COL[k],dim=hot&&hot!==k;
   segs+="<b style='flex:"+c+";background:"+col+(dim?";opacity:.25":"")+"'></b>";});
  cells+="<div class='hb' style='height:"+Math.max(3,Math.round(100*tot[h]/p))+
   "%' title='"+lab(h)+" \\u2014 "+tot[h]+" formations'>"+segs+"</div>";}
 main.innerHTML=cells;}
drawMain(null);
var DAYS=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
var wk=document.getElementById('weekmap');
function localWeek(g){var o=[],d,h;for(d=0;d<7;d++){o[d]=[];for(h=0;h<24;h++){
 var uh=h-s,carry=Math.floor(uh/24);uh=((uh%24)+24)%24;
 o[d][h]=(g[((d+carry)%7+7)%7]||[])[uh]||0;}}return o;}
function hexA(hex,a){var n=parseInt(hex.slice(1),16);
 return 'rgba('+(n>>16)+','+((n>>8)&255)+','+(n&255)+','+a+')';}
function drawWeek(hot){
 if(!wk||!(D.week||{}).all)return;
 var g=localWeek(hot?((D.week.cats||{})[hot]||D.week.all):D.week.all);
 var p=1,d,h;for(d=0;d<7;d++)for(h=0;h<24;h++)p=Math.max(p,g[d][h]);
 var col=hot?COL[hot]:'#5fdcff',cells='';
 for(d=0;d<7;d++){cells+="<span class='dlbl' data-d='"+d+"' title='click for "+
   DAYS[d]+"\\u2019s breakdown'>"+DAYS[d]+"</span>";
  for(h=0;h<24;h++){var c=g[d][h];
   var bg=c?';background:'+hexA(col,Math.round((0.18+0.82*c/p)*100)/100):'';
   cells+="<i style='display:block"+bg+"' title='"+DAYS[d]+' '+lab(h)+" \\u2014 "+c+
    "'></i>";}}
 cells+='<span></span>';
 for(h=0;h<24;h++){cells+="<span style='text-align:center'>"+(h%3?'':lab(h))+"</span>";}
 wk.innerHTML=cells;
 wk.querySelectorAll('.dlbl').forEach(function(el){
  el.addEventListener('click',function(){dayBreak(+el.getAttribute('data-d'));});});}
var dd=document.getElementById('daydetail'),curDay=null;
function dayBreak(d){
 if(!dd)return;
 if(curDay===d){dd.style.display='none';curDay=null;return;}
 curDay=d;var tot={},sum=0,sp=(D.week||{}).sparse||{};
 for(var c in sp){sp[c].forEach(function(t){
  var lh=t[1]+s,carry=Math.floor(lh/24);
  if((((t[0]+carry)%7)+7)%7===d){tot[c]=(tot[c]||0)+t[2];sum+=t[2];}});}
 var items=Object.keys(tot).sort(function(a,b){return tot[b]-tot[a];});
 dd.innerHTML="<b>"+DAYS[d]+"</b> \\u00b7 "+sum+" formations in the last 7 days"+
  (items.length?"<div style='margin-top:6px'>"+items.map(function(c){
    var k=(D.catOf||{})[c]||'other';
    return "<span class='pill'><i style='background:"+COL[k]+"'></i>"+esc(c)+
     " \\u00d7"+tot[c]+"</span>";}).join(' ')+"</div>"
   :" <span class='dim'>\\u2014 nothing captured yet</span>");
 dd.style.display='block';}
drawWeek(null);
var leg=document.getElementById('catlegend');
if(leg){leg.innerHTML=ORDER.filter(function(k){return CATS[k];}).map(function(k){
  return "<span class='pill' data-cat='"+k+"'><i style='background:"+COL[k]+
   "'></i>"+NAME[k]+"</span>";}).join(' ');
 leg.querySelectorAll('[data-cat]').forEach(function(ch){
  ch.addEventListener('mouseenter',function(){var k=ch.getAttribute('data-cat');
   drawMain(k);drawWeek(k);});
  ch.addEventListener('mouseleave',function(){drawMain(null);drawWeek(null);});});}
function drawMini(el,key,hotContent){
 var cat=CATS[key]||rot((D.cats||{})[key]),p=Math.max.apply(null,cat)||1,cells='';
 var hc=hotContent?rot((D.contents||{})[hotContent]):null;
 for(var h=0;h<24;h++){var ct=cat[h];
  if(!ct){cells+="<div class='z' title='"+lab(h)+" \\u2014 0'></div>";continue;}
  var col=COL[key]||'#5fdcff',hh=Math.max(3,Math.round(100*ct/p));
  if(hc){var c=Math.min(hc[h]||0,ct);
   cells+="<div class='hb' style='height:"+hh+"%' title='"+lab(h)+" \\u2014 "+
    (hc[h]||0)+" of "+ct+"'>"+
    (c?"<b style='flex:"+c+";background:#ffffff'></b>":"")+
    ((ct-c)?"<b style='flex:"+(ct-c)+";background:"+col+";opacity:.25'></b>":"")+
    "</div>";}
  else{cells+="<div style='height:"+hh+"%;background:"+col+
   "' title='"+lab(h)+" \\u2014 "+ct+" formations'></div>";}}
 el.innerHTML=cells;}
document.querySelectorAll('.hours.mini[data-hours]').forEach(function(el){
 drawMini(el,el.getAttribute('data-hours'),null);});
document.querySelectorAll('tr[data-content]').forEach(function(row){
 var card=row.closest('.card');if(!card)return;
 var mini=card.querySelector('.hours.mini[data-hours]');if(!mini)return;
 var key=mini.getAttribute('data-hours');
 row.addEventListener('mouseenter',function(){
  drawMini(mini,key,row.getAttribute('data-content'));});
 row.addEventListener('mouseleave',function(){drawMini(mini,key,null);});});
document.querySelectorAll('.tzname').forEach(function(e){e.textContent=tz;});
var host=document.getElementById('nowstrip');
if(host){var now=Date.now()/1e3,prev=0,rows='';
 [[5,'last 5 min'],[15,'5\\u201315 min ago'],[30,'15\\u201330 min ago'],
  [60,'30\\u201360 min ago']].forEach(function(b){
  var seen={};(D.recent||[]).forEach(function(r){var age=now-r.t;
   if(age>prev*60&&age<=b[0]*60){seen[r.c]=(seen[r.c]||0)+1;}});
  var chips=Object.keys(seen).map(function(k){
   return "<span class='pill'>"+esc(k)+(seen[k]>1?' \\u00d7'+seen[k]:'')+"</span>";
  }).join('')||"<span class='dim'>\\u2014</span>";
  rows+="<tr><td class='dim' style='white-space:nowrap'>"+b[1]+"</td><td>"+chips+
   "</td></tr>";prev=b[0];});
 host.innerHTML=rows;}
})();
"""


def _hour_counts(by_hour):
    return [int(by_hour.get(h) or by_hour.get(str(h)) or 0) for h in range(24)]


_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _week_grid(content_day_hours, contents, window):
    """7×24 weekday-by-hour counts over the last-7-days window (UTC)."""
    g = [[0] * 24 for _ in range(7)]
    for content in contents:
        for day, hrs in (content_day_hours.get(content) or {}).items():
            if day not in window:
                continue
            try:
                wd = datetime.date.fromisoformat(day).weekday()
            except ValueError:
                continue
            for h, c in hrs.items():
                if str(h).isdigit() and 0 <= int(h) < 24:
                    g[wd][int(h)] += int(c)
    return g


def _week_html(grid):
    """Server-rendered heatmap (UTC fallback; the page script re-renders local)."""
    peak = max((c for row in grid for c in row), default=0) or 1
    cells = ""
    for wd, row in enumerate(grid):
        cells += f"<span>{_WEEKDAYS[wd]}</span>"
        for h, c in enumerate(row):
            a = round(0.12 + 0.88 * c / peak, 2) if c else 0
            bg = f";background:rgba(95,220,255,{a})" if c else ""
            cells += (f"<i style='display:block{bg}' title='{_WEEKDAYS[wd]} "
                      f"{(h % 12 or 12)}{'a' if h < 12 else 'p'} — {c}'></i>")
    lbls = "<span></span>" + "".join(
        f"<span style='text-align:center'>{((h % 12) or 12)}{'a' if h < 12 else 'p'}"
        "</span>" if h % 3 == 0 else "<span></span>" for h in range(24))
    return f"<div class='week' id='weekmap'>{cells}{lbls}</div>"


def _hour_chart(by_hour, key="all", mini=False):
    """24-bar busiest-times histogram. The server-rendered bars are the no-JS fallback;
    on the public board a small script re-renders every [data-hours] chart shifted to
    the VIEWER's time zone (the pipeline normalized all timestamps to UTC)."""
    counts = _hour_counts(by_hour)
    peak = max(counts) or 1
    bars = "".join(
        f"<div style='height:{max(2, int(100 * c / peak))}%'"
        f"{' class=z' if not c else ''} "
        f"title='{(h % 12 or 12)}{'a' if h < 12 else 'p'} — {c} formations'></div>"
        for h, c in enumerate(counts))
    lbls = "".join(f"<span>{((h % 12) or 12)}{'a' if h < 12 else 'p'}</span>"
                   if h % 3 == 0 else "<span></span>" for h in range(24))
    return (f"<div class='hours{' mini' if mini else ''}' data-hours='{_esc(key)}'>"
            f"{bars}</div><div class='hourlbl'>{lbls}</div>")


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
    # Public data is UTC (the pipeline normalizes every source); the page script shifts
    # every chart and timestamp into the VIEWER's browser time zone and says so.
    by_content = pulse.get("by_content") or {}
    tzline = ("<div class='tzline'>Busiest times of day — shown in your time zone "
              "(<span class='tzname'>UTC</span>)</div>" if public else
              "<div class='tzline'>Busiest times of day (this machine's clock)</div>")
    legend = "<div id='catlegend'></div>" if public else ""
    pulse_card = _card(
        "Server pulse — what's forming",
        f"formations witnessed on public channels · {pulse.get('recruit_seen', 0)} "
        "(a recruiter's repeated asks for the same run count once)",
        (tzline + _hour_chart(pulse.get("by_hour") or {}) + legend)
        if by_content else
        "<div class='dim'>No recruitment captured yet. This fills as the shard's "
        "LFG / Broadcast / Coalition channels scroll by while logging is on.</div>",
        cls="full")

    # happening right now — the browser computes the 5/15/30/60-minute windows against
    # its own clock, so the strip stays honest between pipeline publishes
    now_card = ""
    if public and by_content:
        now_card = _card(
            "Happening right now", "recruiting seen in the last hour, freshest first",
            "<table id='nowstrip'><tr><td class='dim'>This view needs JavaScript — "
            "see the category boards below for the full picture.</td></tr></table>",
            cls="full")

    lx_map = (gamelog._lexicon() or {}).get("categories") or {}
    content_hours = pulse.get("content_hours") or {}
    content_day_hours = pulse.get("content_day_hours") or {}
    groups, cat_hours = {}, {}
    for content, n in by_content.items():
        key = _categorize(content, lx_map)
        groups.setdefault(key, []).append((content, n))
        agg = cat_hours.setdefault(key, {})
        for h, c in (content_hours.get(content) or {}).items():
            agg[int(h)] = agg.get(int(h), 0) + c

    # ---- The last 7 days: weekday × hour heatmap (Joel's week-at-a-glance) -------------
    week_card, week_all, week_cats = "", None, {}
    all_days = sorted({d for cd in content_day_hours.values() for d in cd})
    if all_days:
        end = datetime.date.fromisoformat(all_days[-1])
        window = {(end - datetime.timedelta(days=i)).isoformat() for i in range(7)}
        week_all = _week_grid(content_day_hours, list(content_day_hours), window)
        for key, rows in groups.items():
            week_cats[key] = _week_grid(content_day_hours,
                                        [c for c, _n in rows], window)
        wk_tz = ("shown in your time zone (<span class='tzname'>UTC</span>)"
                 if public else "this machine's clock")
        week_card = _card(
            "The last 7 days",
            f"when the shard plays — day of week × time of day · {wk_tz}"
            + (" · <b>click a day</b> for its full breakdown · hover a legend color "
               "below to filter" if public else ""),
            _week_html(week_all) + ("<div id='daydetail'></div>" if public else ""),
            cls="full")
    cat_cards = ""
    for key, label in CATEGORIES:
        rows = sorted(groups.get(key) or [], key=lambda kv: -kv[1])
        if not rows:
            continue
        peak = rows[0][1]
        body = "".join(
            f"<tr class='chartrow' data-content=\"{_esc(k)}\"><td>{_esc(k)}</td>"
            f"<td><div class='bar'><i style='width:{max(6, int(100 * v / peak))}%'></i></div></td>"
            f"<td class='num'>{v}</td></tr>" for k, v in rows[:12])
        cat_cards += (f"<div class='card full'>{_banner(key, label)}"
                      f"<p class='sub'>{sum(v for _k, v in rows)} formations · "
                      f"{len(rows)} distinct · when to look for these:</p>"
                      f"{_hour_chart(cat_hours.get(key) or {}, key=key, mini=True)}"
                      f"<table style='margin-top:10px'><tr><th>Content</th><th>Activity</th>"
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
        "Market activity", "your own auction-house ledger (the price board's proving ground)",
        _market_ledger_html(events, overall), cls="full")

    # ---- Badges (LOCAL ONLY — a partial badge count misrepresents a veteran character;
    # badges/levels/accolades go public only via the one-time character sync, task #38) ---
    badges = overall.get("badges") or []
    badge_pills = "".join(f"<span class='pill'>{_esc(b)}</span>" for b in badges[-40:]) or \
        "<div class='dim'>No badge lines captured yet. Badge earns show here as they land " \
        "(the exact in-game line format is still being confirmed from real logs).</div>"
    badge_card = "" if public else _card(
        "Badges earned", f"{len(badges)} captured", badge_pills, cls="full")

    # ---- Boards still collecting (the vision pieces that need more log parsing) ---------
    # 0.1.16: the first CONFIRMED run-level formats now land as real rows — zone-
    # event completions and task-completion ticks — while per-run pages still wait
    # on the TF/iTrial completion-line formats (a designated to-completion session).
    zev = {}
    task_ticks = 0
    for ev in events:
        if ev.get("type") == "zone_event":
            z = ev.get("zone") or "?"
            zev.setdefault(z, {"n": 0, "last": ""})
            zev[z]["n"] += 1
            zev[z]["last"] = max(zev[z]["last"], ev.get("ts") or "")
        elif ev.get("type") == "task_done":
            task_ticks += 1
    early_rows = ""
    if zev or task_ticks:
        zrows = "".join(
            f"<tr><td>Raid completed — {_esc(z)}</td><td class='num'>{d['n']}</td>"
            f"<td class='dim'>{_esc(d['last'])}</td></tr>"
            for z, d in sorted(zev.items(), key=lambda x: -x[1]["n"]))
        trow = (f"<tr><td>Team tasks completed (name unknown — the game's line "
                f"carries none)</td><td class='num'>{task_ticks}</td><td></td></tr>"
                if task_ticks else "")
        early_rows = ("<table><tr><th>Witnessed</th><th class='num'>Count</th>"
                      f"<th>Last seen</th></tr>{zrows}{trow}</table>")
    sync_note = ("<p class='dim'>Character pages (level, badges, accolades, vet levels) "
                 "join the boards when the one-time character sync ships — so a "
                 "multi-year character arrives whole, not as the sliver a fresh capture "
                 "happens to see.</p>" if public else "")
    soon = _card(
        "iTrials · Task Forces · League runs", None,
        early_rows
        + "<p class='dim'>Per-run pages (leader, participants, time, badges earned, ranked "
        "against every recorded run) appear here once the run start/finish and league "
        "join/leader line formats are confirmed from real logs. Capture is watching for "
        "them now — the format hunter flags each new shape it sees.</p>" + sync_note
        + "<p class='tagline'>collecting</p>", cls="full soon")

    # ---- Diagnostic banner (public: no machine path, no account login names) ------------
    if public:
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        shards = state.get("shards") or []
        servers = (f"Servers reporting: <b>{_esc(', '.join(shards))}</b>" if shards
                   else "server reporting arrives with the next client update")
        diag = (f"<div class='card' style='border-color:var(--pulse)'>"
                f"<b>Built from {len(events):,} captured events</b>"
                f"<div class='dim' style='margin-top:6px'>{servers}</div>"
                f"<div class='dim' style='margin-top:2px'>published {stamp} UTC</div>"
                f"</div>")
    else:
        diag = (f"<div class='card' style='border-color:var(--pulse)'>"
                f"<b>Read {len(events):,} events</b> from "
                f"<code style='color:#8fa0bd;font-size:.8rem'>{_esc(src_path)}</code>"
                + ("<div class='dim' style='margin-top:6px'>0 events — logging hasn't written "
                   "anything yet. Run <b>/logchat 1</b> in game (each account) and play a "
                   "little.</div>" if not events else
                   f"<div class='dim' style='margin-top:6px'>{len(accounts)} account(s): "
                   f"{_esc(', '.join(accounts))}</div>") + "</div>")

    # characters + haul are LOCAL ONLY for now (Joel: pointless on the public board
    # until the one-time character sync can bring characters over whole, task #38)
    if public:
        tail_sections = ""
    else:
        tail_sections = ("<h2 style='margin-top:24px'>Your characters</h2>"
                         + scorecards
                         + f"<div class='grid'>{haul_card}{market_card}</div>")

    script = ""
    if public:
        recent_entries = []
        for r in (pulse.get("recent") or []):
            try:
                t = calendar.timegm(time.strptime(r.get("ts") or "",
                                                  "%Y-%m-%d %H:%M:%S"))
            except Exception:  # noqa: BLE001
                continue
            recent_entries.append({"c": r.get("content") or "?", "t": t})
        # sparse per-content (weekday, hour, count) tuples for the click-a-day
        # breakdown — sparse because bounded by actual formations, not the grid
        sparse = {}
        if all_days:
            for content, days in content_day_hours.items():
                tuples = []
                for day, hrs in days.items():
                    if day not in window:
                        continue
                    try:
                        wd = datetime.date.fromisoformat(day).weekday()
                    except ValueError:
                        continue
                    tuples += [[wd, int(h), int(c)] for h, c in hrs.items()
                               if str(h).isdigit()]
                if tuples:
                    sparse[content] = tuples
        data = {"hours": _hour_counts(pulse.get("by_hour") or {}),
                "cats": {k: _hour_counts(v) for k, v in cat_hours.items()},
                "contents": {k: _hour_counts(v) for k, v in content_hours.items()},
                "week": {"all": week_all, "cats": week_cats, "sparse": sparse},
                "catOf": {c: _categorize(c, lx_map) for c in by_content},
                "recent": recent_entries}
        script = ("<script>window.PULSE=" + json.dumps(data) + ";\n"
                  + _PULSE_JS + "</script>")

    if public:
        # direct download of the CURRENT Lite build — the pipeline renders from a fresh
        # site checkout, so this link self-updates with every Lite release
        try:
            with open(os.path.join(ROOT, "lite_version.txt"), encoding="utf-8") as f:
                _lv = f.read().strip()
            dl = ("https://github.com/joelc67/hero-companion/releases/download/"
                  f"lite-v{_lv}/CompanionLite.exe")
            dl_label = f"Companion Lite {_lv}"
        except Exception:  # noqa: BLE001 — frozen/odd layouts fall back to the list
            dl = "https://github.com/joelc67/hero-companion/releases"
            dl_label = "Companion Lite"
        mock = "Alpha · built from live player capture · times shown in your time zone"
        logo_note = "(live)"
        tag = ("Built from game logs captured by players running Companion Lite "
               f"(<a href='{dl}'>download {dl_label}</a> · "
               "<a href='https://github.com/joelc67/hero-companion/releases'>all "
               "releases</a>). Uploads are private and pseudonymized — no account "
               "names, no money, no machine details ever appear here; only these "
               "rendered boards are public.")
        foot = ("Built from game logs captured by players running Companion Lite. Sections "
                "marked \"collecting\" fill in as capture learns the line formats from real "
                "sessions.")
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
{now_card}
{week_card}
{pulse_card}
{cat_cards}
{recent_card}
{tail_sections}
{badge_card}
{soon}
<footer>{foot}</footer>
</div>{script}</body></html>"""
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

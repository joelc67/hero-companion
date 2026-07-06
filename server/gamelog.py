"""In-game chat-log capture — discovery, incremental ingest, parsing, insights (P1).

The game's /logchat writes day files to <game>\\accounts\\<account>\\Logs\\. This module
finds them, tails them incrementally (byte offsets per file, so re-ingest only reads what's
new), and turns lines into structured EVENTS (xp, influence, level-ups, drops, merits,
badges, defeats, auction sales).

⚠ EVERY LINE PATTERN HERE IS PROVISIONAL — written from community knowledge, not yet
validated against a real Homecoming log (the user's first /logchat sample is the
authority). The ingest report therefore counts what DIDN'T parse and keeps samples of
unrecognized "You …" lines, so the first real session tells us exactly what to fix
instead of silently dropping data. Veteran-level lines are a known unknown.
"""
import json
import os
import re
import time

STATE_DIR = None      # set by server.py -> %APPDATA%\HeroCompanion\gamelog


def _state_path():
    return os.path.join(STATE_DIR, "state.json")


def _events_path():
    return os.path.join(STATE_DIR, "events.jsonl")


def load_state():
    try:
        with open(_state_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {"log_dir": None, "offsets": {}}


def save_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(st, f)


# ── discovery ────────────────────────────────────────────────────────────────
def find_log_accounts(accounts_dirs):
    """Every account folder with (or without) a Logs dir, so the UI can offer the
    choice — the user has multiple accounts and picks the one they actually play."""
    out = []
    for base in accounts_dirs or []:
        try:
            entries = sorted(os.listdir(base))
        except Exception:  # noqa: BLE001
            continue
        for name in entries:
            acct = os.path.join(base, name)
            if not os.path.isdir(acct):
                continue
            logdir = os.path.join(acct, "Logs")
            files = []
            if os.path.isdir(logdir):
                files = [f for f in os.listdir(logdir) if f.lower().endswith(".txt")]
            out.append({"account": name, "dir": acct, "log_dir": logdir,
                        "has_logs": bool(files), "log_files": len(files)})
    return out


# ── parsing (VALIDATED against real Homecoming logs, 2026-07-05) ─────────────
# Real formats confirmed from a farm session (Rattle/Lime Juice). Key facts the
# guessed patterns got wrong: DROPS say "You received X" (combat) or "You got X"
# (Consignment House collection); "You have defeated X" is a KILL, not a death;
# influence from sales reads "You got N influence from the Consignment House".
_TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(?P<msg>.*)$")
_N = r"([\d,]+)"


def _num(s):
    return int(s.replace(",", "")) if s else 0


def _drop_kind(item):
    """Categorize a received item by its name (no external salvage list needed)."""
    low = item.lower()
    if item.endswith("(Recipe)") or low.startswith("invention:"):
        return "recipe"
    if "incarnate thread" in low or "incarnate shard" in low:
        return "incarnate"
    if "empyrean" in low or "astral" in low:
        return "incarnate_merit"
    if low.startswith("enhancement catalyst") or low.startswith("enhancement converter"):
        return "crafting"
    if low.startswith(("catalyst:", "awakening:", "boost")):
        return "enhancement"
    return "salvage"        # bare names: Ruby, Gold, Spirit Thorn, Fortune…


_PATTERNS = [
    # (type, regex, extractor)  — order matters; specific before general.
    ("xp", re.compile(rf"^You gain {_N} experience(?: and {_N} (?:influence|infamy))?\.?$", re.I),
     lambda m: {"xp": _num(m.group(1)), "inf": _num(m.group(2))}),
    ("influence_ah", re.compile(rf"^You got {_N} (?:influence|infamy) from the Consignment House\.?$", re.I),
     lambda m: {"inf": _num(m.group(1))}),
    ("spent", re.compile(rf"^You paid {_N} to the Consignment House\.?$", re.I),
     lambda m: {"inf": _num(m.group(1))}),
    ("ah_sold", re.compile(r"^You (?:have )?sold (.+?)\.?$", re.I),
     lambda m: {"item": m.group(1).strip()}),
    ("ah_listed", re.compile(r"^You put (?:\d+ )?(.+?) in the Consignment House\.?$", re.I),
     lambda m: {"item": m.group(1).strip()}),
    ("collect", re.compile(r"^You got (?:\d+ )?(.+?)\.?$", re.I),
     lambda m: {"item": m.group(1).strip()}),
    ("kill", re.compile(r"^You have defeated (.+?)\.?$", re.I),
     lambda m: {"enemy": m.group(1).strip()}),
    ("death", re.compile(r"^You have been defeated(?: by (.+?))?\.?$", re.I),
     lambda m: {"by": (m.group(1) or "").strip() or None}),
    ("merits", re.compile(rf"^You (?:have been awarded|are awarded|receive) {_N} (?:reward )?merits?\.?$", re.I),
     lambda m: {"merits": _num(m.group(1))}),
    ("level", re.compile(r"^(?:Welcome to level|You are now level|You have reached level) (\d+)", re.I),
     lambda m: {"level": int(m.group(1))}),
    ("badge", re.compile(r"^(?:Congratulations! )?You (?:have )?(?:earned|received) the (.+?) [Bb]adge", re.I),
     lambda m: {"badge": m.group(1).strip()}),
    ("drop", re.compile(r"^You received (.+?)\.?$", re.I),
     lambda m: {"item": m.group(1).strip(), "kind": _drop_kind(m.group(1).strip())}),
    # The game announces the active character on each fresh login — this is how we know
    # WHO is playing, and it marks a character switch within an account's log.
    ("char", re.compile(r"^Welcome to City of Heroes, (.+?)!\s*$"),
     lambda m: {"character": m.group(1).strip()}),
]

# Known-NOISE lines (combat, buffs, status, MOTD, chat) — recognized so the coverage
# report does NOT flag them. Built against the real farm log's actual chatter (Brute
# Taunt spam, heals, Fury, Sprint, login MOTD). Reward verbs are parsed BEFORE this
# check, so a broad "You gain/heal/Taunt…" here can't swallow xp/drops/kills/sales.
_NOISE = re.compile(
    r"^(You \w+ .+ with (your|the) |"                    # any "You <verb> <target> with your <power>"
    r"You (are |hit |miss|heal |[Tt]aunt |activate|increase|decrease|gain \d|"
    r"can'?t? |may |have \d|have (Insight|Keen|Uncanny|Robust|Rugged|Enrage|Focused|"
    r"Righteous|Sturdy|good |the power)|don't|feel|start to|now have|conjure|summon|"
    r"throw|unleash|place|slot|enter|do |knock|interrupt|were|contaminate|disorient|"
    r"hold|immobilize|confuse|terrorize|placate|stun|sap|absorb|Take a|Catch a|undergo|"
    r"think|rated|revive|resurrect|awaken)|"
    r"HIT |MISS |Your |A |An |The |.+ (hits you|HITS you|MISSES you|heals you|"
    r"misses you|grants you|is |was |has |begins|patrol|appeared)|"
    r"Entering |Now entering|Joined channel|Left channel|Passcode |"
    r"\[|.+: <(color|bgcolor))", re.I)


def parse_line(line):
    """(event dict | None, interesting). `interesting` flags an UNPARSED line that looks
    like it carries reward data but matched no pattern AND isn't known noise — those are
    the samples the coverage report surfaces so real logs keep improving the parser."""
    m = _TS.match(line.strip())
    if not m:
        return None, False
    msg = m.group("msg")
    for etype, rex, extract in _PATTERNS:
        h = rex.match(msg)
        if h:
            ev = {"ts": m.group(1), "type": etype}
            ev.update(extract(h))
            return ev, True
    if _NOISE.match(msg):
        return None, False
    # Unrecognized but genuinely REWARD-shaped — the things the parser might be missing
    # (merits, veteran levels, badges, accolades) or an unhandled gain/receipt verb.
    # Deliberately NOT keyed on bare "defeat/influence/experience" — those are already
    # parsed, and AE farm mobs spew flavor text full of "defeat".
    interesting = bool(re.search(r"\b(merit|veteran|badge|accolade|component)\b", msg, re.I)) \
        or bool(re.match(r"^You (gain \d|got |received |earned |have earned|have been awarded)", msg))
    return None, interesting


def ingest(log_dir, state):
    """Read every log file's NEW bytes (byte offset per file), append events, return a
    report. BINARY read + seek-to-end so it works LIVE while the game holds the file open
    (the game shares the handle for reading; a partial trailing line is left for next
    poll). Incremental and idempotent."""
    events, report = [], {"files": 0, "new_lines": 0, "parsed": 0,
                          "unparsed_interesting": 0, "unparsed_samples": []}
    if not (log_dir and os.path.isdir(log_dir)):
        return events, report
    offsets = state.setdefault("offsets", {})
    account = os.path.basename(os.path.dirname(log_dir))   # <game>\accounts\<acct>\Logs
    for fname in sorted(os.listdir(log_dir)):
        if not fname.lower().endswith(".txt"):
            continue
        path = os.path.join(log_dir, fname)
        try:
            start = int(offsets.get(path, 0))
            with open(path, "rb") as f:
                f.seek(0, 2)
                size = f.tell()
                if start > size:                 # rotated/truncated — start over
                    start = 0
                if start >= size:
                    continue
                f.seek(start)
                chunk = f.read()
            nl = chunk.rfind(b"\n")
            if nl == -1:                         # only a partial line so far — wait
                continue
            complete = chunk[:nl + 1]
            offsets[path] = start + len(complete)
            report["files"] += 1
            for line in complete.decode("utf-8", "replace").splitlines():
                report["new_lines"] += 1
                ev, interesting = parse_line(line)
                if ev:
                    ev["file"] = fname
                    ev["account"] = account
                    events.append(ev)
                    report["parsed"] += 1
                    if ev["type"] == "char":
                        # This account's CURRENT character = the last Welcome seen. Kept
                        # per account so a dual-boxer's two clients don't overwrite each other.
                        state.setdefault("characters", {})[account] = ev["character"]
                elif interesting:
                    report["unparsed_interesting"] += 1
                    if len(report["unparsed_samples"]) < 20:
                        report["unparsed_samples"].append(line.strip()[:160])
        except Exception:  # noqa: BLE001 — one unreadable file never blocks the rest
            continue
    if events:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_events_path(), "a", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
    return events, report


def log_status(log_dir, now):
    """Best-effort 'is logging on?' signal for the UI: the newest log file, how long ago
    it changed, and whether one exists for today. We can't see whether the game is
    running, so we report facts and let the UI nudge — never a false alarm."""
    if not (log_dir and os.path.isdir(log_dir)):
        return {"has_files": False}
    files = [f for f in os.listdir(log_dir) if f.lower().endswith(".txt")]
    if not files:
        return {"has_files": False}
    newest = max(files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
    mtime = os.path.getmtime(os.path.join(log_dir, newest))
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    return {"has_files": True, "newest": newest,
            "age_sec": max(0, int(now - mtime)),
            "today_log": any(today in f for f in files)}


def load_events(limit=20000):
    out = []
    try:
        with open(_events_path(), encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except Exception:  # noqa: BLE001
                    continue
    except FileNotFoundError:
        return []
    return out[-limit:]


def _blank_summary():
    return {"xp": 0, "inf_gained": 0, "inf_spent": 0, "merits": 0, "levels": [],
            "badges": [], "kills": 0, "deaths": 0, "drops": [], "ah_sold": 0,
            "drop_kinds": {}, "days": set()}


def summarize(events, accounts=None):
    """Aggregate events into the insight card's numbers. If `accounts` (a set/list) is
    given, only those accounts' events count. Attributes events to the CHARACTER active at
    the time (from 'Welcome to City of Heroes, X!' markers) so the Play Log can break stats
    out per character — keyed by account so simultaneous dual-boxed characters never
    cross-attribute."""
    acc = set(accounts) if accounts else None
    evs = [e for e in events if acc is None or e.get("account") in acc]
    evs.sort(key=lambda e: (e.get("ts") or "", e.get("account") or ""))
    s = _blank_summary()
    by_char, cur = {}, {}          # by_char[name] -> summary ; cur[account] -> character
    characters = []                # order-of-appearance list of names seen
    for ev in evs:
        t = ev["type"]
        acct = ev.get("account")
        if t == "char":
            cur[acct] = ev["character"]
            if ev["character"] not in by_char:
                by_char[ev["character"]] = _blank_summary()
                characters.append(ev["character"])
            continue
        who = cur.get(acct)
        targets = [s] + ([by_char[who]] if who and who in by_char else [])
        for tgt in targets:
            _tally(tgt, ev)
    s["days"] = sorted(s["days"])
    s["max_level"] = max([x for x in s["levels"] if x], default=None)
    per = {}
    for name, cs in by_char.items():
        cs["days"] = sorted(cs["days"])
        cs["max_level"] = max([x for x in cs["levels"] if x], default=None)
        per[name] = {k: v for k, v in cs.items() if k != "drops"}
    s["by_character"] = per
    s["characters"] = characters
    return s


def _tally(s, ev):
    """Fold ONE reward event into a running summary dict (used for both the overall and
    the per-character totals)."""
    t = ev["type"]
    s["days"].add((ev.get("ts") or "")[:10])
    if t == "xp":
        s["xp"] += ev.get("xp", 0)
        s["inf_gained"] += ev.get("inf", 0)
    elif t == "influence_ah":
        s["inf_gained"] += ev.get("inf", 0)
    elif t == "spent":
        s["inf_spent"] += ev.get("inf", 0)
    elif t == "level":
        s["levels"].append(ev.get("level"))
    elif t == "merits":
        s["merits"] += ev.get("merits", 0)
    elif t == "badge":
        s["badges"].append(ev.get("badge"))
    elif t == "kill":
        s["kills"] += 1
    elif t == "death":
        s["deaths"] += 1
    elif t == "ah_sold":
        s["ah_sold"] += 1
    elif t == "drop":
        s["drops"].append(ev)
        k = ev.get("kind", "salvage")
        s["drop_kinds"][k] = s["drop_kinds"].get(k, 0) + 1

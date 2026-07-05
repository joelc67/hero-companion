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


# ── parsing (PROVISIONAL patterns — see module docstring) ────────────────────
_TS = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(?:\s+\[(?P<chan>[^\]]+)\])?\s+(?P<msg>.*)$")
_N = r"([\d,]+)"


def _num(s):
    return int(s.replace(",", "")) if s else 0


_PATTERNS = [
    # (type, regex, extractor)  — extractor(match) -> event fields
    ("xp", re.compile(rf"You gain {_N} experience(?: and {_N} (?:influence|infamy|information))?[.,]?", re.I),
     lambda m: {"xp": _num(m.group(1)), "inf": _num(m.group(2))}),
    ("inf", re.compile(rf"You gain {_N} (?:influence|infamy|information)[.,]?", re.I),
     lambda m: {"inf": _num(m.group(1))}),
    ("level", re.compile(r"You are now (?:a )?level (\d+)|You have reached level (\d+)", re.I),
     lambda m: {"level": int(m.group(1) or m.group(2))}),
    ("vet_level", re.compile(r"[Vv]eteran [Ll]evel\s*(\d+)?"),
     lambda m: {"vet_level": int(m.group(1)) if m.group(1) else None}),
    ("merits", re.compile(rf"You (?:have been awarded|are awarded|received) {_N} [Rr]eward [Mm]erits?", re.I),
     lambda m: {"merits": _num(m.group(1))}),
    ("badge", re.compile(r"(?:Congratulations! )?[Yy]ou (?:have )?earned the (.+?) [Bb]adge", re.I),
     lambda m: {"badge": m.group(1).strip()}),
    ("defeat", re.compile(r"You have been defeated(?: by (.+?))?[.!]?$", re.I),
     lambda m: {"by": (m.group(1) or "").strip() or None}),
    ("ah_sold", re.compile(rf"You (?:have )?sold (.+?) for {_N} (?:influence|infamy|inf)\b", re.I),
     lambda m: {"item": m.group(1).strip(), "price": _num(m.group(2))}),
    ("ah_bought", re.compile(rf"You (?:have )?bought (.+?) for {_N} (?:influence|infamy|inf)\b", re.I),
     lambda m: {"item": m.group(1).strip(), "price": _num(m.group(2))}),
    ("drop", re.compile(r"You (?:received|found) (.+?)(\s*\((?:Recipe|Salvage)\))?\.?$", re.I),
     lambda m: {"item": m.group(1).strip(),
                "kind": (m.group(2) or "").strip(" ()").lower() or "enhancement"}),
]


def parse_line(line):
    """(event dict | None, interesting) — `interesting` marks unparsed lines that LOOK
    like they carry data ("You …"), which the coverage report samples for format fixes."""
    m = _TS.match(line.strip())
    if not m:
        return None, False
    msg = m.group("msg")
    for etype, rex, extract in _PATTERNS:
        h = rex.search(msg)
        if h:
            ev = {"ts": m.group(1), "type": etype}
            ev.update(extract(h))
            return ev, True
    return None, msg.startswith("You ") or "eteran" in msg


def ingest(log_dir, state):
    """Read every log file's NEW bytes (per-file offset), append events, return a report.
    Incremental and idempotent — running it twice ingests nothing the second time."""
    events, report = [], {"files": 0, "new_lines": 0, "parsed": 0,
                          "unparsed_interesting": 0, "unparsed_samples": []}
    if not (log_dir and os.path.isdir(log_dir)):
        return events, report
    offsets = state.setdefault("offsets", {})
    for fname in sorted(os.listdir(log_dir)):
        if not fname.lower().endswith(".txt"):
            continue
        path = os.path.join(log_dir, fname)
        try:
            size = os.path.getsize(path)
            start = offsets.get(path, 0)
            if start > size:                     # rotated/truncated — start over
                start = 0
            if start == size:
                continue
            report["files"] += 1
            with open(path, encoding="utf-8", errors="replace") as f:
                f.seek(start)
                for line in f:
                    report["new_lines"] += 1
                    ev, interesting = parse_line(line)
                    if ev:
                        ev["file"] = fname
                        events.append(ev)
                        report["parsed"] += 1
                    elif interesting:
                        report["unparsed_interesting"] += 1
                        if len(report["unparsed_samples"]) < 20:
                            report["unparsed_samples"].append(line.strip()[:160])
                offsets[path] = f.tell()
        except Exception:  # noqa: BLE001 — one unreadable file never blocks the rest
            continue
    if events:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_events_path(), "a", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
    return events, report


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


def summarize(events):
    """Aggregate events into the insight card's numbers (all-time within the store)."""
    s = {"xp": 0, "inf_gained": 0, "inf_spent": 0, "merits": 0, "levels": [],
         "vet_levels": 0, "badges": [], "defeats": 0, "drops": [],
         "ah_sold": [], "ah_bought": [], "days": set()}
    for ev in events:
        s["days"].add((ev.get("ts") or "")[:10])
        t = ev["type"]
        if t == "xp":
            s["xp"] += ev.get("xp", 0)
            s["inf_gained"] += ev.get("inf", 0)
        elif t == "inf":
            s["inf_gained"] += ev.get("inf", 0)
        elif t == "level":
            s["levels"].append(ev.get("level"))
        elif t == "vet_level":
            s["vet_levels"] += 1
        elif t == "merits":
            s["merits"] += ev.get("merits", 0)
        elif t == "badge":
            s["badges"].append(ev.get("badge"))
        elif t == "defeat":
            s["defeats"] += 1
        elif t == "drop":
            s["drops"].append(ev)
        elif t == "ah_sold":
            s["ah_sold"].append(ev)
            s["inf_gained"] += ev.get("price", 0)
        elif t == "ah_bought":
            s["ah_bought"].append(ev)
            s["inf_spent"] += ev.get("price", 0)
    s["days"] = sorted(s["days"])
    s["max_level"] = max([x for x in s["levels"] if x], default=None)
    return s

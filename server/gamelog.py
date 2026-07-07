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


# ── single-ingester lock: full app and Companion Lite share ONE capture store ─────────
# Both processes tail the same log files with the same byte offsets; two ingesters would
# race the offsets and duplicate or drop events. Whoever holds this heartbeat lock ingests;
# the other reads events.jsonl freely (reading needs no lock). Stale after 90s, so a
# crashed owner never wedges capture.
_OWNER_TTL = 90


def _owner_path():
    return os.path.join(STATE_DIR, "ingest_owner.json")


def acquire_ingest(tag):
    """True if this process may ingest (it becomes/refreshes the owner). `tag` names the
    owner for status display ('full' | 'lite')."""
    os.makedirs(STATE_DIR, exist_ok=True)
    now = time.time()
    me = {"pid": os.getpid(), "tag": tag, "ts": now}
    try:
        with open(_owner_path(), encoding="utf-8") as f:
            cur = json.load(f)
        if cur.get("pid") != me["pid"] and (now - float(cur.get("ts", 0))) < _OWNER_TTL:
            return False                 # someone else holds it, and their heartbeat is fresh
    except Exception:  # noqa: BLE001 — no owner file yet
        pass
    with open(_owner_path(), "w", encoding="utf-8") as f:
        json.dump(me, f)
    return True


def ingest_owner():
    """Current owner record, or None — for status display ('captured by Companion Lite')."""
    try:
        with open(_owner_path(), encoding="utf-8") as f:
            cur = json.load(f)
        if (time.time() - float(cur.get("ts", 0))) < _OWNER_TTL:
            return cur
    except Exception:  # noqa: BLE001
        pass
    return None


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
    # real Homecoming format LEARNED from Joel's logs 2026-07-07 ("Your combat improves
    # to level 50! Seek a trainer..."); the earlier alternatives were guesses kept as
    # fallbacks for other message paths
    ("level", re.compile(r"^(?:Your combat improves to level|Welcome to level"
                         r"|You are now level|You have reached level) (\d+)", re.I),
     lambda m: {"level": int(m.group(1))}),
    # AH-open pending summary ("You have 0 bought and 1 sold items in the Consignment
    # House.") — sales that completed while offline announce themselves here
    ("ah_status", re.compile(r"^You have (\d+) bought and (\d+) sold items? in the "
                             r"Consignment House", re.I),
     lambda m: {"bought": int(m.group(1)), "sold": int(m.group(2))}),
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


# ── pulse capture: recruitment facts from public channels (the Lite-in-full core) ────
# Format PROVEN by a real log line:
#   2026-07-05 17:16:36 [Looking For Group] Bunny Emerald: <color #010101>forming +2 numina...
# Only STRUCTURED recruitment facts become events (channel, speaker, content, spots,
# difficulty) — general conversation is never stored, even locally. Gated by the
# pulse_capture state flag: channel capture is its own consent, per the choice doctrine.
_LEXICON = None


def _lexicon():
    global _LEXICON
    if _LEXICON is None:
        import sys as _s
        if getattr(_s, "frozen", False):
            base = os.path.join(getattr(_s, "_MEIPASS", os.path.dirname(_s.executable)), "data")
        else:
            base = os.path.join(os.path.dirname(__file__), "..", "data")
        try:
            with open(os.path.join(base, "chat_lexicon.json"), encoding="utf-8") as f:
                _LEXICON = json.load(f)
        except Exception:  # noqa: BLE001
            _LEXICON = {"channels": [], "content_aliases": {}, "patterns": {}}
    return _LEXICON


_CHAN_RX = re.compile(r"^\[([^\]]+)\]\s+([^:]{1,40}):\s*(.*)$")
_TAG_RX = re.compile(r"<[^>]{1,40}>")

# PUBLIC recruitment channels — a line here IS recruitment activity (that's the channel's
# job), so we capture it generously and LEARN the content rather than demanding it match a
# pre-baked pattern. Matched case-insensitively and by substring so "Looking For Group",
# "LFG", "Help", global recruiting channels etc. all count.
_PUBLIC_RECRUIT = ("looking for group", "lfg", "broadcast", "request", "help",
                   "coalition", "supergroup")
# PRIVATE channels — NEVER captured, even locally. A tell/whisper is between two people.
_PRIVATE_CHANS = ("tell", "whisper", "private", "friend")
# Words that mean "a group is forming / needs people" — the signal that a line is active
# recruitment (vs. someone just chatting in the channel).
_RECRUIT_HINT = re.compile(
    r"\b(lf\d*m?|forming|starting|need\s|needs\s|spots?|lfg|lft|lf\b|"
    r"\d+\s*/\s*\d+|\+\d|inv\b|invite|join|join up|@)\b", re.I)
_STOPWORDS = frozenset(
    "the a an to for of and or in on at is are be we you your my me it this that with "
    "any all get got new lvl level lfm lf2m lf3m lf4m lf5m lf6m lf7m lf8m lf lfg lft lfm "
    "up now run go come please pst tell inv invite join star".split())


def parse_channel_line(msg):
    """A recruitment EVENT from a PUBLIC channel, or None. Never keeps raw chat — only
    structured facts leave here. Private messages (tells/whispers) are excluded outright."""
    lx = _lexicon()
    h = _CHAN_RX.match(msg)
    if not h:
        return None
    channel, speaker, text = h.group(1), h.group(2).strip(), _TAG_RX.sub("", h.group(3))
    clow = channel.lower()
    if any(p in clow for p in _PRIVATE_CHANS):
        return None                                  # private — never captured, always wins
    # public recruitment channels = the built-in list PLUS the lexicon pack's channels
    # (hub-updatable: shard globals where raids/iTrials organize get added there)
    pubs = _PUBLIC_RECRUIT + tuple(c.lower() for c in (lx.get("channels") or []))
    if not any(p in clow for p in pubs):
        return None                                  # not a recruitment channel
    low = " " + text.lower() + " "
    if re.search(r"\bfull\b", low):
        # The speaker saying "full" CLOSES their open recruitment (Joel's rule) — their
        # next ask is a NEW formation (e.g. back-to-back DFB runs). Structured fact only;
        # the marker is consumed by episode-collapsing and never counted itself.
        return {"type": "recruit_full", "channel": channel, "speaker": speaker}
    if not _RECRUIT_HINT.search(low):
        return None                                  # channel chatter, not a group forming

    # LEARN the content: prefer a known lexicon alias; else derive a label from the line's
    # own salient words so unknown trials/TFs still classify AND grow the discovered list.
    # LONGEST alias first — "posi 2" must win over "posi", "ice mistral" over "ice"
    # (file order once let the short alias eat every Part 1/Part 2 ask).
    if "_alias_order" not in lx:
        lx["_alias_order"] = sorted((lx.get("content_aliases") or {}).items(),
                                    key=lambda kv: -len(kv[0]))
    content, master = None, False
    for alias, full in lx["_alias_order"]:
        if re.search(rf"\b{re.escape(alias)}\b", low):
            content = full
            master = bool(re.search(
                rf"\b{lx.get('master_prefix', 'mo')}\s*{re.escape(alias)}\b", low))
            break
    if content and master:
        content = "Master of " + content
    learned = None
    if not content:
        # discovered nomenclature: the first salient token that ISN'T a stopword or an
        # archetype/role word (the AT someone SEEKS is not the content of the run).
        at_words = set(lx.get("at_words") or [])
        toks = [t for t in re.findall(r"[a-z][a-z'&+-]{2,}", text.lower())
                if t not in _STOPWORDS and t not in at_words]
        learned = toks[0] if toks else None
        content = ("recruiting: " + learned) if learned else "recruiting (general)"

    pats = lx.get("patterns", {})
    ev = {"type": "recruit", "channel": channel, "speaker": speaker, "content": content,
          "forming": bool(re.search(r"\bforming|starting\b", low)),
          "learned_term": learned}                   # feeds the discovered-nomenclature tally
    m_spots = re.search(pats.get("spots_needed", r"\blf\s*(\d+)\s*m"), low)
    m_slash = re.search(pats.get("spots_slash", r"\b(\d{1,2})\s*/\s*(\d{1,2})\b"), low)
    m_diff = re.search(pats.get("difficulty", r"\+(\d)\b"), low)
    if m_spots:
        ev["spots_needed"] = int(m_spots.group(1))
    if m_slash:
        ev["spots_filled"], ev["spots_total"] = int(m_slash.group(1)), int(m_slash.group(2))
    if m_diff:
        ev["difficulty"] = int(m_diff.group(1))
    return ev


def parse_line(line, pulse=False):
    """(event dict | None, interesting). `interesting` flags an UNPARSED line that looks
    like it carries reward data but matched no pattern AND isn't known noise — those are
    the samples the coverage report surfaces so real logs keep improving the parser."""
    m = _TS.match(line.strip())
    if not m:
        return None, False
    msg = m.group("msg")
    if pulse:
        if msg.startswith("["):
            ev = parse_channel_line(msg)
            if ev:
                ev["ts"] = m.group(1)
                return ev, True
        # FORMAT HUNTER: league/team lifecycle lines (joins, leader changes) have no
        # validated format yet — surface candidates (bracketed or not, in either word
        # order, before the noise gate can swallow them) so the first real sighting
        # teaches the parser.
        if (re.search(r"\b(league|team)\b", msg, re.I)
                and re.search(r"\b(join(?:ed)?|quit|left|lead(?:er|ing)?)\b", msg, re.I)):
            return None, True
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
    # Public broadcast channels (LFG/Broadcast/Request/Coalition/SG) captured LOCALLY as
    # structured facts default ON — the meaningful consent is SHARING (a separate manual
    # publish), not local capture. The toggle still lets anyone opt out (remembered).
    pulse = state.get("pulse_capture", True) is not False
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
                ev, interesting = parse_line(line, pulse=pulse)
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
    # SHARD AUTO-DETECT (Joel's insight): the client maintains playerslot.txt beside
    # Logs — `"account" "Shard" "Character" "slot"` per character. Look up this
    # account's current character and remember its shard: capture becomes server-
    # attributable with zero configuration. Only WITNESSED characters are recorded —
    # the roster itself is never stored or uploaded.
    cur = (state.get("characters") or {}).get(account)
    if cur and cur not in (state.get("char_shards") or {}):
        shard = _playerslots(log_dir).get(cur)
        if shard:
            state.setdefault("char_shards", {})[cur] = shard
    if events:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(_events_path(), "a", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev) + "\n")
    return events, report


_SLOT_CACHE = {}


def _playerslots(log_dir):
    """character -> shard from the account's playerslot.txt (the client-maintained
    roster living beside Logs). Cached by mtime; missing/unreadable = empty map."""
    path = os.path.join(os.path.dirname(log_dir), "playerslot.txt")
    try:
        mt = os.path.getmtime(path)
    except OSError:
        return {}
    cached = _SLOT_CACHE.get(path)
    if cached and cached[0] == mt:
        return cached[1]
    roster = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                fields = re.findall(r'"([^"]*)"', line)
                if len(fields) >= 3 and fields[1] and fields[2]:
                    roster[fields[2]] = fields[1]
    except Exception:  # noqa: BLE001
        roster = {}
    _SLOT_CACHE[path] = (mt, roster)
    return roster


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
            "drop_kinds": {}, "days": set(),
            "pulse": {"recruit_seen": 0, "by_content": {}, "recent": [],
                      "by_channel": {}, "learned_terms": {}, "by_hour": {},
                      "content_hours": {}, "content_day_hours": {}}}


def _ts_epoch(ts):
    """Event timestamp string -> epoch seconds, or None if unparseable."""
    try:
        import calendar
        return calendar.timegm(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))
    except Exception:  # noqa: BLE001
        return None


RECRUIT_EPISODE_GAP = 600     # 10 min of silence = the next ask is a NEW formation


def _collapse_recruits(evs):
    """ONE FORMATION = ONE SIGHTING (Joel's rules, from watching real LFG):

    - Spam collapse: a recruiter re-asking for the same content ("lf2m dfb" every 40s
      until filled) is ONE formation, not one per shout. An episode is keyed by
      (speaker, content) — channel ignored, so cross-posting LFG+Broadcast is still one
      formation — and each repeat EXTENDS it.
    - "full" closes: the speaker saying full means the team filled; their next ask is a
      NEW formation (back-to-back DFB runs). The marker itself is never counted.
    - 10-minute silence closes: no re-ask for RECRUIT_EPISODE_GAP = they're done or
      running it again — the next ask counts fresh.
    - Dual-box falls out for free: your second client's copy of the same shout lands
      inside the episode (same speaker+content, seconds apart) and is absorbed.

    Expects evs sorted by ts."""
    out, open_ep = [], {}          # (speaker, content) -> epoch of the last ask
    for e in evs:
        t = e.get("type")
        if t == "recruit_full":
            for k in [k for k in open_ep if k[0] == e.get("speaker")]:
                open_ep.pop(k)
            continue                                 # marker consumed, never counted
        if t != "recruit":
            out.append(e)
            continue
        key = (e.get("speaker"), e.get("content"))
        ts, last = _ts_epoch(e.get("ts") or ""), open_ep.get(key)
        if (last is not None and ts is not None
                and 0 <= ts - last < RECRUIT_EPISODE_GAP):
            open_ep[key] = ts                        # spam extends, never re-counts
            continue
        open_ep[key] = ts
        out.append(e)
    return out


def summarize(events, accounts=None):
    """Aggregate events into the insight card's numbers. If `accounts` (a set/list) is
    given, only those accounts' events count. Attributes events to the CHARACTER active at
    the time (from 'Welcome to City of Heroes, X!' markers) so the Play Log can break stats
    out per character — keyed by account so simultaneous dual-boxed characters never
    cross-attribute."""
    acc = set(accounts) if accounts else None
    evs = [e for e in events if acc is None or e.get("account") in acc]
    evs.sort(key=lambda e: (e.get("ts") or "", e.get("account") or ""))
    evs = _collapse_recruits(evs)
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
    elif t == "recruit":
        pu = s["pulse"]
        pu["recruit_seen"] += 1
        key = ev.get("content") or "(unrecognized content)"
        pu["by_content"][key] = pu["by_content"].get(key, 0) + 1
        ch = ev.get("channel") or "?"
        pu["by_channel"][ch] = pu["by_channel"].get(ch, 0) + 1
        hr = (ev.get("ts") or "")[11:13]
        if hr.isdigit():                              # busiest-times histograms
            pu["by_hour"][int(hr)] = pu["by_hour"].get(int(hr), 0) + 1
            ch_hours = pu["content_hours"].setdefault(key, {})
            ch_hours[int(hr)] = ch_hours.get(int(hr), 0) + 1
            # day-granular (feeds the last-7-days weekday × hour heatmap)
            dh = pu["content_day_hours"].setdefault(key, {}).setdefault(
                (ev.get("ts") or "")[:10], {})
            dh[int(hr)] = dh.get(int(hr), 0) + 1
        lt = ev.get("learned_term")
        if lt:                                        # discovered nomenclature, tallied
            pu["learned_terms"][lt] = pu["learned_terms"].get(lt, 0) + 1
        # keep the LATEST 60 (events arrive ts-sorted; capping at the first N froze the
        # card on the oldest sightings ever captured — the opposite of "recent")
        pu["recent"].append({k: ev.get(k) for k in
                             ("ts", "channel", "content", "spots_needed",
                              "spots_filled", "spots_total", "difficulty")})
        if len(pu["recent"]) > 60:
            pu["recent"].pop(0)

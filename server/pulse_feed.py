"""Pulse Boards feed + local boards for the FULL Hero Companion app.

Joel's parity order (2026-07-12): everything Companion Lite can do, the full
app can do — this module ports Lite's three exclusive features:

  1. build the PRIVATE local board (your scorecards/market ledger/raids —
     never uploaded) from the shared capture store;
  2. build the PUBLIC-variant preview (exactly what would be shared);
  3. feed the live Pulse Boards, under the identical consent model.

FAITHFUL PORT of run_lite.py's feed machinery, kept STATE-COMPATIBLE with
Lite on purpose: same shared-state keys (terms_version, install_id,
upload_offset, state_upload_hash), same offset-named retry-safe chunk files,
same pseudonymization — so the full app and Lite interoperate on one machine
without double-sending a byte (whoever uploads advances the same offset, and
a re-sent chunk overwrites its own name). Lite 0.1.17 should adopt this
module so the logic lives once (noted in the queue; Lite releases are
decoupled, so run_lite.py keeps its copy until its own cut).

CONSENT (Joel's model, unchanged from Lite): the TERMS are the consent —
uploads never start before the terms have been shown once at the current
version. The full app shows them in the Play Log tab. The upload key ships
only in RELEASE builds (data/inbox_key.bin, obfuscated, gitignored); source
runs and forks have no key and the feed is structurally inert.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamelog  # noqa: E402

TERMS_VERSION = 2   # keep in lockstep with run_lite.py — same consent, one version
TERMS = """Hero Companion can feed the live CoH Pulse Boards. Turning the
feed on means you accept these terms.

WHAT IT CAPTURES (from your game chat log, only while logging is on):
  - your own rewards: XP, influence, drops, merits, badges, defeats
  - recruitment facts from public channels (what's forming, and the
    recruiting CHARACTER's name — it was broadcast publicly in game).
    Never raw chat. Private messages (tells, whispers) are never
    captured.
  - your auction-house lines, so confirmed per-item SALE PRICES can
    feed the public price board.

WHAT IT UPLOADS: that captured play data, and nothing else. Uploads are
tagged with an anonymous install id. Your own CHARACTER names (as the
game announces them) are included so your data can be attributed to
your characters; they are not shown publicly today. Your account login
names never leave this machine (they are replaced with meaningless
codes first). Machine names, file paths, and anything outside the game
log are never read or sent.

WHERE IT GOES: into the project's locked storage that the general
public cannot read. What the PUBLIC board shows: what's forming and
when, the character names of public-channel recruiters (public in game
already), and per-item sale prices. It never shows account names,
anyone's money totals, who sold what, or machine details.

YOUR CONTROLS: turn game logging off any time (/logchat in game) and
nothing is captured; turn the feed off here and nothing is uploaded.
That is the whole agreement."""

UPLOAD_SECONDS = 300
_INBOX_REPO = "joelc67/hero-companion-inbox"
_stats = {}


def _data_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(getattr(sys, "_MEIPASS",
                                    os.path.dirname(sys.executable)), "data")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data")


def inbox_token():
    """The product's upload key — scoped to the private inbox repo ONLY. Bundled
    obfuscated at release build time (data/inbox_key.bin, gitignored); absent in
    source runs and forks, which leaves the feed inert."""
    try:
        with open(os.path.join(_data_dir(), "inbox_key.bin"), "rb") as f:
            raw = f.read()
        return bytes(b ^ 0x5A for b in raw).decode("ascii").strip() or None
    except Exception:  # noqa: BLE001
        return None


def _install_id(st):
    """Anonymous per-install id — never a hostname or username. Shared with Lite."""
    iid = st.get("install_id")
    if not iid:
        import uuid
        iid = uuid.uuid4().hex[:16]
        st["install_id"] = iid
        gamelog.save_state(st)
    return iid


def _gh_request(method, path, body=None):
    import urllib.request
    req = urllib.request.Request(
        f"https://api.github.com/repos/{_INBOX_REPO}/{path}",
        data=json.dumps(body).encode("utf-8") if body is not None else None,
        headers={"Authorization": f"token {inbox_token()}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": "HeroCompanion"},
        method=method)
    import urllib.request as _ur
    with _ur.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def _inbox_put(path, data, message, need_sha=False):
    import base64
    body = {"message": message,
            "content": base64.b64encode(data).decode("ascii")}
    if need_sha:
        try:
            body["sha"] = _gh_request("GET", f"contents/{path}").get("sha")
        except Exception:  # noqa: BLE001 — file doesn't exist yet: create it
            pass
    _gh_request("PUT", f"contents/{path}", body)


def _pseudonym(iid, account):
    import hashlib
    return "a" + hashlib.sha256(f"{iid}|{account}".encode("utf-8")).hexdigest()[:12]


def _anonymize_chunk(chunk, iid):
    out = []
    for line in chunk.decode("utf-8", "replace").splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
            if ev.get("account"):
                ev["account"] = _pseudonym(iid, ev["account"])
            out.append(json.dumps(ev))
        except Exception:  # noqa: BLE001 — an unparseable line is dropped, never leaked
            continue
    return ("\n".join(out) + "\n").encode("utf-8") if out else b""


def maybe_upload():
    """Identical semantics to Lite's _maybe_upload — see module docstring. Safe
    to call after every ingest; it self-limits to one upload per UPLOAD_SECONDS
    and returns silently without key or consent."""
    st = gamelog.load_state()
    if not inbox_token() or st.get("terms_version", 0) < TERMS_VERSION:
        return
    # Choice doctrine, TIGHTENED (Pulse diagnostic 6a, 2026-07-15): unlike Lite
    # (whose whole job is feeding, so using it IS the consent), the full app is
    # a build planner first — its feed is an explicit, REVERSIBLE opt-in. The
    # old gate (`feed_disabled` absent = upload) leaked consent ACROSS APPS: on
    # a machine where LITE's terms were accepted, the full app uploaded without
    # its own opt-in ever being shown. The full app now uploads only when its
    # own toggle was explicitly answered YES (feed_disabled present and False —
    # set_feed_enabled(True) writes exactly that). Absent = this app was never
    # asked = it does not upload. Lite 0.1.17 respects feed_disabled=True as
    # the shared remembered "no", as promised here.
    if st.get("feed_disabled") is not False:
        return
    if time.time() - _stats.get("uploaded_ts", 0) < UPLOAD_SECONDS:
        return
    # ONE uploader per store (6a): never race a co-running Lite's offset.
    if not gamelog.acquire_upload("full"):
        return
    src = os.path.join(gamelog.STATE_DIR, "events.jsonl")
    size = os.path.getsize(src) if os.path.isfile(src) else 0
    offset = int(st.get("upload_offset", 0))
    if offset > size:
        import uuid
        st["install_id"] = uuid.uuid4().hex[:16]
        st["upload_offset"] = offset = 0
        gamelog.save_state(st)
    if size == 0 or size == offset:
        return
    _stats["uploaded_ts"] = time.time()
    try:
        with open(src, "rb") as f:
            f.seek(offset)
            chunk = f.read()
        if not chunk.endswith(b"\n"):                  # never ship a torn last line
            cut = chunk.rfind(b"\n")
            if cut < 0:
                return
            chunk = chunk[:cut + 1]
        sent = len(chunk)
        iid = _install_id(st)
        chunk = _anonymize_chunk(chunk, iid)
        if not chunk:
            return
        _inbox_put(f"sources/{iid}/c{offset:012d}.jsonl", chunk,
                   f"capture from {iid}", need_sha=True)
        chars = {_pseudonym(iid, a): c
                 for a, c in (st.get("characters") or {}).items()}
        char_shards = st.get("char_shards") or {}
        state_body = json.dumps({"characters": chars, "char_shards": char_shards,
                                 "shards": sorted(set(char_shards.values()))}).encode()
        import hashlib
        state_hash = hashlib.sha256(state_body).hexdigest()
        if st.get("state_upload_hash") != state_hash:
            _inbox_put(f"sources/{iid}/state.json", state_body,
                       f"state from {iid}", need_sha=True)
            st["state_upload_hash"] = state_hash
            gamelog.save_state(st)
        st = gamelog.load_state()                       # re-load: capture may have run
        st["upload_offset"] = offset + sent
        gamelog.save_state(st)
        _stats["uploaded_bytes"] = _stats.get("uploaded_bytes", 0) + len(chunk)
        _stats["uploaded_last"] = time.strftime("%H:%M:%S")
    except Exception as e:  # noqa: BLE001 — the feed never breaks the app
        # reason-first, same as Lite 0.1.17 (bare class names forced guessing)
        reason = getattr(e, "reason", None) or e
        _stats["last_error"] = f"board feed: {reason} ({type(e).__name__})"
        _stats["feed_fails"] = _stats.get("feed_fails", 0) + 1


def build_board(public=False):
    """Build the pulse board HTML from the shared capture store and return its
    text. public=True renders the sanitized PUBLIC variant (the exact preview of
    what sharing shows); default is the PRIVATE local board (scorecards, market
    ledger, personal hauls — never uploaded)."""
    tools = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "tools")
    if getattr(sys, "frozen", False):
        tools = os.path.join(getattr(sys, "_MEIPASS",
                                     os.path.dirname(sys.executable)), "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import build_pulse_boards
    appdir = os.path.dirname(gamelog.STATE_DIR)
    name = "pulse_boards_public.html" if public else "pulse_boards.html"
    build_pulse_boards.OUT = os.path.join(appdir, name)
    build_pulse_boards.APPDIR = appdir
    out, _n = build_pulse_boards.build(state_dir=gamelog.STATE_DIR, public=public)
    with open(out, encoding="utf-8") as f:
        return f.read()


def feed_status():
    st = gamelog.load_state()
    return {"key_present": bool(inbox_token()),
            "terms_version_seen": st.get("terms_version", 0),
            "terms_version_current": TERMS_VERSION,
            "consented": st.get("terms_version", 0) >= TERMS_VERSION,
            "feed_disabled": bool(st.get("feed_disabled")),
            # 6a consent shape: the full app uploads only when ITS toggle was
            # explicitly answered yes — absent means "never asked here"
            "opted_in_here": st.get("feed_disabled") is False,
            "upload_owner": (gamelog.upload_owner() or {}).get("tag"),
            "feed_fails": _stats.get("feed_fails", 0),
            "upload_offset": int(st.get("upload_offset", 0)),
            "uploaded_last": _stats.get("uploaded_last"),
            "last_error": _stats.get("last_error")}


def set_feed_enabled(enabled):
    st = gamelog.load_state()
    st["feed_disabled"] = not enabled
    gamelog.save_state(st)


def accept_terms():
    """Record that the CURRENT terms version has been shown and accepted — the
    consent gate maybe_upload() checks. Reversible: /gamelog/feed off simply
    stops calling maybe_upload (and without consent it would refuse anyway)."""
    st = gamelog.load_state()
    st["terms_version"] = TERMS_VERSION
    gamelog.save_state(st)

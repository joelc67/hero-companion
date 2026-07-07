"""Pulse Boards pipeline renderer — runs INSIDE GitHub Actions (the inbox repo's
render workflow), never on a player's machine.

Layout when it runs (working dir = the PRIVATE inbox repo checkout):
  sources/<install_id>/c<offset>.jsonl   incremental capture chunks from Companion
                                         Lite, named by the local byte offset they
                                         start at (a retried upload overwrites the
                                         same file — events can never double-count)
  sources/<install_id>/compacted.jsonl   chunks already collected into one file
  sources/<install_id>/state.json        the sender's (pseudonymized) characters map
  last_count.json                        growth guard memory
  site/                                  checkout of the PUBLIC hero-companion repo

Modes:
  (default)   merge every source (compacted + chunks in offset order), build the
              sanitized PUBLIC board, write site/docs/pulse/index.html. Emits
              published=true/false to GITHUB_OUTPUT.
  --collect   the mailbox rule (Joel's): uploads get collected and REMOVED, never
              accumulated. Per source, every chunk EXCEPT the newest is appended to
              compacted.jsonl and deleted. The newest chunk stays because it is the
              only file its client could still be overwriting (a client re-PUTs only
              its current offset; once a newer chunk exists, the older name is final).

Raw uploads never leave the private inbox; only the rendered page is pushed public.
The growth guard never publishes a board built from fewer events than the last one.
"""
import calendar
import json
import os
import re
import subprocess
import sys
import time

INBOX = os.getcwd()
SITE = os.path.join(INBOX, "site")
sys.path.insert(0, os.path.join(SITE, "server"))
sys.path.insert(0, os.path.join(SITE, "tools"))

_CHUNK_RX = re.compile(r"^c(\d+)\.jsonl$")


def _chunks(d):
    """[(offset, filename)] sorted by offset."""
    out = []
    for name in os.listdir(d):
        m = _CHUNK_RX.match(name)
        if m:
            out.append((int(m.group(1)), name))
    return sorted(out)


def _read_lines(path):
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8", errors="replace") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _source_dirs():
    root = os.path.join(INBOX, "sources")
    if not os.path.isdir(root):
        return []
    return [os.path.join(root, n) for n in sorted(os.listdir(root))
            if os.path.isdir(os.path.join(root, n))]


def _ts_epoch(ts):
    try:
        return calendar.timegm(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))
    except Exception:  # noqa: BLE001
        return None


def _infer_offset_min(d, cached):
    """A source's UTC offset (minutes), inferred with no client support: chunk commit
    times are UTC and land within minutes of the newest event in the chunk, so
    (commit time − event clock) exposes the capturer's offset. Rounded to 30 min;
    falls back to the cached value when no chunk with events remains."""
    for _off, name in reversed(_chunks(d)):
        lines = _read_lines(os.path.join(d, name))
        if not lines:
            continue
        try:
            local = _ts_epoch(json.loads(lines[-1]).get("ts"))
            rel = os.path.relpath(os.path.join(d, name), INBOX).replace(os.sep, "/")
            out = subprocess.run(["git", "-C", INBOX, "log", "-1", "--format=%ct",
                                  "--", rel], capture_output=True, text=True, timeout=30)
            commit_utc = int(out.stdout.strip())
            if local is None:
                continue
            return -int(round((commit_utc - local) / 60.0 / 30.0)) * 30
        except Exception:  # noqa: BLE001
            continue
    return cached


def _shift_line(line, off_min):
    """Rewrite one event line's ts from the capturer's local clock to UTC."""
    if not off_min:
        return line
    try:
        ev = json.loads(line)
        t = _ts_epoch(ev.get("ts") or "")
        if t is None:
            return line
        ev["ts"] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t - off_min * 60))
        return json.dumps(ev)
    except Exception:  # noqa: BLE001
        return line


def _set_output(published):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"published={'true' if published else 'false'}\n")
    print(f"published={published}")


def collect():
    """Mailbox cleanup: fold every chunk but the newest into compacted.jsonl and
    delete it. Keeps each source at one compacted file + at most one live chunk."""
    folded = 0
    for d in _source_dirs():
        ch = _chunks(d)
        if len(ch) < 2:
            continue
        with open(os.path.join(d, "compacted.jsonl"), "a", encoding="utf-8") as out:
            for _off, name in ch[:-1]:
                for ln in _read_lines(os.path.join(d, name)):
                    out.write(ln + "\n")
                os.remove(os.path.join(d, name))
                folded += 1
    print(f"collected {folded} chunk file(s) into compacted stores")


def render():
    # merged scratch lives OUTSIDE the checkout so no commit step can ever pick it up
    merged_dir = os.path.join(os.environ.get("RUNNER_TEMP") or INBOX + "-tmp", "_merged")
    os.makedirs(merged_dir, exist_ok=True)
    try:
        with open(os.path.join(INBOX, "last_count.json"), encoding="utf-8") as f:
            cached_off = (json.load(f) or {}).get("offsets") or {}
    except Exception:  # noqa: BLE001
        cached_off = {}
    offsets, shards = {}, set()
    total, chars, nsrc = 0, {}, 0
    with open(os.path.join(merged_dir, "events.jsonl"), "w", encoding="utf-8") as out:
        for d in _source_dirs():
            nsrc += 1
            iid = os.path.basename(d)
            off = _infer_offset_min(d, cached_off.get(iid))
            offsets[iid] = off if off is not None else 0
            lines = _read_lines(os.path.join(d, "compacted.jsonl"))
            for _off, name in _chunks(d):
                lines += _read_lines(os.path.join(d, name))
            total += len(lines)
            # every merged timestamp becomes UTC so the board can render in the
            # VIEWER's time zone (offset inferred per source, cached across collects)
            lines = [_shift_line(ln, offsets[iid]) for ln in lines]
            out.write("\n".join(lines) + ("\n" if lines else ""))
            print(f"source {iid}: {len(lines)} events, utc offset {offsets[iid]} min")
            st = {}
            try:
                with open(os.path.join(d, "state.json"), encoding="utf-8") as f:
                    st = json.load(f) or {}
            except Exception:  # noqa: BLE001
                pass
            chars.update(st.get("characters") or {})
            # which server(s) this source plays on: the client auto-detects them from
            # the game's playerslot.txt (state.json "shards", Lite 0.1.14+); a
            # pipeline-side shard.json covers older clients
            src_shards = [str(s) for s in (st.get("shards") or []) if s]
            if not src_shards and st.get("shard"):
                src_shards = [str(st["shard"])]
            if not src_shards:
                try:
                    with open(os.path.join(d, "shard.json"), encoding="utf-8") as f:
                        sj = (json.load(f) or {}).get("shard")
                    if sj:
                        src_shards = [str(sj)]
                except Exception:  # noqa: BLE001
                    pass
            shards.update(src_shards)
    with open(os.path.join(merged_dir, "state.json"), "w", encoding="utf-8") as f:
        json.dump({"characters": chars, "shards": sorted(shards)}, f)

    try:
        with open(os.path.join(INBOX, "last_count.json"), encoding="utf-8") as f:
            last = int((json.load(f) or {}).get("events") or 0)
    except Exception:  # noqa: BLE001
        last = 0
    if total == 0 or total < last:
        print(f"GROWTH GUARD: merged {total} events vs last published {last} — skipping")
        _set_output(False)
        return

    import build_pulse_boards
    build_pulse_boards.OUT = os.path.join(SITE, "docs", "pulse", "index.html")
    build_pulse_boards.APPDIR = merged_dir
    out_path, n = build_pulse_boards.build(state_dir=merged_dir, public=True)
    print(f"built {out_path} from {n:,} events across {nsrc} source(s)")
    with open(os.path.join(INBOX, "last_count.json"), "w", encoding="utf-8") as f:
        json.dump({"events": n, "offsets": offsets}, f)
    _set_output(True)


if __name__ == "__main__":
    if "--collect" in sys.argv:
        collect()
    else:
        render()

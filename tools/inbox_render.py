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
import json
import os
import re
import sys

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
    total, chars, nsrc = 0, {}, 0
    with open(os.path.join(merged_dir, "events.jsonl"), "w", encoding="utf-8") as out:
        for d in _source_dirs():
            nsrc += 1
            lines = _read_lines(os.path.join(d, "compacted.jsonl"))
            for _off, name in _chunks(d):
                lines += _read_lines(os.path.join(d, name))
            total += len(lines)
            out.write("\n".join(lines) + ("\n" if lines else ""))
            try:
                with open(os.path.join(d, "state.json"), encoding="utf-8") as f:
                    chars.update((json.load(f) or {}).get("characters") or {})
            except Exception:  # noqa: BLE001
                pass
    with open(os.path.join(merged_dir, "state.json"), "w", encoding="utf-8") as f:
        json.dump({"characters": chars}, f)

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
        json.dump({"events": n}, f)
    _set_output(True)


if __name__ == "__main__":
    if "--collect" in sys.argv:
        collect()
    else:
        render()

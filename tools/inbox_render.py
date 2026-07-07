"""Pulse Boards pipeline renderer — runs INSIDE GitHub Actions (the inbox repo's
render workflow), never on a player's machine.

Layout when it runs (working dir = the PRIVATE inbox repo checkout):
  sources/<install_id>/c<epoch>.jsonl   incremental capture chunks from Companion Lite
  sources/<install_id>/r<epoch>.jsonl   reset chunk (that source's store was rebuilt —
                                        it supersedes every chunk before it)
  sources/<install_id>/state.json       the sender's characters map
  last_count.json                       growth guard memory
  site/                                 checkout of the PUBLIC hero-companion repo

It merges every source's chunks in order, builds the PUBLIC board variant (the
sanitized one: no machine paths, no account login names, no money, no achievement
state), and writes it into site/docs/pulse/index.html. The workflow pushes that file —
and ONLY that file — to the public site. Raw uploads never leave the private inbox.

Growth guard: never publish a board built from fewer events than the last publish
(a missing or half-synced source must not wipe the live board). Emits
published=true/false to GITHUB_OUTPUT.
"""
import json
import os
import re
import sys

INBOX = os.getcwd()
SITE = os.path.join(INBOX, "site")
sys.path.insert(0, os.path.join(SITE, "server"))
sys.path.insert(0, os.path.join(SITE, "tools"))

_CHUNK_RX = re.compile(r"^([cr])(\d+)\.jsonl$")


def _source_events(d):
    """One source's event lines, honoring the newest reset chunk if any."""
    chunks = []
    for name in os.listdir(d):
        m = _CHUNK_RX.match(name)
        if m:
            chunks.append((int(m.group(2)), m.group(1), name))
    chunks.sort()
    resets = [c for c in chunks if c[1] == "r"]
    if resets:
        cutoff = resets[-1][0]
        chunks = [c for c in chunks if c[0] >= cutoff and not
                  (c[1] == "r" and c[0] != cutoff)]
    lines = []
    for _ts, _kind, name in chunks:
        with open(os.path.join(d, name), encoding="utf-8", errors="replace") as f:
            lines += [ln.strip() for ln in f if ln.strip()]
    return lines


def _set_output(published):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"published={'true' if published else 'false'}\n")
    print(f"published={published}")


def main():
    srcroot = os.path.join(INBOX, "sources")
    merged_dir = os.path.join(INBOX, "_merged")
    os.makedirs(merged_dir, exist_ok=True)
    total, chars = 0, {}
    with open(os.path.join(merged_dir, "events.jsonl"), "w", encoding="utf-8") as out:
        if os.path.isdir(srcroot):
            for iid in sorted(os.listdir(srcroot)):
                d = os.path.join(srcroot, iid)
                if not os.path.isdir(d):
                    continue
                lines = _source_events(d)
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
    print(f"built {out_path} from {n:,} events across "
          f"{len(os.listdir(srcroot)) if os.path.isdir(srcroot) else 0} source(s)")
    with open(os.path.join(INBOX, "last_count.json"), "w", encoding="utf-8") as f:
        json.dump({"events": n}, f)
    _set_output(True)


if __name__ == "__main__":
    main()

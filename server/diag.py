"""One line on stderr whenever an exception is caught and deliberately ignored.

WHY THIS EXISTS (2026-07-26): a `except Exception: return []` in _ask_remedies
swallowed a real defect for a whole release cycle. The field report said the tool
gave a bare refusal with no suggestions; the code said it was working. Five rounds
of reasoning could not close that gap, because the evidence was being discarded at
the moment it was produced.

The swallow itself is usually RIGHT - advice, diagnostics, and optional data files
must never break a solve. What is never right is discarding the reason silently.
This costs one line of output and turns "it just does nothing" into "here is what
threw, and where".

Deliberately not the logging module: no config, no handlers, no import-order
surprises in a frozen PyInstaller build, and it prints the same way the rest of
this server already talks to its console.
"""
import sys


def swallowed(where, detail=""):
    """Call INSIDE an except block. Names the site and what was thrown."""
    exc = sys.exc_info()[1]
    if exc is None:                       # called outside an except block
        return
    tail = f" ({detail})" if detail else ""
    print(f"[hc] swallowed in {where}{tail}: {type(exc).__name__}: {exc}",
          file=sys.stderr, flush=True)

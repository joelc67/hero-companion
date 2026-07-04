"""Run the dev server on port 5080 so it never collides with the installed
tray app, which owns port 5000. Used by .claude/launch.json (coh-builder-dev)."""
import os
import runpy
import sys

os.environ.setdefault("PORT", "5080")
SERVER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "server", "server.py")
sys.path.insert(0, os.path.dirname(SERVER))
runpy.run_path(SERVER, run_name="__main__")

"""Hero Companion — the packaged (PyInstaller) entry point: start the local server,
open the browser, keep the console as the app's lifeline. Also runs from source:
    python run_app.py
Env knobs: PORT (default 5000), HC_NO_BROWSER=1 (don't auto-open a browser tab).
"""
import os
import sys
import threading
import webbrowser

if getattr(sys, "frozen", False):
    BASE = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE, "server"))
sys.path.insert(0, os.path.join(BASE, "ai"))

import server  # noqa: E402  — the Flask app module; loads the game data on import


def main():
    port = int(os.environ.get("PORT", "5000"))
    print(f"Hero Companion v{server.APP_VERSION} — model v{__import__('first_principles').MODEL_VERSION}"
          f" — data {server.DB_VERSION}")
    print(f"Running at http://localhost:{port}")
    print("Keep this window open while you use the app; close it to stop.")
    if os.environ.get("HC_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    server.app.run(host="127.0.0.1", port=port, debug=False)


if __name__ == "__main__":
    main()

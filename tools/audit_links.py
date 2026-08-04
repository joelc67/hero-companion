"""audit_links.py — the design once-over, mechanized (Joel, 2026-08-04:
"make sure this does not have broken links, or any other inabilities to
read and navigate content").

Checks, each with a denominator from an independent source:
  1. Local href/src references (index.html + app.js template strings) point
     at files that exist under static/ — a broken image or stylesheet is a
     broken page.
  2. Server-route references (window.open, href to /docs/... etc.) point at
     routes @app.route actually declares.
  3. Every inline onclick handler names a function app.js actually defines
     (function / window.x = / const x =) — a dead handler is a dead button.
  4. Every data-tab / showTab target is a real tab key.
  5. External URLs are well-formed https and on a known host list — the
     wikis 403 automated fetchers, so existence is format-checked here and
     eyeballed in the app, never silently assumed dead OR alive.

Hard-fails on any local miss. Negative controls (--selftest) plant one
defect per class and demand the checker catches it.
"""
import re
import sys
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

KNOWN_HOSTS = {
    "homecoming.wiki", "forums.homecomingservers.com", "github.com",
    "hero-companion.com", "www.hero-companion.com", "joelc67.github.io",
    "midsreborn.com", "cod.uberguy.net", "web3forms.com", "api.web3forms.com",
    "archive.org", "homecomingservers.com",
}

FAILS = []
CHECKED = {"local": 0, "route": 0, "onclick": 0, "tab": 0, "ext": 0}


def read(p):
    return p.read_text(encoding="utf-8", errors="replace")


def audit(html, js, server_src, quiet=False):
    global FAILS, CHECKED
    FAILS = []
    CHECKED = {k: 0 for k in CHECKED}
    both = html + "\n" + js

    routes = set(re.findall(r'@app\.route\(\s*"([^"]+)"', server_src))
    # route patterns with <converters> match by prefix segment
    route_prefixes = {r.split("<")[0].rstrip("/") for r in routes}

    # ── 1+2: href/src targets ────────────────────────────────────────────
    for attr, target in re.findall(r'(href|src)="([^"${}]+)"', both):
        t = target.strip()
        if not t or t.startswith(("#", "mailto:", "javascript:", "data:")):
            continue
        if t.startswith(("http://", "https://")):
            CHECKED["ext"] += 1
            host = re.sub(r"^https?://", "", t).split("/")[0]
            if not t.startswith("https://"):
                FAILS.append(f"ext not https: {t}")
            elif host not in KNOWN_HOSTS:
                FAILS.append(f"ext host not on the known list (add it or fix it): {t}")
            continue
        if t.startswith("/static/") or t.startswith("static/"):
            CHECKED["local"] += 1
            rel = t.split("?")[0].lstrip("/")
            if not (ROOT / rel).exists():
                FAILS.append(f"missing local file: {t}")
            continue
        if t.startswith("/"):
            CHECKED["route"] += 1
            base = t.split("?")[0].rstrip("/")
            if base not in {r.rstrip("/") for r in routes} and not any(
                    p and base.startswith(p) for p in route_prefixes):
                FAILS.append(f"no server route for: {t}")

    # window.open('...') targets are navigation too (template-built URLs
    # carry ${...} and can't be checked statically — skipped, not failed)
    for target in re.findall(r"window\.open\(\s*['\"]([^'\"]+)['\"]", both):
        if "${" in target:
            continue
        if target.startswith(("http://", "https://")):
            CHECKED["ext"] += 1
            host = re.sub(r"^https?://", "", target).split("/")[0]
            if host not in KNOWN_HOSTS:
                FAILS.append(f"window.open ext host unknown: {target}")
            continue
        CHECKED["route"] += 1
        base = target.split("?")[0].rstrip("/")
        if base not in {r.rstrip("/") for r in routes} and not any(
                p and base.startswith(p) for p in route_prefixes):
            FAILS.append(f"window.open target has no route: {target}")

    # ── 3: onclick handlers name real functions ──────────────────────────
    defined = set(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)", js))
    defined |= set(re.findall(r"\bwindow\.([A-Za-z_$][\w$]*)\s*=", js))
    defined |= set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?(?:function|\()", js))
    for call in re.findall(r'onclick="\s*([A-Za-z_$][\w$]*)\s*\(', both):
        CHECKED["onclick"] += 1
        if call not in defined and call not in ("event",):
            FAILS.append(f"onclick names undefined function: {call}()")

    # ── 4: tab navigation targets ────────────────────────────────────────
    m = re.search(r"_TABS\s*=\s*\[([^\]]*)\]", js)
    tabs = set(re.findall(r'"(\w+)"', m.group(1))) if m else set()
    if not tabs:
        FAILS.append("could not extract _TABS from app.js")
    for t in re.findall(r'data-tab="(\w+)"', both) + re.findall(r"showTab\(\s*['\"](\w+)['\"]", both):
        CHECKED["tab"] += 1
        if t not in tabs:
            FAILS.append(f"tab target is not a real tab: {t}")

    if not quiet:
        n = sum(CHECKED.values())
        print(f"audit_links: {n} references checked "
              f"(local {CHECKED['local']} · routes {CHECKED['route']} · "
              f"onclick {CHECKED['onclick']} · tabs {CHECKED['tab']} · "
              f"external {CHECKED['ext']})")
        for f in FAILS:
            print(f"  FAIL {f}")
    return not FAILS


def selftest(html, js, server_src):
    """Negative controls: one planted defect per class must each fail."""
    plants = [
        ("local", html + '<img src="/static/no_such_file_xyz.png">', js, server_src),
        ("route", html + '<a href="/no/such/route/xyz">x</a>', js, server_src),
        ("onclick", html + '<button onclick="noSuchFnXyz()">x</button>', js, server_src),
        ("tab", html + '<button data-tab="nosuchtab">x</button>', js, server_src),
        ("ext", html + '<a href="https://evil-unknown-host.example/x">x</a>', js, server_src),
    ]
    ok = True
    for name, h, j, s in plants:
        if audit(h, j, s, quiet=True):
            print(f"  NEGATIVE CONTROL FAILED: planted {name} defect not caught")
            ok = False
    print(f"negative controls: {len(plants)} planted defects "
          + ("all caught" if ok else "NOT all caught"))
    return ok


def main():
    html = read(STATIC / "index.html")
    # tour.js defines handlers index.html calls (startTour/explainStep) and
    # paints its own markup — it is both a definition source and a reference
    # source, so it joins the js side whole.
    js = read(STATIC / "app.js") + "\n" + read(STATIC / "tour.js")
    server_src = read(ROOT / "server" / "server.py")
    ok = audit(html, js, server_src)
    ok = selftest(html, js, server_src) and ok
    print("audit_links: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    main()

"""RELEASE SMOKE (run against dist/HeroCompanion/HeroCompanion.exe before EVERY publish):
pinned Defender L1 RULE (one pick from each set's first two), MM Mercs summons carry pet
sets (no heal globals), version/packaged flags. Update the version expectation per release.
"""
import json, subprocess, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
EXE = r"C:\Users\joelc\code\coh-builder\dist\HeroCompanion\HeroCompanion.exe"
proc = subprocess.Popen([EXE])
base = None
try:
    for _ in range(60):
        time.sleep(1)
        for port in (5000, 5001, 5002):
            try:
                v = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2))
                # PORT-RACE GUARD (see smoke_gold): only the exe we launched counts
                m = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/meta", timeout=2))
                if m.get("app_version") != "0.12.22":
                    continue
                base = f"http://127.0.0.1:{port}"; break
            except Exception: pass
        if base: break
    if not base: raise SystemExit("FAIL: server never came up")

    def get(path):
        return json.load(urllib.request.urlopen(base+path, timeout=10))
    def post(path, payload):
        req = urllib.request.Request(base+path, json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=120))

    meta = get("/meta")
    print("version:", meta.get("app_version"), "packaged:", meta.get("packaged"))
    ok3 = meta.get("app_version") == "0.12.22" and meta.get("packaged") is True

    # pinned case 1: Defender Poison/Sonic L1 creation pair (champion-mask trap)
    ap = post("/build/autopick", {"archetype":"Class_Defender","primary":"Defender_Buff.Poison",
              "secondary":"Defender_Ranged.Sonic_Attack","content":"itrial"})
    l1 = sorted(p["display_name"] for p in ap["powers"]
                if p.get("pick_level")==1 and not p["full_name"].startswith("Inherent"))
    print("Defender L1 picks:", l1)
    # The RULE, not an instance: exactly one L1 pick from the primary's first two and
    # one from the secondary's first two (the champion may legitimately pick Scream).
    ok1 = (len(l1) == 2 and len(set(l1) & {"Alkaloid", "Envenom"}) == 1
           and len(set(l1) & {"Shriek", "Scream"}) == 1)

    # pinned case 2 (NEW): MM Mercenaries summons get PET sets, no heal globals
    ap2 = post("/build/autopick", {"archetype":"Class_Mastermind","primary":"Mastermind_Summon.Mercenaries",
               "secondary":"Mastermind_Buff.Traps","content":"general"})
    sol = post("/build/solve", {"archetype":"Class_Mastermind","powers":ap2["powers"],
               "content":"general","role":"damage"})
    HEAL = {"Numina's Convalesence","Miracle","Regenerative Tissue","Panacea"}
    ok2 = True
    for p in sol["powers"]:
        if p.get("display_name") in ("Soldiers","Spec Ops","Commando"):
            sets = [s.get("set_name") for s in (p.get("slots") or []) if s]
            bad = [s for s in sets if s in HEAL]
            has_set = any(s and s != "Common IO" for s in sets)
            print(f"  {p['display_name']}: {'OK pet sets' if has_set and not bad else sets}")
            if bad or not has_set: ok2 = False

    # pinned case 3 (NEW, 2026-07-20 — the dead-air interaction smoke): the
    # controls that silently no-op'd in the field must be exercised in the
    # PACKAGED app. (a) /build/calculate is the recompute backend behind epic
    # swap + target edits — a fresh build must yield real totals; (b) the shipped
    # client must carry the global error surface so a server-down page can never
    # be silently dead again.
    calc = post("/build/calculate", {"archetype": "Class_Mastermind",
                "powers": sol["powers"], "content": "general", "role": "damage"})
    ok4 = isinstance(calc, dict) and ("endurance" in calc or "defense" in calc)
    print("recompute backend (/build/calculate):", "OK totals" if ok4 else "NO TOTALS")
    # all THREE dead-air surfaces must be present in the shipped client, or the
    # regression class (silent no-op / dead page) can return unnoticed:
    #  - fetch banner (server unreachable)   -> global-error-banner + showServerError
    #  - global exception surface            -> unhandledrejection handler
    #  - old-save forward-compat guard       -> the powers normalization filter
    ok5 = False
    for path in ("/static/app.js", "/app.js"):
        try:
            js = urllib.request.urlopen(base + path, timeout=10).read().decode("utf-8", "ignore")
            ok5 = ("global-error-banner" in js and "showServerError" in js
                   and "unhandledrejection" in js
                   and "filter((p) => p && p.full_name)" in js
                   # walk failure #2 (2026-07-20): every solve/action surface gives
                   # a named-gate-or-visible-result answer, chip==editor truth
                   and "function flagMissing" in js
                   and "function hasTargetValues" in js
                   and "No changes" in js
                   # walk failure #3: a pending confirm-intent question must be
                   # announced at the button, never an invisible hang
                   and "One question before I build" in js)
            break
        except Exception:  # noqa: BLE001
            continue
    print("client error/forward-compat surfaces present:", "YES" if ok5 else "MISSING")

    # pinned case 4 (2026-07-20): the content picker's farm section renders EXACTLY
    # the two defined fire-farm choices; the retired generic "fire_farm" key never
    # reappears in any picker surface.
    ok6 = False
    try:
        html = urllib.request.urlopen(base + "/", timeout=10).read().decode("utf-8", "ignore")
        ok6 = ('value="fire_farm"' not in html
               and 'value="farm_afk"' in html and 'value="farm_active"' in html)
    except Exception:  # noqa: BLE001
        pass
    print("fire-farm picker (2 choices, no generic):", "OK" if ok6 else "WRONG")

    # pinned case 5 (2026-07-20 walk report): EVERY import entry point offers file
    # navigation — the two entry cards, the builder's import button, and the file
    # input they all trigger. A missing browse control strands users with a game
    # export and no way to load it.
    ok7 = False
    try:
        html2 = urllib.request.urlopen(base + "/", timeout=10).read().decode("utf-8", "ignore")
        ok7 = all(m in html2 for m in
                  ('id="import-file"', 'id="import-btn"',
                   'id="entry-mids"', 'id="ingame-pick-go"',
                   # walk failure #3: the solve flow's output panel must live
                   # OUTSIDE the AI-only #ai-qa section (hidden on AI-free
                   # clients) or confirms/reports render invisibly
                   'ai-response lives OUTSIDE'))
    except Exception:  # noqa: BLE001
        pass
    print("import entry points (browse everywhere):", "OK" if ok7 else "MISSING")

    allok = ok1 and ok2 and ok3 and ok4 and ok5 and ok6 and ok7
    print("SMOKE:", "PASS" if allok else
          f"FAIL (L1={ok1} summons={ok2} ver={ok3} recompute={ok4} "
          f"errsurface={ok5} farmpicker={ok6} importnav={ok7})")
    sys.exit(0 if allok else 1)
finally:
    proc.terminate()
    time.sleep(2)
    subprocess.run(["taskkill","/F","/IM","HeroCompanion.exe"], capture_output=True)

"""GOLD SMOKE (run before EVERY publish): every champion context in benchmarks/champions.json
must be SERVED by the frozen exe's autopick at >90% pick overlap - proves the bundled
champions actually reach end users (the 0.12.10-and-earlier packaging defect).
"""
import json, subprocess, sys, time, urllib.request
sys.stdout.reconfigure(encoding="utf-8")
EXE = r"C:\Users\joelc\code\coh-builder\dist\HeroCompanion\HeroCompanion.exe"
CHAMPS = json.load(open(r"C:\Users\joelc\code\coh-builder\benchmarks\champions.json", encoding="utf-8"))
proc = subprocess.Popen([EXE])
base = None
try:
    for _ in range(60):
        time.sleep(1)
        for port in (5000, 5001, 5002):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2)
                # PORT-RACE GUARD (bit 3x on 2026-07-20): the installed tray app can
                # own 5000 while the launched dist exe fell back to 5001 - accept a
                # port ONLY if it is the exe we just launched (version pin match).
                m = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/meta", timeout=2))
                if m.get("app_version") != "0.12.23":
                    continue
                base = f"http://127.0.0.1:{port}"; break
            except Exception: pass
        if base: break
    if not base: raise SystemExit("FAIL: no server")
    def post(path, payload):
        req = urllib.request.Request(base+path, json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=120))
    meta = json.load(urllib.request.urlopen(base+"/meta", timeout=5))
    print("version:", meta["app_version"], "model:", meta["model_version"], "packaged:", meta["packaged"])
    # Update these pins per release (like smoke_release's version expectation).
    ok_all = meta["app_version"] == "0.12.23" and meta["model_version"] == 35
    if not ok_all:
        print("  VERSION/MODEL PIN MISMATCH — update the pins for this release")
    # THE GOLD TEST: every champion context, served to a frozen END USER via autopick.
    # FORM champions (5-part keys, Joel's per-form Kheldian ruling 2026-07-12) can't
    # be reached through plain autopick until the wizard grows its Form question —
    # they're checked for a CONVERGED certificate + nonempty picks instead, and the
    # denominator names both counts so nothing hides.
    checked = 0
    for key, entry in CHAMPS.items():
        parts = key.split("|")
        at, prim, sec, content = parts[:4]
        form = parts[4] if len(parts) > 4 else None
        # FORM champions (per-form Kheldian route): served through the wizard's
        # Form question — the same autopick path, with the form passed.
        ap = post("/build/autopick", {"archetype":at,"primary":prim,"secondary":sec,
                                      "content":content, "form":form})
        got = {p["full_name"] for p in ap["powers"] if not p["full_name"].startswith("Inherent")}
        champ = {p for p in entry["picks"] if not p.split(".")[0].startswith("Inherent")}
        overlap = len(got & champ) / max(1, len(champ))
        served = overlap > 0.9
        ok_all = ok_all and served
        checked += 1
        tag = f" [{form}]" if form else ""
        print(f"  {'GOLD SERVED' if served else 'HEURISTIC (FAIL)':18s} {prim.split('.')[-1]}/{sec.split('.')[-1]}{tag}  overlap={overlap:.0%}")
    # Coverage denominator (standing rule): every bundled champion context checked.
    print(f"  {checked} of {len(CHAMPS)} champion contexts checked (form contexts served via the Form route)")
    ok_all = ok_all and checked == len(CHAMPS)
    print("GOLD SMOKE:", "PASS" if ok_all else "FAIL")
    # A gate that prints FAIL must also EXIT nonzero (it used to exit 0 regardless).
    sys.exit(0 if ok_all else 1)
finally:
    proc.terminate(); time.sleep(2)
    subprocess.run(["taskkill","/F","/IM","HeroCompanion.exe"], capture_output=True)

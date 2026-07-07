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
    ok3 = meta.get("app_version") == "0.12.14" and meta.get("packaged") is True

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

    print("SMOKE:", "PASS" if (ok1 and ok2 and ok3) else f"FAIL (L1={ok1} summons={ok2} ver={ok3})")
    sys.exit(0 if (ok1 and ok2 and ok3) else 1)
finally:
    proc.terminate()
    time.sleep(2)
    subprocess.run(["taskkill","/F","/IM","HeroCompanion.exe"], capture_output=True)

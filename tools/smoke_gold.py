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
    ok_all = meta["app_version"] == "0.12.13" and meta["model_version"] == 27
    # THE GOLD TEST: every champion context, served to a frozen END USER via autopick
    for key, entry in CHAMPS.items():
        at, prim, sec, content = key.split("|")
        ap = post("/build/autopick", {"archetype":at,"primary":prim,"secondary":sec,"content":content})
        got = {p["full_name"] for p in ap["powers"] if not p["full_name"].startswith("Inherent")}
        champ = {p for p in entry["picks"] if not p.split(".")[0].startswith("Inherent")}
        overlap = len(got & champ) / max(1, len(champ))
        served = overlap > 0.9
        ok_all = ok_all and served
        print(f"  {'GOLD SERVED' if served else 'HEURISTIC (FAIL)':18s} {prim.split('.')[-1]}/{sec.split('.')[-1]}  overlap={overlap:.0%}")
    print("GOLD SMOKE:", "PASS" if ok_all else "FAIL")
finally:
    proc.terminate(); time.sleep(2)
    subprocess.run(["taskkill","/F","/IM","HeroCompanion.exe"], capture_output=True)

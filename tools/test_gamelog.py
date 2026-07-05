"""Game-log capture: parser VALIDATED against a real Homecoming farm-session sample
(tools/fixtures/gamelog_real_sample.txt — representative lines from Rattle/Lime Juice,
2026-07-05), plus discovery/ingest/endpoint machinery on a synthetic tree.

Run:  python tools/test_gamelog.py
"""
import json
import os
import shutil
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8")
ROOT = r"C:\Users\joelc\code\coh-builder"
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv
import gamelog

fails = []


def check(name, ok, detail=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


# ── parse the REAL sample line-by-line ───────────────────────────────────────
print("── real-format parsing (validated fixture) ──")
FIX = os.path.join(ROOT, "tools", "fixtures", "gamelog_real_sample.txt")
events, interesting = [], 0
with open(FIX, encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        ev, is_interesting = gamelog.parse_line(line)
        if ev:
            events.append(ev)
        elif is_interesting:
            interesting += 1
by = {}
for e in events:
    by.setdefault(e["type"], []).append(e)


def one(t):
    return (by.get(t) or [{}])[0]


check("XP + influence", one("xp").get("xp") == 2524 and one("xp").get("inf") == 3533)
check("AH sale influence in", one("influence_ah").get("inf") == 15000000)
check("AH fee out (spent)", one("spent").get("inf") == 500)
check("AH sold item", "Calibrated Accuracy" in one("ah_sold").get("item", ""))
check("AH collect (You got X Recipe)", "Air Burst" in one("collect").get("item", ""))
check("KILL parsed (not death)", len(by.get("kill", [])) == 3,
      f"{len(by.get('kill', []))} kills: " + ", ".join(k["enemy"] for k in by.get("kill", [])))
check("no false death from kills", "death" not in by)
check("drop: Incarnate Thread -> incarnate", any(
    d["item"] == "Incarnate Thread" and d["kind"] == "incarnate" for d in by.get("drop", [])))
check("drop: Ruby -> salvage", any(
    d["item"] == "Ruby" and d["kind"] == "salvage" for d in by.get("drop", [])))
check("drop: Enhancement Converter -> crafting", any(
    "Converter" in d["item"] and d["kind"] == "crafting" for d in by.get("drop", [])))
check("drop: Invention recipe -> recipe", any(
    d["kind"] == "recipe" for d in by.get("drop", [])))
# NOISE must not become events or 'interesting' samples
check("combat/buff/chat noise ignored", interesting == 0,
      f"{interesting} noise lines wrongly flagged")
check("heals/procs/LFG produced no events",
      not any(e["type"] not in ("xp", "influence_ah", "spent", "ah_sold", "ah_listed",
                                "collect", "kill", "death", "drop", "merits", "level", "badge")
              for e in events))

# ── coverage report surfaces a GENUINELY unknown reward line ─────────────────
print("\n── coverage honesty ──")
unknown = "2026-07-05 19:00:00 You have earned a Veteran Level!"
ev, interesting_flag = gamelog.parse_line(unknown)
check("unknown vet-level line flagged as interesting", ev is None and interesting_flag)

# ── discovery + incremental ingest + endpoints (synthetic tree) ──────────────
print("\n── discovery / ingest / endpoints ──")
tmp = tempfile.mkdtemp(prefix="hc_gamelog_test_")
logdir = os.path.join(tmp, "accounts", "filofinfain", "Logs")
os.makedirs(logdir)
os.makedirs(os.path.join(tmp, "accounts", "kalicous"))      # no Logs yet
shutil.copy(FIX, os.path.join(logdir, "chatlog 2026-07-05.txt"))
gamelog.STATE_DIR = os.path.join(tmp, "state")

accts = gamelog.find_log_accounts([os.path.join(tmp, "accounts")])
check("both accounts discovered", len(accts) == 2)
st = {"log_dir": logdir, "offsets": {}}
ev1, rep1 = gamelog.ingest(logdir, st)
check("ingest parsed the sample", rep1["parsed"] >= 15, f"{rep1['parsed']} events")
check("ingest coverage clean (no false unknowns)", rep1["unparsed_interesting"] == 0,
      f"{rep1['unparsed_interesting']}: {rep1['unparsed_samples'][:3]}")
ev2, rep2 = gamelog.ingest(logdir, st)
check("incremental: second pass reads nothing", not ev2 and rep2["new_lines"] == 0)

s = gamelog.summarize(gamelog.load_events())
check("summary kills counted", s["kills"] == 3, s["kills"])
check("summary influence includes AH sale", s["inf_gained"] >= 15000000)
check("summary drop kinds populated", bool(s["drop_kinds"]), str(s["drop_kinds"]))

c = srv.app.test_client()
r = c.post("/gamelog/watch", json={"log_dir": logdir, "root": tmp}).get_json()
check("watch accepts in-tree dir", r.get("ok"))
ins = c.get("/gamelog/insights").get_json()["insights"]
inc = next((h for h in ins["haul"] if h["item"] == "Incarnate Thread"), None)
check("insights: incarnate drop = KEEP", inc and inc["verdict"] == "KEEP", str(inc))

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)

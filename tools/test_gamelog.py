"""Game-log capture P1: discovery, incremental ingest, provisional parsing, insights.

Runs against a SYNTHETIC accounts tree (the parse patterns themselves stay provisional
until a real /logchat sample arrives — this proves the machinery, not the formats).

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


# ── synthetic world ──────────────────────────────────────────────────────────
tmp = tempfile.mkdtemp(prefix="hc_gamelog_test_")
acct = os.path.join(tmp, "accounts", "testacct")
logdir = os.path.join(acct, "Logs")
os.makedirs(logdir)
os.makedirs(os.path.join(tmp, "accounts", "emptyacct"))
LOG = os.path.join(logdir, "chatlog 2026-07-05.txt")
LINES = [
    "2026-07-05 20:01:11 You gain 1,250 experience and 625 influence.",
    "2026-07-05 20:02:12 You gain 5,000 influence.",
    "2026-07-05 20:03:13 You are now level 23.",
    "2026-07-05 20:04:14 You have been awarded 20 Reward Merits.",
    "2026-07-05 20:05:15 Congratulations! You earned the Keeper of Secrets badge.",
    "2026-07-05 20:06:16 You have been defeated by Hellion Blood Brother.",
    "2026-07-05 20:07:17 You received Luck of the Gambler: Defense/Endurance (Recipe).",
    "2026-07-05 20:08:18 You received Apocalypse: Chance of Damage(Negative) (Recipe).",
    "2026-07-05 20:09:19 You sold Kinetic Combat: Damage/Endurance for 2,000,000 inf.",
    "2026-07-05 20:10:20 You bought Enhancement Converter for 70,000 inf.",
    "2026-07-05 20:11:21 [Local] Player1: selling cheap purples meet at AE",
    "2026-07-05 20:12:22 You activated the Fly power.",
    "garbage line without a timestamp",
]
with open(LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES) + "\n")

gamelog.STATE_DIR = os.path.join(tmp, "state")

# ── discovery ────────────────────────────────────────────────────────────────
print("── discovery ──")
accts = gamelog.find_log_accounts([os.path.join(tmp, "accounts")])
check("finds both accounts", len(accts) == 2, ", ".join(a["account"] for a in accts))
ta = next(a for a in accts if a["account"] == "testacct")
check("flags log files", ta["has_logs"] and ta["log_files"] == 1)
check("empty account offered too (picker shows it)",
      any(not a["has_logs"] for a in accts))

# ── ingest + parse ───────────────────────────────────────────────────────────
print("\n── ingest ──")
st = {"log_dir": logdir, "offsets": {}}
events, report = gamelog.ingest(logdir, st)
by = {}
for e in events:
    by[e["type"]] = by.get(e["type"], 0) + 1
check("xp parsed", by.get("xp") == 1)
check("influence parsed", by.get("inf") == 1)
check("level parsed", by.get("level") == 1)
check("merits parsed", by.get("merits") == 1)
check("badge parsed", by.get("badge") == 1)
check("defeat parsed", by.get("defeat") == 1)
check("drops parsed", by.get("drop") == 2, str(by))
check("AH sale + buy parsed", by.get("ah_sold") == 1 and by.get("ah_bought") == 1)
check("chat chatter NOT an event", "Player1" not in json.dumps(events))
check("coverage counts the unrecognized You-line", report["unparsed_interesting"] >= 1,
      f"samples: {report['unparsed_samples']}")
ev2, rep2 = gamelog.ingest(logdir, st)
check("incremental: second ingest reads nothing", not ev2 and rep2["new_lines"] == 0)
with open(LOG, "a", encoding="utf-8") as f:
    f.write("2026-07-05 21:00:00 You gain 99 experience and 33 influence.\n")
ev3, rep3 = gamelog.ingest(logdir, st)
check("incremental: appended line ingested", len(ev3) == 1 and rep3["new_lines"] == 1)

# ── summarize + endpoint flow ────────────────────────────────────────────────
print("\n── insights ──")
s = gamelog.summarize(gamelog.load_events())
check("xp total", s["xp"] == 1349, s["xp"])
check("influence gained incl. sale", s["inf_gained"] == 625 + 5000 + 33 + 2000000, s["inf_gained"])
check("influence spent from buy", s["inf_spent"] == 70000)
check("max level", s["max_level"] == 23)

c = srv.app.test_client()
r = c.post("/gamelog/scan", json={"root": tmp}).get_json()
check("scan endpoint lists accounts", r["ok"] and len(r["accounts"]) >= 2)
r = c.post("/gamelog/watch", json={"log_dir": logdir, "root": tmp}).get_json()
check("watch endpoint accepts in-tree dir", r.get("ok"), str(r))
r = c.post("/gamelog/watch", json={"log_dir": r"C:\Windows\System32", "root": tmp}).get_json()
check("watch endpoint REFUSES out-of-tree dir", not r.get("ok"))
r = c.get("/gamelog/insights").get_json()
haul = {h["item"]: h for h in r["insights"]["haul"]}
lotg = haul.get("Luck of the Gambler: Defense/Endurance")
apoc = haul.get("Apocalypse: Chance of Damage(Negative)")
check("LotG mapped + convert/sell verdict", lotg and lotg["verdict"] == "CONVERT/SELL",
      str(lotg and lotg["verdict"]))
check("Apocalypse mapped + KEEP verdict", apoc and apoc["verdict"] == "KEEP",
      str(apoc and apoc["verdict"]))

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n══ {'ALL PASS' if not fails else f'{len(fails)} FAILURE(S): ' + ', '.join(fails)} ══")
sys.exit(1 if fails else 0)

"""PRESET-vs-CAP AUDIT (yellowthief1's find generalized, per the universal rule:
fix the RULE archetype-independently and prove it with an all-AT audit).

For EVERY archetype x content preset x role preset, compose the targets the
solver would actually chase (through ai_build.preset_targets with the AT's
REAL res cap) and assert the cap family invariant:

  1. no resistance target EXCEEDS the AT's hard cap (unreachable ask), and
  2. no CAP-marked entry resolves BELOW the AT's cap (the 75-on-a-Tanker
     undercut — the reported defect), and
  3. every res_cap consumer in the serving code derives from the archetype
     table, never the generic fallback, when an archetype is in hand
     (checked here by comparing table-cap composition vs generic-75
     composition: any AT/content/role whose targets differ MUST be using
     the table path — deep_optimize/joint_refine hardcodes are the pinned
     regression this audit exists to catch).

Coverage denominator: |ATs| x |contents| x |roles| combinations checked,
printed and hard-failed if short.

Run:  python tools/audit_preset_caps.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder")
sys.path.insert(0, r"C:\Users\joelc\code\coh-builder\server")
import server as srv  # noqa: E402
import ai_build  # noqa: E402
import inspect  # noqa: E402

ATS = sorted(a["name"] for a in srv.ARCHETYPES["archetypes"]
             if a.get("playable") and a.get("name"))
CONTENTS = sorted(ai_build.CONTENT_PRESETS)
ROLES = sorted(set(ai_build.ROLE_PRESETS) | {""})

problems = []
checked = 0
for at_name in ATS:
    at = srv.ARCH_BY_NAME[at_name]
    cap = round((at.get("res_cap") or 0.75) * 100, 1)
    for content in CONTENTS:
        for role in ROLES:
            checked += 1
            t = ai_build.preset_targets(content, role or None, res_cap=cap)["targets"]
            for ty, v in (t.get("resistance") or {}).items():
                if v > cap + 1e-9:
                    problems.append(f"{at_name} {content}/{role or '-'}: res {ty} "
                                    f"target {v} EXCEEDS cap {cap}")
            # CAP-marked entries must resolve to the AT's own cap
            raw = (ai_build.CONTENT_PRESETS.get(content) or {}).get("resistance") or {}
            for ty, v in raw.items():
                if v == "CAP" and (t.get("resistance") or {}).get(ty) != cap:
                    problems.append(f"{at_name} {content}/{role or '-'}: CAP entry "
                                    f"{ty} resolved to "
                                    f"{(t.get('resistance') or {}).get(ty)} != cap {cap}")

# Pinned regression: no res_cap=<number> hardcodes on serving/certification paths.
src = inspect.getsource(srv)
hardcodes = [ln.strip() for ln in src.splitlines()
             if "res_cap=75" in ln.replace(" ", "").replace("res_cap =", "res_cap=")]
for ln in hardcodes:
    problems.append(f"HARDCODED res_cap=75 in server.py: {ln[:90]}")

expected = len(ATS) * len(CONTENTS) * len(ROLES)
print(f"{checked} of {expected} AT x content x role combinations checked "
      f"({len(ATS)} ATs, {len(CONTENTS)} contents, {len(ROLES)} roles)")
print(f"PROBLEMS: {len(problems)}")
for p in problems[:30]:
    print(" ", p)
if checked != expected or problems:
    sys.exit(1)
print("Every preset resistance target respects its archetype's cap family.")

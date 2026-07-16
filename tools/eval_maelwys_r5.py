"""Maelwys round-5 verification harness (2026-07-16 work order, items 1-4).

Imports his three reference .mbd builds through OUR parser and evaluates them
under OUR math + the AFK sustain ledger, TWICE:
  BASELINE  = shipped data/powers.json (Temperature Protection stale: no
              +MaxHP, Regeneration flagged unbuffable)
  PATCHED   = a SCRATCH powers.json with TP corrected to the current client
              bins (out_full, 2026-07-16): +MaxHP (HitPoints/Maximum,
              Melee_HealSelf) added, Regeneration un-flagged + Heal added to
              accepted enhancement types. NOTHING is written to the shipped
              data — this is measurement only, per harden-before-certify.

Prints, per build: def/res/HP, regen HP/s, the full sustain ledger (every
self-heal rate + interrupt flag), sustain HP/s, and the certified AFK tier.
The decisive number: does the Burn build clear the +4x8 line (~37 HP/s) once
TP carries its 6/23 attributes?
"""
import copy
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CODE = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
import server as srv  # noqa: E402
import first_principles as fp  # noqa: E402
import mids_import  # noqa: E402

BUILDS = [
    ("Burn", "Rad_FA_Farmer_Burn_4.mbd"),
    ("Atom Smasher", "Rad_FA_Farmer_AS_4.mbd"),
    ("Stone/Rooted", "Rad_Stone_AFK_Farmer_4R.mbd"),
]

# The current-client TP correction (source: out_full/brute_defense/fiery_aura/
# temperature_protection.json, 2026-07-16 export; client bin_powers.pigg
# 2026-07-07 = post-6/23). Applied to EVERY AT's Fiery Aura TP record.
# Engine convention (verified against Dull Pain / Earth's Embrace records):
# a power's +MaxHP is effect "HitPoints", enhance_aspect "HitPoints", on the
# Melee_HealSelf table; the value >3 flat-HP path in _add_power_effect converts
# to a base-HP fraction. Client scale = 1.0 (HitPoints/Maximum template).
TP_MAXHP_EFFECT = {
    "effect": "HitPoints", "damage_type": "None", "scale": 1.0, "nmag": 1.0,
    "modifier_table": "Melee_HealSelf", "enhance_aspect": "HitPoints",
    "ed_schedule": 0, "pv_mode": 0, "duration": 10.25,
    "_source": "client bins 2026-07-16 (6/23 patch): HitPoints/Maximum",
}


def patch_tp(powers_data):
    """Return a deep-copied powers.json with every Fiery Aura Temperature
    Protection corrected to the current client. Reports what it touched."""
    data = copy.deepcopy(powers_data)
    touched = []
    for pset_key, plist in data.items():
        if not isinstance(plist, list):
            continue
        for p in plist:
            if not str(p.get("full_name", "")).endswith(
                    ".Temperature_Protection"):
                continue
            se = p.setdefault("self_effects", [])
            # (a) un-flag the regen. Making it ENHANCEABLE (6/23: Heal boosts
            # it) means the slotted Heal pieces must reach it — the engine keys
            # enhancement on enhance_aspect, so retag Regeneration's aspect to
            # "Heal" (boosts_allowed=['Res_Damage','Heal'] in the client). Both
            # deltas printed so the base-vs-enhanced split is legible.
            for e in se:
                if e.get("effect") == "Regeneration":
                    e.pop("unbuffable", None)
                    e["enhance_aspect"] = "Heal"
            # (b) add +MaxHP if absent
            if not any(e.get("effect") == "MaxHP" for e in se):
                se.append(dict(TP_MAXHP_EFFECT))
            # (c) allow Heal enhancement + Healing set category
            if "Healing" not in (p.get("accepted_set_categories") or []):
                p.setdefault("accepted_set_categories", []).append("Healing")
            ets = p.setdefault("accepted_enhancement_types", [])
            if "Heal" not in ets:
                ets.append("Heal")
            touched.append(p.get("full_name"))
    return data, touched


def evaluate(build, at, powers_data):
    """Score an imported build under the given powers table. Returns the
    totals + the sustain ledger."""
    # rebind the module-level tables the engine/ledger read
    srv.POWER_BY_FULL = {p["full_name"]: p
                         for plist in powers_data.values()
                         if isinstance(plist, list) for p in plist}
    ctx = srv._stat_ctx(at)
    ctx["power_by_full"] = srv.POWER_BY_FULL
    arch_row = srv.ARCH_BY_NAME.get(at)
    res_cap = round((arch_row or {}).get("res_cap", 0.90) * 100, 1)
    powers = build["powers"]
    tot = srv.engine.calculate_build({"archetype": at, "powers": powers},
                                     srv.SET_BONUSES, res_cap=res_cap, ctx=ctx)
    ledger = fp.afk_sustain_assessment(powers, tot, arch_row, ctx,
                                       role_output_mod=srv.role_output)
    return tot, ledger


def fmt_def_res(tot):
    d = tot.get("defense", {})
    r = tot.get("resistance", {})
    fd = (d.get("Fire") or {}).get("value", 0)
    fr = (r.get("Fire") or {}).get("value", 0)
    return f"fire def {fd:.1f} / fire res {fr:.1f}"


def main():
    lk = srv._import_lookups()
    shipped = srv.engine  # unused; keep POWER_BY_FULL reference
    orig_pbf = dict(srv.POWER_BY_FULL)
    powers_path = os.path.join(ROOT, "data", "powers.json")
    base_data = json.load(open(powers_path, encoding="utf-8"))
    patched_data, touched = patch_tp(base_data)
    print(f"TP correction touches {len(touched)} records "
          f"(all ATs' Fiery Aura): {sorted(set(touched))[:3]}...\n")

    for label, fn in BUILDS:
        path = os.path.join(CODE, "maelwys_builds", fn)
        data = json.load(open(path, encoding="utf-8"))
        parsed = mids_import.parse_build(data, lk)
        if not parsed.get("ok"):
            print(f"[{label}] IMPORT FAILED: {parsed.get('error')}")
            continue
        at = parsed["archetype"]
        build = parsed["build"]
        npow = len(build["powers"])
        unres = parsed.get("unresolved_powers") or []
        print(f"=== {label}  ({fn})  AT={at.split('_')[-1]}  "
              f"{npow} powers"
              + (f"  UNRESOLVED: {unres}" if unres else "") + " ===")
        for tag, pdata in (("BASELINE (stale TP)", base_data),
                           ("PATCHED  (6/23 TP)", patched_data)):
            tot, led = evaluate(build, at, pdata)
            print(f"  {tag}: {fmt_def_res(tot)} | HP {led['hp']:.0f} "
                  f"| regen {led['regen_hps']:.1f} HP/s "
                  f"| auto-heal {led['auto_fire_heal']} "
                  f"{led['auto_fire_hps']:.1f} | SUSTAIN {led['sustain_hps']:.1f}"
                  f" HP/s -> {('+' + str(led['tier']) + 'x8') if led['tier'] is not None else 'NONE'}")
            for hr in led["heal_rates"]:
                print(f"        heal: {hr['power']} {hr['self_hps']:.1f} HP/s"
                      + ("  [INTERRUPTIBLE]" if hr["interruptible"] else ""))
        print()
    srv.POWER_BY_FULL = orig_pbf


if __name__ == "__main__":
    main()

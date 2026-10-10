"""Additive patcher: Traps DETONATOR as a death trigger (Issue 28 Page 4).

Page 4 changed Mastermind_Buff.Traps.Detonator from "pick a henchman and blow it
up" (Grant_Power Time_Bomb) to "every henchman carries explosives that go off when
it is defeated": Grant_Boosted_Power of Villain_Pets.Traps_TimeBomb.Time_Bomb to
MyPet, a Click flagged castable_after_death = DeadOnly. Boosted = the Detonator's
own slotting reaches the bomb.

Writes onto our Detonator record a `death_bomb` block read from the client:
  power, accuracy, radius, max_targets, damage rows (scale x table, typed)
and corrects our Time_Bomb pet record's damage rows to the client's (ours carried
Fire/Lethal swapped). The scorer prices it as henchman deaths/s x bomb damage.

  python tools/patch_detonator.py           # report
  python tools/patch_detonator.py --write
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_client_delta as scd  # noqa: E402

DET = "Mastermind_Buff.Traps.Detonator"


def main():
    write = "--write" in sys.argv
    data = json.loads(open(scd.POWERS, "rb").read().decode("utf-8"))
    ax = scd.load_export(scd.AFTER)
    grants = [n for g in ax[DET]["effects"] for t in g["templates"]
              if t["attribs"] == ["Grant_Boosted_Power"] for n in t["params"]["power_names"]]
    bombs = [n for n in grants if ax.get(n, {}).get("castable_after_death") == "DeadOnly"]
    if len(bombs) != 1:
        sys.exit(f"REFUSE: Detonator grants {grants}, DeadOnly {bombs}")
    b = ax[bombs[0]]
    rows = [{"damage_type": scd.DMG[t["attribs"][0][:-4]], "scale": t["scale"],
             "modifier_table": t["table"]}
            for g in b["effects"] if not scd._req(g).strip()
            for t in g["templates"]
            if len(t["attribs"]) == 1 and t["attribs"][0].endswith("_Dmg")
            and t["aspect"] in ("Absolute", "Current")]
    if not rows:
        sys.exit("REFUSE: no damage rows on the bomb")
    det = next(p for p in data["Mastermind_Buff.Traps"] if p["full_name"] == DET)
    det["death_bomb"] = {"power": bombs[0], "accuracy": b["accuracy"], "radius": b["radius"],
                         "max_targets": b["max_targets_hit"], "damage": rows}
    print(f"  DETONATOR  death_bomb {det['death_bomb']}")
    pet = next(p for p in data[bombs[0].rsplit(".", 1)[0]] if p["full_name"] == bombs[0])
    fixed = 0
    for d in pet.get("damage_effects") or []:
        if d.get("pv_mode") == 2:
            continue
        want = next((r for r in rows if r["damage_type"] == d["damage_type"]), None)
        if want and d["scale"] != want["scale"]:
            print(f"  TIME BOMB  {d['damage_type']} {d['scale']} -> {want['scale']} (client)")
            d["scale"] = want["scale"]
            fixed += 1
    if write:
        with open(scd.POWERS, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        print(f"wrote {scd.POWERS}")


if __name__ == "__main__":
    main()

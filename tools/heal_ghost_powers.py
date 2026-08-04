"""Remove GHOST powers from a save file — picks whose powerset is no longer
part of the build's identity (2026-08-04: set changes used to leave the old
set's powers in build.powers, invisible on the wall but solved by the ILP;
fd8da705 prevents NEW ghosts, this heals saves that already carry them).

Usage:  python tools/heal_ghost_powers.py <save.json path>

Keeps: powers of the current primary / secondary / epic / chosen pools,
every Inherent.*, and the VEAT base sets (a branch build legally holds base
Arachnos powers). Everything else is a ghost and is removed, listed by name.
Writes a .json.bak of the original first. Run with the app CLOSED — a
running app can autosave its in-memory copy back over the heal.
"""
import json
import shutil
import sys

VEAT_BASE = {"Arachnos_Soldiers.Arachnos_Soldier", "Training_Gadgets.Training_and_Gadgets",
             "Widow_Training.Widow_Training", "Teamwork.Teamwork"}


def heal(path):
    save = json.load(open(path, encoding="utf-8"))
    b = save.get("build") or {}
    keep_sets = {b.get("primary"), b.get("secondary"), b.get("epic"),
                 *(b.get("pools") or []), *VEAT_BASE} - {None, ""}
    ghosts, kept = [], []
    for p in (b.get("powers") or []):
        fn = p.get("full_name") or ""
        ps = fn.rsplit(".", 1)[0]
        if fn.startswith("Inherent.") or ps in keep_sets:
            kept.append(p)
        else:
            ghosts.append(p)
    if not ghosts:
        print(f"No ghosts in {path} — {len(kept)} powers all belong to the build.")
        return 0
    shutil.copyfile(path, path + ".bak")
    b["powers"] = kept
    with open(path, "w", encoding="utf-8") as f:
        json.dump(save, f, indent=1)
    print(f"Removed {len(ghosts)} ghost power(s) from '{save.get('name')}' "
          f"({len(kept)} kept); original preserved as .bak:")
    for g in ghosts:
        slots = len([s for s in (g.get("slots") or []) if s])
        print(f"  ✂ {g.get('display_name') or g.get('full_name')}  "
              f"[{g.get('full_name')}] ({slots} slotted)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(heal(sys.argv[1]))

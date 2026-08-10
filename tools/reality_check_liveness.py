"""Liveness check: no content may exist that the last SHIPPED snapshot lacks.

THE FAILURE THIS EXISTS FOR (2026-08-10): 34 records (Wind Control, Gadgetry,
Utility Belt, Boomerang Slice) were synthesised from the client bins and reached
two certified champions. The bins prove MECHANICS, not LIVENESS - the game ships
assets for content that never matured. The liveness authority is the Mids-derived
data/powers.json AS SHIPPED in the last release, which tracks live Homecoming.
Every other check compared the client to our data; none asked whether the
client's content is in the game. This one asks exactly that.

Baseline = data/powers.json + data/powersets.json at the highest release tag.
Any power record or offered powerset present now and absent then (or vice versa)
HARD-FAILS unless dispositioned in tools/liveness_dispositions.json with its
evidence - and a disposition naming a diff that no longer exists also fails
(two-way pin, the prereq-baseline contract).

Legitimate additions arrive ONLY via a real game patch reaching the Mids-derived
snapshot (PATCH-WATCH), at which point the release that ships them moves the
baseline tag forward automatically.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISP_PATH = os.path.join(ROOT, "tools", "liveness_dispositions.json")


def latest_release_tag():
    out = subprocess.run(["git", "tag", "--list", "v*"], cwd=ROOT,
                         capture_output=True, text=True, check=True)
    tags = [t.strip() for t in out.stdout.splitlines() if re.fullmatch(r"v\d+(\.\d+)*", t.strip())]
    if not tags:
        sys.exit("liveness: no release tags found")
    return max(tags, key=lambda t: [int(x) for x in t[1:].split(".")])


def git_json(tag, path):
    out = subprocess.run(["git", "show", f"{tag}:{path}"], cwd=ROOT,
                         capture_output=True, check=True)
    return json.loads(out.stdout.decode("utf-8"))


def power_names(powers):
    return {p["full_name"] for recs in powers.values() for p in recs}


def offered_sets(powersets):
    names = {p["full_name"] for p in powersets.get("pools", [])}
    for sides in powersets.get("by_archetype", {}).values():
        for lst in sides.values():
            for entry in lst:
                names.add(entry["full_name"] if isinstance(entry, dict) else entry)
    return names


def check(cur_p, old_p, cur_s, old_s, disp):
    """Return the list of failure strings. Pure, so the battery can sabotage it."""
    diffs = {
        "power added":    sorted(cur_p - old_p),
        "power removed":  sorted(old_p - cur_p),
        "offer added":    sorted(cur_s - old_s),
        "offer removed":  sorted(old_s - cur_s),
    }
    all_diff_names = {n for names in diffs.values() for n in names}
    failures = []
    for kind, names in diffs.items():
        for n in names:
            if n not in disp:
                failures.append(f"UNDISPOSITIONED {kind}: {n}")
    for n in disp:
        if n not in all_diff_names:
            failures.append(f"STALE disposition (diff no longer exists): {n}")
    return failures


def main():
    gate = "--gate" in sys.argv
    tag = latest_release_tag()

    cur_p = power_names(json.load(open(os.path.join(ROOT, "data", "powers.json"), encoding="utf-8")))
    cur_s = offered_sets(json.load(open(os.path.join(ROOT, "data", "powersets.json"), encoding="utf-8")))
    old_p = power_names(git_json(tag, "data/powers.json"))
    old_s = offered_sets(git_json(tag, "data/powersets.json"))

    disp = {}
    if os.path.exists(DISP_PATH):
        disp = json.load(open(DISP_PATH, encoding="utf-8"))

    failures = check(cur_p, old_p, cur_s, old_s, disp)

    diff_count = len(cur_p ^ old_p) + len(cur_s ^ old_s)
    print(f"liveness: baseline {tag} | powers {len(cur_p)} current vs {len(old_p)} shipped | "
          f"offered sets {len(cur_s)} current vs {len(old_s)} shipped | "
          f"diffs {diff_count} | dispositions {len(disp)}")
    for f in failures:
        print("  " + f)
    if failures:
        if not gate:
            print("\nContent not in the shipped Mids-derived snapshot is NOT LIVE until the "
                  "game says otherwise. Disposition it in tools/liveness_dispositions.json "
                  "with its evidence, or remove it.")
        sys.exit(1)
    print("liveness: OK")


if __name__ == "__main__":
    main()

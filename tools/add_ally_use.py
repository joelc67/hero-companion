"""Additive patcher: ALLY USE of dual-use powers (Issue 28 Page 4).

Page 4 made Sonic Cage, Refraction Shield and Detention Field castable on a friend:
the client splits their effect groups on `target.isFriend?` - a foe is caged, a
friend gets +Defense/+Resistance for 15s, and a `Recharge_Power` template sets the
power's OWN recharge to 90s for that use (60s base on a foe).

This writes, onto every one of our powers whose current client record carries a
friend-side group, an `ally_use` block read from the client (never assumed):
  base_recharge  the friend group's Recharge_Power magnitude
  buff_effects   the friend-side rows, through sync_client_delta.convert(side_only="ally")
The engine swaps it in when the player's setting "I use my cages on teammates" is
on (server settings `cage_on_allies`); off, the record is unchanged.

  python tools/add_ally_use.py           # report
  python tools/add_ally_use.py --write
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_client_delta as scd  # noqa: E402


def _recharge_override(crec):
    vals = {float(t["scale"]) for g in crec.get("effects") or []
            if scd._req(g).split().count("target.isFriend?") and "!" not in
            scd._req(g).replace("target.isFriend? !", "").split()
            for t in g.get("templates") or [] if t.get("attribs") == ["Recharge_Power"]}
    if len(vals) != 1:
        sys.exit(f"REFUSE: {crec['full_name']} friend Recharge_Power values {vals}")
    return vals.pop()


def main():
    write = "--write" in sys.argv
    data = json.loads(open(scd.POWERS, "rb").read().decode("utf-8"))
    alias = json.load(open(scd.ALIASES, encoding="utf-8")).get("aliases", {})
    ax = scd.load_export(scd.AFTER)
    res = dict(ax)
    res.update(scd.load_redirects(scd.AFTER))
    n = 0
    for recs in data.values():
        for p in recs:
            c = ax.get(alias.get(p["full_name"], p["full_name"]))
            # dual-use = a friend-side group that resets the power's own recharge
            if not c or not any("target.isFriend?" in scd._req(g).split()
                                and "target.isFriend? !" not in scd._req(g)
                                and any(t.get("attribs") == ["Recharge_Power"]
                                        for t in g.get("templates") or [])
                                for g in c.get("effects") or []):
                continue
            rows, un = scd.convert(c, res, patch=True, side_only="ally")
            buffs = [scd._row_from(k, None) for k in rows.get("buff_effects", scd.Counter()).elements()]
            other = {b: sum(v.values()) for b, v in rows.items() if b != "buff_effects" and v}
            if other or not buffs:
                sys.exit(f"REFUSE: {p['full_name']} ally rows outside buff_effects {other} / none")
            left = {k: v for k, v in un.items() if not k.startswith("Recharge_Power/")}
            if left:
                sys.exit(f"REFUSE: {p['full_name']} unmapped ally templates {left}")
            p["ally_use"] = {"base_recharge": _recharge_override(c), "buff_effects": buffs}
            n += 1
            print(f"  ALLY USE  {p['full_name']}: recharge {p['ally_use']['base_recharge']}s, "
                  f"{len(buffs)} buff rows ({sorted({b['effect'] for b in buffs})}, "
                  f"{buffs[0]['duration']}s)")
    print(f"{n} dual-use powers")
    if write:
        with open(scd.POWERS, "w", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        print(f"wrote {scd.POWERS}")


if __name__ == "__main__":
    main()

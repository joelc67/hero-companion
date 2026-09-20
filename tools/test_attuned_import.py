"""Attuned-uid import battery (field report 2026-09-19, ChainsawHands).

The in-game /build_save_file export writes an attuned piece as
"Attuned_<Set>_<L>"; our catalog stores only "Crafted_<Set>_<L>" for those
sets, so both importers missed the uid and the slot came back EMPTY.

  - an attuned set piece resolves to its catalog piece and keeps attuned=True;
  - the crafted uid still resolves (control);
  - Superior_Attuned_* never aliases to a non-Superior set (different set).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import server as srv  # noqa: E402
import ingame_import  # noqa: E402

EXPORT = """Chainsaw: Level 50 Magic Class_Scrapper

Character Profile:
------------------
Level 1: Scrapper_Melee Fiery_Melee Fire_Sword
\tAttuned_Touch_of_Death_F (1)
\tAttuned_Achilles_Heel_C (1)
\tCrafted_Touch_of_Death_A (50)
------------------
Badges Earned:
"""

CHECKS, FAILS = 0, []


def check(ok, label):
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILS.append(label)


res = ingame_import.parse_ingame_build(EXPORT, srv._import_lookups())
check(res.get("ok"), "export parsed")
slots = res["build"]["powers"][0]["slots"]
check(res["unresolved_enh"] == [], f"no unresolved enh (got {res['unresolved_enh']})")
check(slots[0]["set_name"] == "Touch of Death" and slots[0]["attuned"] is True,
      f"attuned ToD proc resolved (got {slots[0]})")
check(slots[1]["set_name"] == "Achilles' Heel" and slots[1]["attuned"] is True,
      f"attuned Achilles proc resolved (got {slots[1]})")
check(slots[2]["set_name"] == "Touch of Death" and slots[2]["attuned"] is False,
      f"crafted control resolved (got {slots[2]})")

# Superior ATOs are their own sets — an alias across Superior_ would price a
# Superior piece off the plain set's values.
for uid, slot in srv.PIECE_BY_UID_IMPORT.items():
    if uid.startswith("Superior_"):
        check(slot["piece_uid"].startswith("Superior_"),
              f"{uid} maps to a Superior piece (got {slot['piece_uid']})")

# The aliases live in an import-only map: PIECE_BY_UID itself must stay one
# entry per piece, or every helper that enumerates .values() slots duplicates.
check(len(set(id(s) for s in srv.PIECE_BY_UID.values()))
      == len(srv.PIECE_BY_UID), "PIECE_BY_UID has no duplicate slot objects")
check(len(srv.PIECE_BY_UID_IMPORT) > len(srv.PIECE_BY_UID), "aliases registered")

# An attuned piece serializes as "(1)" in the export. Resolving it to the crafted
# piece must NOT price it as a level-1 IO: the engine ignores io_level when
# attuned=True and scales to the character level, so the recovered slot is worth
# the same as the crafted level-50 copy.
import engine  # noqa: E402

CTX = srv._stat_ctx("Class_Scrapper")
attuned = dict(srv.PIECE_BY_UID["Crafted_Touch_of_Death_A"], io_level=1, attuned=True)
crafted = dict(srv.PIECE_BY_UID["Crafted_Touch_of_Death_A"], io_level=50, attuned=False)
check(dict(engine._scaled_boosts(attuned, dict(CTX, char_level=50)))
      == dict(engine._scaled_boosts(crafted, CTX)),
      "attuned import prices at char level, not level 1")

print(f"{CHECKS - len(FAILS)}/{CHECKS} checks passed")
for f in FAILS:
    print("FAIL:", f)
sys.exit(1 if FAILS else 0)

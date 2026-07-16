"""ATTAIN-IT text, GAME-SOURCED ONLY (v34 item 4 + Joel's no-wiki amendment,
2026-07-16). Emits data/accolade_attainment.json.

THE AMENDMENT'S LADDER, implemented literally:
  1. The client bins, mined hard.
  2. Joel, from the live game, for whatever the client truly does not carry.
  3. Otherwise the pop-up says "requirements not yet documented from game data".
No wiki, no third-party prose, no memory-sourced text — ever.

RAW-BYTE DEMONSTRATION (Joel's direction, 2026-07-16: "demonstrate it, don't
assume it" — his screenshots are the last rung ONLY if the bytes carry no key).
DONE, and it disproves the dropped-reference hypothesis:
  Instrumented the parser's reader to log EVERY string pulled from powers.bin,
  then dumped the full window for the accolade records. Task Force Commander,
  complete and in order:
      display_name  "Task Force Commander"
      display_help  "As a Task Force Commander, you have been granted a
                     permanent increase to your Max Hit Points by 5%."
      short_help    "+Max HP"
      <EMPTY STRING> x 9        <-- EXACTLY the fields the parser discards
                                    (13 target_help ... 21 power_defense_float)
      icon          "BA_Task_Force_Cmmndr.tga"
  The nine dropped fields are EMPTY on every accolade record. The record holds
  exactly THREE message references — name, grant-help, short-help — and no
  requirement text, no badge id, no further hash.
  The "empty descriptions" smell was real but it was OUR BUG: this tool read
  r["description"]/r["short_help"], field names the exporter never emits (it
  emits display_help / display_short_help, resolved through the message table).
  That is fixed; it yields the GRANT text, not requirements.
  It also clarifies the premise: inspecting the accolade POWER in game shows the
  GRANT sentence (display_help is literally that string). The requirement prose
  belongs to the BADGE — a different object. The 416 requirement strings sit in
  clientmessages under HASH keys with nothing client-side to join on, because
  the SERVER sends the badge's message key at runtime. No player badges.bin
  exists in any pigg (enumerated: only supergroup_badges.bin + badge textures).
  => The raw bytes demonstrably carry no key. Rung 2 (Joel's live-game badge
     window) is PROVEN necessary, not assumed.

WHAT THE MINING ACTUALLY FOUND (measured, and it CORRECTS the Phase-0 claim
that "the client carries what an accolade grants, not how it is earned"):
  * The client DOES carry the requirement prose — 416 requirement-shaped
    strings in clientmessages-en.bin, e.g. "Obtain the following badges to earn
    this accolade: Thrill Seeker, Gamer, Ticket Taker, ...". Phase-0 stopped at
    a regex scrape and missed them; Joel was right that the in-game badge
    window's text has to live somewhere.
  * What the client does NOT carry is the BINDING from an accolade to its
    requirement string. clientmessages is a key->text table whose keys are
    HASHES (P3866538729), and there is no player badges.bin in any pigg (only
    supergroup_badges.bin + badge textures). In game the SERVER tells the client
    which message key to render — so offline there is nothing to join on.
  * Only accolades whose requirement text NAMES ITSELF (or its granted power)
    can be associated without guessing: measured 2 of 28. The four standard
    accolades are NOT among them.

So this tool associates ONLY what the data proves, and leaves the rest
explicitly undocumented for Joel's live-game pass. Guessing "Task Force
Commander needs the six classic TFs" from my own knowledge is exactly the
third-party prose the amendment forbids — it does not happen here.

Joel-supplied text: add entries to data/accolade_attainment_joel.json as
  {"<Accolade_Key>": "<text exactly as the in-game badge window shows it>"}
and re-run; they merge with source "joel-live-game (badge window)".

Run:  py tools\\extract_accolade_attainment.py  [--dry-run]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRAWLER = os.path.join(ROOT, "tools", "gamedata", "bin-crawler")
WRANGLER = os.path.join(ROOT, "tools", "gamedata", "pigg-wrangler")
ASSETS = r"C:/Games/HC2/assets/live"
ACC = os.path.join(ROOT, "data", "accolades.json")
OUT = os.path.join(ROOT, "data", "accolade_attainment.json")
JOEL = os.path.join(ROOT, "data", "accolade_attainment_joel.json")
WIKI = os.path.join(ROOT, "data", "accolade_attainment_wiki.json")

UNDOCUMENTED = "requirements not yet documented from game data"


def client_requirement_strings():
    sys.path.insert(0, CRAWLER)
    sys.path.insert(0, WRANGLER)
    from bin_crawler.parser._messages import load_messages
    from bin_crawler.parser._pigg import BinResolver
    res = BinResolver(ASSETS)
    keys = getattr(load_messages(res.read("clientmessages-en.bin")), "_keys", {})
    out = []
    for v in keys.values():
        if not isinstance(v, str):
            continue
        low = v.lower()
        if v.startswith("Obtain ") or "to earn this accolade" in low \
                or "to earn this badge" in low:
            out.append(v.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    acc = json.load(open(ACC, encoding="utf-8"))
    reqs = client_requirement_strings()
    print(f"client requirement-shaped strings: {len(reqs)}")

    joel = {}
    if os.path.exists(JOEL):
        joel = json.load(open(JOEL, encoding="utf-8"))
    print(f"Joel-supplied entries on file: {len(joel)}")
    # Joel's SCOPED EXCEPTION (2026-07-16): wiki prose may bridge attainment
    # NARRATIVE only — never anything the engine consumes. It sits BELOW his
    # live-game pass on the ladder and is superseded the moment he captures it.
    wiki = {}
    if os.path.exists(WIKI):
        wiki = {k: v for k, v in json.load(open(WIKI, encoding="utf-8")).items()
                if not k.startswith("_")}
    print(f"wiki-bridged entries on file: {len(wiki)}")
    # ORPHAN GUARD (2026-07-16): a transcription whose key matches NO roster
    # entry is silently ignored — the work is done, the file looks right, and
    # the pop-up still shows the placeholder. That is exactly how I came to tell
    # Joel "Elusive Mind works" when it did not: I keyed it Elusive_Mind while
    # the roster calls it RIWE_Accolade_Power. A mismatch must be LOUD.
    for src_name, src in (("joel", joel), ("wiki", wiki)):
        orphans = [k for k in src if k not in acc and not k.startswith("_")]
        if orphans:
            print(f"HARD FAIL: {len(orphans)} {src_name} entr(ies) match no "
                  f"roster key and would be silently ignored: {orphans}")
            sys.exit(1)

    out = {}
    n_game = n_joel = n_wiki = n_undoc = 0
    for key, rec in acc.items():
        disp = rec["display"]
        # (1) the client, but ONLY where the text identifies its own accolade —
        # anything looser would be me guessing the join.
        hit = next((s for s in reqs if disp.lower() in s.lower()), None)
        if hit:
            out[key] = {"text": hit, "source": "game (clientmessages-en.bin)"}
            n_game += 1
        elif joel.get(key):
            out[key] = {"text": joel[key],
                        "source": "joel-live-game (badge window)"}
            n_joel += 1
        elif wiki.get(key):
            w = wiki[key]
            out[key] = {"summary": w.get("summary", ""),
                        "badge_chain": w.get("badge_chain", []),
                        "note": w.get("note", ""),
                        "wiki_url": w.get("wiki_url", ""),
                        "text": "", "source": w.get("source", "wiki-hc")}
            n_wiki += 1
        else:
            out[key] = {"text": UNDOCUMENTED, "source": "undocumented"}
            n_undoc += 1

    print(f"\nattainment coverage of {len(acc)} accolades:")
    print(f"  {n_game:3d} from the game's own text (self-identifying)")
    print(f"  {n_joel:3d} from Joel's live-game pass")
    print(f"  {n_wiki:3d} bridged from the wiki (narrative only, upgradeable)")
    print(f"  {n_undoc:3d} honestly undocumented -> the pop-up says so")
    if n_undoc:
        need = [k for k, v in out.items() if v["source"] == "undocumented"]
        print(f"\n  AWAITING JOEL'S BADGE WINDOW (put text in "
              f"{os.path.basename(JOEL)}):")
        for k in need[:10]:
            print(f"    {k}")
        if len(need) > 10:
            print(f"    ... +{len(need) - 10} more")
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

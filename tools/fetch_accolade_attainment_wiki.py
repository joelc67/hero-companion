"""ONE-TIME wiki harvest for attainment NARRATIVE (Joel's scoped exception,
2026-07-16). Writes data/accolade_attainment_wiki.json.

⚠ THE EXCEPTION IS A KEYHOLE, NOT A DOOR — the bounds, verbatim from the ruling:
  1. SCOPE: attainment NARRATIVE ONLY — the how-to-earn prose for the pop-ups.
     No number, effect, requirement-count, or ANYTHING THE ENGINE CONSUMES may
     ever come from a wiki. Display prose exclusively. (Enforced structurally:
     this writes a separate file that only the /accolades pop-up text reads.
     accolades.json — the file the engine's accolade routing consumes — is
     produced by extract_accolades.py from the client bins and is NOT touched
     here.)
  2. LIVE GAME OUTRANKS WIKI. Joel's badge-window pass supersedes any entry
     here the moment it is captured (extract_accolade_attainment.py merges his
     file at a higher rung).
  3. PER-ENTRY SOURCE TAGS, upgradeable. Aged prose gets caught by the
     verification pass, not trusted forever — the June-23 lesson applies to
     text too.
  4. ONE-TIME FETCH, transcribed into our data. Never scraped at runtime, never
     hotlinked.

SOURCE RANKING (Joel's): homecoming.wiki accolade pages = PRIMARY (`wiki-hc`).
The forum guides are cross-check/depth sources; both 404'd on their bare topic
URLs from here, so this harvest is wiki-only and every entry is tagged as such
— a single-source entry is NOT marked `conflict` (nothing disagreed), it is
simply single-sourced and upgradeable.

FETCH NOTE (measured 2026-07-16): homecoming.wiki returns 403 to cloud egress
(Cowork's fetches, and the agent WebFetch tool) but 200 to this Windows box
with a browser UA — index AND deep pages. So the harvest runs here.

Run:  py tools\\fetch_accolade_attainment_wiki.py  [--dry-run]
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACC = os.path.join(ROOT, "data", "accolades.json")
OUT = os.path.join(ROOT, "data", "accolade_attainment_wiki.json")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
INDEXES = ["https://homecoming.wiki/wiki/Hero_Accolade_Badges",
           "https://homecoming.wiki/wiki/Villain_Accolade_Badges"]


def get(url):
    try:
        r = subprocess.run(["curl", "-s", "-A", UA, "-L", "--max-time", "40", url],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="ignore")
        return r.stdout or ""
    except Exception:  # noqa: BLE001
        return ""


def strip(h):
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))
    return re.sub(r"\s+", " ", t).strip()


def deep_links(index_html):
    """{link_text: /wiki/Page} for badge pages listed on an accolade index."""
    out = {}
    for href, text in re.findall(r'href="(/wiki/[^"#:]+)"[^>]*>([^<]{3,70})<',
                                 index_html):
        t = html.unescape(text).strip()
        if t and t not in out:
            out[t] = href
    return out


def parse_page(page_html):
    """The narrative we want: the Description sentence + the badge chain the
    page lists. We take the page's OWN words — no invention."""
    txt = strip(page_html)
    desc = ""
    m = re.search(r"Description (.+?)(?: Accolade Power | Badges | Notes | See Also |$)",
                  txt)
    if m:
        desc = m.group(1).strip()
    # the constituent chain: the page's badge links after the description
    chain = []
    for href, text in re.findall(r'href="(/wiki/[^"#:]+_Badge)"[^>]*>([^<]{3,60})<',
                                 page_html):
        t = html.unescape(text).strip()
        if t and t not in chain:
            chain.append(t)
    return desc, chain


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    acc = json.load(open(ACC, encoding="utf-8"))

    # map our roster display names -> the wiki's page for that accolade
    links = {}
    for ix in INDEXES:
        h = get(ix)
        print(f"index {ix.rsplit('/', 1)[-1]}: {len(h)} bytes")
        links.update(deep_links(h))
        time.sleep(1)

    def find_page(display):
        for t, href in links.items():
            tl, dl = t.lower(), display.lower()
            if tl == dl or tl == dl + " badge" or dl in tl:
                return t, href
        return None, None

    out, n_hit = {}, 0
    for key, rec in acc.items():
        disp = rec["display"]
        title, href = find_page(disp)
        if not href:
            continue
        page = get("https://homecoming.wiki" + href)
        time.sleep(1)
        if not page or "Unofficial Homecoming Wiki" not in page:
            continue
        desc, chain = parse_page(page)
        if not desc and not chain:
            continue
        out[key] = {
            "wiki_title": title, "wiki_url": "https://homecoming.wiki" + href,
            "description": desc[:600],
            "badge_chain": chain[:24],
            "source": "wiki-hc",
            "fetched": "2026-07-16",
        }
        n_hit += 1
        print(f"  {key:28s} chain={len(chain):2d}  {desc[:56]}")

    print(f"\nharvested {n_hit} of {len(acc)} accolades from the wiki")
    if args.dry_run:
        print("--dry-run: nothing written.")
        return
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

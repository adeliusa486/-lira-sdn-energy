"""Search Crossref for recent papers (with abstracts) to support the literature review.

Usage: python tools/search_literature.py "query one" "query two" ... [--from 2021] [--rows 6]
Prints DOI | year | venue | first authors | title, then a short abstract excerpt when Crossref has one.
Only papers whose abstract you have read may be cited, and every DOI still goes through verify_refs.py.
"""
import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "lira-lit-search/1.0 (mailto:research@example.org)"}


def search(q, since, rows):
    params = urllib.parse.urlencode({"query.bibliographic": q, "rows": rows, "filter": f"from-pub-date:{since}-01-01,type:journal-article,type:proceedings-article"})
    req = urllib.request.Request("https://api.crossref.org/works?" + params, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["message"]["items"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("queries", nargs="+")
    ap.add_argument("--from", dest="since", default="2021")
    ap.add_argument("--rows", type=int, default=6)
    a = ap.parse_args()
    for q in a.queries:
        print(f"\n=== {q}")
        try:
            items = search(q, a.since, a.rows)
        except Exception as ex:
            print("  error:", ex)
            continue
        for it in items:
            title = (it.get("title") or [""])[0]
            venue = (it.get("container-title") or [""])[0]
            year = (it.get("issued", {}).get("date-parts") or [[None]])[0][0]
            authors = "; ".join(f"{x.get('given', '')} {x.get('family', '')}".strip() for x in it.get("author", [])[:4])
            print(f"- {it['DOI']} | {year} | {venue[:60]} | {authors}\n  {title}")
            abs_ = it.get("abstract")
            if abs_:
                txt = html.unescape(re.sub(r"<[^>]+>", " ", abs_))
                print("  ABS:", " ".join(txt.split())[:420])
        time.sleep(2.5)


if __name__ == "__main__":
    main()

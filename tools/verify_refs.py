"""Verify BibTeX entries against Crossref (DOI) and arXiv (eprint).

Usage: python tools/verify_refs.py references_candidate.bib [--out results/ref_verification.csv]
Writes a CSV with status PASS / MISMATCH / NOT_FOUND / URL_OK / URL_FAIL / NO_ID per entry,
plus references_verified.bib containing PASS and URL_OK entries.
"""
import argparse
import csv
import difflib
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import json

UA = {"User-Agent": "lira-ref-verifier/1.0 (mailto:research@example.org)"}


def parse_bib(text):
    entries = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,]+),(.*?)\}\s*(?=\n@|\n%|\Z)", text, re.S):
        body = m.group(3)
        fields = dict((k.lower(), v.strip()) for k, v in re.findall(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", body))
        entries.append({"type": m.group(1), "key": m.group(2).strip(), "raw": m.group(0), **fields})
    return entries


def norm(s):
    s = re.sub(r"[{}\\]", "", s or "")
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return " ".join(s.split())


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def check_doi(e):
    try:
        _, body = get("https://api.crossref.org/works/" + urllib.parse.quote(e["doi"]))
    except Exception as ex:
        return "NOT_FOUND", str(ex)[:80], ""
    msg = json.loads(body)["message"]
    title = (msg.get("title") or [""])[0]
    year = str((msg.get("issued", {}).get("date-parts") or [[None]])[0][0])
    ratio = difflib.SequenceMatcher(None, norm(title), norm(e.get("title"))).ratio()
    # Crossref sometimes stores only the main title (before the colon)
    main = re.split(r"[:—]|---", re.sub(r"[{}]", "", e.get("title", "")))[0]
    ratio = max(ratio, difflib.SequenceMatcher(None, norm(title), norm(main)).ratio())
    # allow +-1 year (online-first vs. print issue)
    year_ok = not e.get("year") or year == "None" or abs(int(e["year"]) - int(year)) <= 1
    ok = ratio >= 0.9 and year_ok
    return ("PASS" if ok else "MISMATCH"), f"title_ratio={ratio:.2f} cr_year={year}", title


def check_arxiv(e):
    try:
        _, body = get("http://export.arxiv.org/api/query?id_list=" + e["eprint"])
    except Exception as ex:
        return "NOT_FOUND", str(ex)[:80], ""
    m = re.search(r"<entry>.*?<title>(.*?)</title>", body.decode(), re.S)
    if not m:
        return "NOT_FOUND", "no entry", ""
    ratio = difflib.SequenceMatcher(None, norm(m.group(1)), norm(e.get("title"))).ratio()
    return ("PASS" if ratio >= 0.9 else "MISMATCH"), f"title_ratio={ratio:.2f}", m.group(1).strip()


def check_url(e):
    try:
        status, _ = get(e["url"])
        return ("URL_OK" if status == 200 else "URL_FAIL"), f"http={status}", ""
    except Exception as ex:
        return "URL_FAIL", str(ex)[:80], ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bib")
    ap.add_argument("--out", default="results/ref_verification.csv")
    a = ap.parse_args()
    entries = parse_bib(open(a.bib, encoding="utf-8").read())
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    rows, keep = [], []
    for e in entries:
        if e.get("doi"):
            st, info, found = check_doi(e)
        elif e.get("eprint"):
            st, info, found = check_arxiv(e)
        elif e.get("url"):
            st, info, found = check_url(e)
        else:
            st, info, found = "NO_ID", "", ""
        rows.append([e["key"], st, info, e.get("title", ""), found])
        if st in ("PASS", "URL_OK"):
            keep.append(e["raw"])
        print(f"{st:10s} {e['key']:28s} {info}")
        time.sleep(0.3)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["key", "status", "info", "bib_title", "source_title"])
        w.writerows(rows)
    with open(os.path.join(os.path.dirname(os.path.abspath(a.bib)), "references_verified.bib"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(keep) + "\n")
    bad = sum(r[1] not in ("PASS", "URL_OK") for r in rows)
    print(f"\n{len(rows)} entries, {len(rows) - bad} verified, {bad} need attention")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()

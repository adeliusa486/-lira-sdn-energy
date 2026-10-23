"""Fetch official BibTeX for DOIs via doi.org content negotiation.

Usage: python tools/doi2bib.py key1=10.xxxx/yyy key2=10.xxxx/zzz ... >> references_candidate.bib
The citation key is replaced by the given key. Review the output before using it.
"""
import re
import sys
import time
import urllib.request

for arg in sys.argv[1:]:
    key, doi = arg.split("=", 1)
    req = urllib.request.Request("https://doi.org/" + doi, headers={"Accept": "application/x-bibtex; charset=utf-8", "User-Agent": "lira-doi2bib/1.0 (mailto:research@example.org)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            bib = r.read().decode("utf-8").strip()
    except Exception as ex:
        print(f"% FAILED {key} {doi}: {ex}")
        continue
    bib = re.sub(r"^@(\w+)\{[^,]*,", lambda m: "@" + m.group(1).lower() + "{" + key + ",", bib, count=1)
    bib = re.sub(r",\s*month\s*=\s*\w+", "", bib)
    print(bib + "\n")
    time.sleep(1.5)

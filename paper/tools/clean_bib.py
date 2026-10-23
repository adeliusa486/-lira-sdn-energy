"""Keep only cited entries in paper/references.bib (reads citations from main.aux).

Usage (from paper/): python tools/clean_bib.py
"""
import re

KEY = re.compile(r"@\w+\{([^,]+),")
aux = open("main.aux", encoding="utf-8").read()
cited = set()
for group in re.findall(r"\\citation\{([^}]*)\}", aux):
    cited.update(k.strip() for k in group.split(","))
entries = [e for e in re.split(r"\n\s*\n", open("references.bib", encoding="utf-8").read().strip()) if KEY.match(e)]
keep = [e for e in entries if KEY.match(e).group(1).strip() in cited]
dropped = [KEY.match(e).group(1) for e in entries if e not in keep]
open("references.bib", "w", encoding="utf-8").write("\n\n".join(keep) + "\n")
kept_keys = {KEY.match(e).group(1).strip() for e in keep}
print(f"cited={len(cited)} kept={len(keep)} dropped={dropped}")
print("cited but missing from bib:", sorted(cited - kept_keys))
print("entries without doi or url:", [KEY.match(e).group(1) for e in keep if "doi=" not in e and "url=" not in e])

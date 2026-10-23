"""One-off helper: LaTeX macro names cannot contain digits, so rewrite digit-containing
macro names in main_v2.tex to the spelled-out names used in generated/results_macros.tex."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BS = chr(92)
W = {"0": "Zero", "1": "One", "2": "Two", "3": "Three", "4": "Four", "5": "Five",
     "6": "Six", "7": "Seven", "8": "Eight", "9": "Nine"}
mac = (ROOT / "paper" / "generated" / "results_macros.tex").read_text(encoding="utf-8")
names = set(re.findall(r"newcommand\{" + re.escape(BS) + r"([A-Za-z]+)\}", mac))
p = ROOT / "paper" / "main_v2.tex"
s = p.read_text(encoding="utf-8")
used = set(re.findall(re.escape(BS) + r"([A-Za-z]+[0-9][A-Za-z0-9]*)", s))
fix = {u: "".join(W.get(c, c) for c in u) for u in used}
fix = {k: v for k, v in fix.items() if v in names}
print(fix)
for k in sorted(fix, key=len, reverse=True):
    s = re.sub(re.escape(BS + k) + r"(?![A-Za-z0-9])", lambda m, v=fix[k]: BS + v, s)
p.write_text(s, encoding="utf-8")

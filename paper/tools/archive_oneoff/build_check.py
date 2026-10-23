"""Compile main_v2.tex with temporary stand-ins for macros that are not generated yet."""
import subprocess
from pathlib import Path

paper = Path(__file__).resolve().parents[1]
s = (paper / "main_v2.tex").read_text(encoding="utf-8")
bs = chr(92)
need = ["emuTrans", "emuTransS", "emuRuleMs", "emuLossWin", "emuLossAll"]
if not (paper / "generated" / "tab_emu.tex").exists():
    s = s.replace(bs + "input{generated/tab_emu}", bs + "mbox{}")
mac = (paper / "generated" / "results_macros.tex").read_text(encoding="utf-8")
stub = "".join(bs + "providecommand{" + bs + n + "}{0}" for n in need if n not in mac)
s = s.replace(bs + "input{generated/results_macros}", bs + "input{generated/results_macros}\n" + stub, 1)
(paper / "checkdraft.tex").write_text(s, encoding="utf-8")
r = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "checkdraft.tex"], cwd=paper,
                   capture_output=True, text=True)
log = (paper / "checkdraft.log").read_text(errors="ignore")
errs = [l for l in log.splitlines() if l.startswith("! ")]
print("errors:", len(errs))
for e in dict.fromkeys(errs):
    print(e)
for l in log.splitlines():
    if "Output written" in l or "Citation" in l and "undefined" in l:
        print(l)
print([l for l in log.splitlines() if "Overfull" in l][:6])

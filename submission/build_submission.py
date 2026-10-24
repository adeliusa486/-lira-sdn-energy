"""Build the JNCA submission package in submission/ from paper/main_jnca.tex.

manuscript.tex  : main text, Figures 1-6 and the core tables, author block, declarations
supplementary.tex: secondary tables, numbered S1, S2, ... and referenced from the manuscript
Run: python submission/build_submission.py   (then latexmk -pdf in submission/)
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUB = ROOT / "submission"
BS = "\\"
s = (ROOT / "paper" / "main_jnca.tex").read_text(encoding="utf-8")

SUPP = ["tab:models", "tab:ablation", "tab:K", "tab:theta", "tab:opt", "tab:scale",
        "tab:nowear", "tab:drift", "tab:folds", "tab:emu"]

# ---- authors
AUTHORS = (BS + "author[a]{Adeel Ahmad" + BS + "corref{cor1}}\n" + BS + "ead{443057803@stu.iu.edu.sa}\n"
           + BS + "author[a]{Toqeer Ali Syed}\n" + BS + "author[a,b]{Ali Akarma}\n"
           + BS + "cortext[cor1]{Corresponding author.}\n"
           + BS + "affiliation[a]{organization={AI Center, Faculty of Computer and Information Systems, Islamic University of Madinah},"
             " city={Madinah}, postcode={42351}, country={Saudi Arabia}}\n"
           + BS + "affiliation[b]{organization={AI V\\&V Lab, King Fahd University of Petroleum and Minerals},"
             " city={Dhahran}, country={Saudi Arabia}}\n")
a = s.index("% Author names and affiliations")
b = s.index(BS + "begin{abstract}")
s = s[:a] + AUTHORS + "\n" + s[b:]

# ---- abstract <= 250 words and at most 7 keywords (common Elsevier limits)
s = s.replace("as the strongest learned controller we could build", "as a strong learned controller", 1)
s = s.replace(BS + "sep metrical task systems", "", 1)

# ---- highlights inside the front matter, as in elsarticle-template-num.tex
hl = [l[2:].strip() for l in (ROOT / "paper" / "highlights_jnca.txt").read_text(encoding="utf-8").splitlines() if l.startswith("- ")]
s = s.replace(BS + "begin{keyword}", BS + "begin{highlights}\n" + "".join(BS + "item " + h.replace("%", BS + "%") + "\n" for h in hl)
              + BS + "end{highlights}\n\n" + BS + "begin{keyword}", 1)

# ---- declarations: CRediT, funding, competing interests. No AI-use statement (author decision).
a = s.index(BS + "section*{CRediT authorship contribution statement}")
b = s.index(BS + "bibliographystyle{elsarticle-num}")
DECL = (BS + "section*{CRediT authorship contribution statement}\n"
        + BS + "textbf{Adeel Ahmad:} Conceptualization, Methodology, Software, Investigation, Data curation, Visualization, Writing -- original draft. "
        + BS + "textbf{Toqeer Ali Syed:} Supervision, Validation, Writing -- review \\& editing. "
        + BS + "textbf{Ali Akarma:} Formal analysis, Validation, Writing -- review \\& editing.\n\n"
        + BS + "section*{Funding}\nThis research did not receive any specific grant from funding agencies in the public, commercial, or not-for-profit sectors.\n\n"
        + BS + "section*{Declaration of competing interest}\n"
        "The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.\n\n")
s = s[:a] + DECL + s[b:]

# ---- move secondary tables to the supplementary file
floats = list(re.finditer(r"\\begin\{(table\*?)\}.*?\\end\{\1\}", s, re.S))
moved, num = [], {}
for m in floats:
    lab = re.search(r"\\label\{([^}]+)\}", m.group(0))
    if lab and lab.group(1) in SUPP:
        moved.append((lab.group(1), m.group(0)))
order = {l: i for i, l in enumerate(SUPP)}
moved.sort(key=lambda x: order[x[0]])
for i, (lab, _) in enumerate(moved, 1):
    num[lab] = f"S{i}"
for lab, blk in moved:
    s = s.replace(blk + "\n", "").replace(blk, "")
for lab, n in num.items():
    s = s.replace("Table~" + BS + "ref{" + lab + "}", "Table~" + n + " (Supplementary Material)")
    s = s.replace(BS + "ref{" + lab + "}", n)
assert not re.search(r"\\ref\{(" + "|".join(map(re.escape, SUPP)) + r")\}", s)
(SUB / "manuscript.tex").write_text(s, encoding="utf-8", newline="\n")

# ---- supplementary material
pre = s[:s.index(BS + "begin{document}")]
title = re.search(r"\\title\{(.*?)\}\n", s, re.S).group(1)
body = "\n\n".join(blk.replace("[t]", "[h!]") for _, blk in moved)
supp = (pre + BS + "renewcommand{" + BS + "thetable}{S" + BS + "arabic{table}}\n" + BS + "begin{document}\n"
        + BS + "begin{center}{" + BS + "Large Supplementary Material}" + BS + "\\[6pt]\n" + title + BS + "\\[6pt]\n"
        "Adeel Ahmad, Toqeer Ali Syed, Ali Akarma" + BS + "end{center}\n\n"
        "These tables complement the results section of the article. All values are generated from the experiment files in "
        + BS + "url{https://github.com/adeliusa486/-lira-sdn-energy} (folder " + BS + "texttt{paper/results})."
        " Section numbers refer to the article.\n\n" + body + "\n\n" + BS + "end{document}\n")
supp = re.sub(r"\\journal\{[^}]*\}\n", "", supp)
(SUB / "supplementary.tex").write_text(supp, encoding="utf-8", newline="\n")

# ---- inputs
shutil.copytree(ROOT / "paper" / "generated", SUB / "generated", dirs_exist_ok=True)
shutil.copy(ROOT / "paper" / "references.bib", SUB / "references.bib")
shutil.copy(ROOT / "paper" / "highlights_jnca.txt", SUB / "highlights.txt")
print("moved to supplementary:", num)

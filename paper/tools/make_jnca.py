"""Build paper/main_jnca.tex (Elsevier elsarticle, Journal of Network and Computer Applications)
from paper/main.tex, so the IEEE and JNCA versions share one text and one set of generated numbers.

Usage: python paper/tools/make_jnca.py && cd paper && latexmk -pdf main_jnca.tex
"""
import re
from pathlib import Path

P = Path(__file__).resolve().parents[1]
REPO = "https://github.com/adeliusa486/-lira-sdn-energy"
BS = "\\"
s = (P / "main.tex").read_text(encoding="utf-8")


def sub(old, new, count=1):
    global s
    assert s.count(old) >= 1, old[:60]
    s = s.replace(old, new) if count == 0 else s.replace(old, new, count)


# ---- preamble
sub(BS + "documentclass[journal]{IEEEtran}", BS + "documentclass[preprint,12pt]{elsarticle}")
sub(BS + "usepackage{cite}\n", "")
sub(BS + "usepackage{amsmath,amssymb,amsfonts}", BS + "usepackage{amsmath,amssymb,amsfonts,amsthm}")
sub(BS + "usepackage[hidelinks]{hyperref}", BS + "usepackage[hidelinks]{hyperref}\n" + BS + "journal{Journal of Network and Computer Applications}")

# ---- front matter
a = s.index(BS + "title{")
b = s.index(BS + "end{IEEEkeywords}") + len(BS + "end{IEEEkeywords}")
front = s[a:b]
title = re.search(r"\\title\{(.*?)\}\n", front, re.S).group(1)
abstract = re.search(r"\\begin\{abstract\}\n(.*?)\n\\end\{abstract\}", front, re.S).group(1)
keys = re.search(r"\\begin\{IEEEkeywords\}\n(.*?)\n\\end\{IEEEkeywords\}", front, re.S).group(1)
keys = (BS + "sep ").join(k.strip().rstrip(".") for k in keys.split(",") if k.strip() and "negative results" not in k)
new_front = (BS + "begin{frontmatter}\n" + BS + "title{" + title + "}\n\n"
             "% Author names and affiliations: add before submission (single-blind review).\n"
             + BS + "author[a]{Author One\\corref{cor1}}\n" + BS + "ead{author.one@example.org}\n"
             + BS + "cortext[cor1]{Corresponding author.}\n" + BS + "affiliation[a]{organization={Affiliation}, country={Country}}\n\n"
             + BS + "begin{abstract}\n" + abstract + "\n" + BS + "end{abstract}\n\n"
             + BS + "begin{keyword}\n" + keys + "\n" + BS + "end{keyword}\n" + BS + "end{frontmatter}")
s = s[:a] + new_front + s[b:]
s = re.sub(r"\\IEEEPARstart\{(\w)\}\{(\w+)\}", lambda m: m.group(1) + m.group(2).lower(), s)
s = s.replace(BS + "begin{IEEEproof}", BS + "begin{proof}").replace(BS + "end{IEEEproof}", BS + "end{proof}")

# ---- references to the venue and the code
sub("The code, configuration libraries, per-experiment CSV files, and scripts that produce every table and figure of this article are provided with the submission.",
    "The code, configuration libraries, per-experiment CSV files, and scripts that produce every table and figure of this article are available at " + BS + "url{" + REPO + "}.")
sub(BS + "section*{Data Availability}", BS + "section*{Data availability}")
sub("We release the oracle, the baselines, and all scripts so that other traces and power models can be tested.",
    "We release the oracle, the baselines, and all scripts (" + BS + "url{" + REPO + "}) so that other traces and power models can be tested.")
decl = (BS + "section*{CRediT authorship contribution statement}\n"
        "% Fill in with the CRediT roles of each author before submission.\n\n"
        + BS + "section*{Declaration of competing interest}\n"
        "The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.\n\n"
        + BS + "section*{Declaration of generative AI and AI-assisted technologies in the writing process}\n"
        "During the preparation of this work the authors used an AI assistant (Claude, Anthropic) to help write code, run experiments, and edit the manuscript. After using this tool, the authors reviewed and edited the content as needed and take full responsibility for the content of the published article.\n\n")
sub(BS + "bibliographystyle{IEEEtran}", decl + BS + "bibliographystyle{elsarticle-num}")

# ---- wide tables: shrink to the single-column text width when needed
s = s.replace(BS + "usepackage{booktabs}", BS + "usepackage{booktabs}\n" + BS + "usepackage{adjustbox}\n" + BS + "emergencystretch=3em")
s = re.sub(r"\\input\{generated/(tab_[A-Za-z]+)\}", lambda m: BS + "begin{adjustbox}{max width=" + BS + "textwidth}" + BS + "input{generated/" + m.group(1) + "}" + BS + "end{adjustbox}", s)
s = s.replace(BS + "usepackage{url}", BS + "usepackage{xurl}")
s = s.replace("width=0.52" + BS + "columnwidth", "width=0.46" + BS + "columnwidth")
(P / "main_jnca.tex").write_text(s, encoding="utf-8", newline="\n")
print("wrote", P / "main_jnca.tex")

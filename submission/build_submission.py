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
# elsarticle prints highlights on an extra first page; JNCA takes them as a separate file
# (highlights.txt), so they stay out of the page-limited manuscript.

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

# ---- inputs
shutil.copytree(ROOT / "paper" / "generated", SUB / "generated", dirs_exist_ok=True)
shutil.copy(ROOT / "paper" / "references.bib", SUB / "references.bib")
shutil.copy(ROOT / "paper" / "highlights_jnca.txt", SUB / "highlights.txt")

# ---- page limit: journal layout, secondary material moves to the supplementary file
import subprocess

s = s.replace(BS + "documentclass[preprint,12pt]{elsarticle}", BS + "documentclass[5p,times]{elsarticle}")
s = s.replace("max width=" + BS + "textwidth", "max width=" + BS + "linewidth")

MOVE_SUBS = ["Drift Detection and Retraining", "Dependence on the Snapshot Classifier",
             "Ablation, Library Size, and Threshold", "Wear and Lifetime", "Decision Time and Scalability",
             "Without the Wear Price", "Traffic Drift", "Rolling-Origin Folds", "Emulation of Configuration Changes"]
MOVE_SECS = ["Algorithms"]
MOVE_FLOATS = ["tab:notation", "tab:params", "fig:case", "tab:models", "tab:ablation", "tab:K", "tab:theta",
               "fig:wear", "tab:opt", "tab:scale", "tab:nowear", "tab:drift", "tab:folds", "tab:emu",
               "alg:offline", "alg:online"]

MOVE_SUBS += ["Cost of Ignoring the Sequence", "Implementation and Parameters",
              "Noise Structure of the Semi-Synthetic Series", "Decisions on the Previous Interval's Traffic"]
MOVE_SECS += ["Limitations and Threats to Validity"]
MOVE_FLOATS += ["fig:pareto", "tab:noise", "tab:info", "fig:gain", "tab:data"]
s = s.replace(BS + "section{Limitations and Threats to Validity}" + BS + "label{sec:limitations}",
              BS + "section{Limitations and Threats to Validity}" + BS + "label{sec:limitations-full}")
ROBUST = BS + r"""subsection{Robustness to Noise Structure and Stale Traffic}\label{sec:res-robust}

Two further experiments, given in full in Sections~\ref{sec:res-noise} and~\ref{sec:res-stale} of the Supplementary Material, test the assumptions behind these results. First, we regenerate the Nobel-Germany series with time-correlated noise (AR(1), $\rho=0.5$ and $\rho=0.9$) and with half the noise scale, and retrain every method. With $\rho=0.5$ the snapshot classifier changes configuration \nzarABfourChg\ times per day and costs \nzarAExcess\% more than the oracle, with $\rho=0.9$ only \nzarBExcess\%, and with half the noise it does not flap. In every variant B6, B2, the static rule, and LiRA stay within \nzarBLiRAgap\% of the oracle, and LiRA costs the same as the static rule. Second, when every online method decides with the previous interval's traffic $D_{t-1}$, costs move by at most \staleNobMaxDJ\%, but the safety layer no longer guarantees $\theta$: up to \staleBzerohl\% of the Nobel-Germany intervals violate it, at single-interval traffic peaks that a margin of 0.05 does not remove. LiRA's exact match with the oracle under high load therefore depends on knowing the traffic of the interval it configures.

"""
LIMITS = BS + r"""section{Limitations}\label{sec:limitations}

The flapping series is semi-synthetic, the two real traces are old research backbones, and the Nobel-Germany test split covers \nobTestDays\ days, so per-day tests have little power and no comparison survives a correction over all settings. Port power and wear parameters are assumed, B4 reimplements the snapshot principle rather than a published system, and no deep reinforcement learning baseline was trained. The main results let each method see the traffic it configures, and the drift study did not validate the detectors. The learned component matters in one scenario only: the trained policy is constant in \liraConstRuns\ of \liraTotalRuns\ runs, and the static rule equals LiRA in \staticSame\ of \staticTotal\ settings. Section~\ref{sec:limitations-full} of the Supplementary Material lists all threats to validity.

"""

# 0. Related Work: a condensed version in the article, the full review in the supplementary file
ra = s.index(BS + "section{Related Work}")
rb = s.index(BS + "section{Problem Formulation}")
related_full = s[ra:rb].replace(BS + "label{sec:related}", BS + "label{sec:related-full}")
related_full = re.sub(r"\\subsection\{", lambda m: BS + "subsection*{", related_full)
RELATED_SHORT = BS + r"""section{Related Work}\label{sec:related}

Energy-aware networking puts idle links and devices to sleep~\cite{bianzino2012survey,bolla2011energy}. Integer programs and heuristics choose the links to sleep under capacity and connectivity constraints~\cite{chiaraviglio2012minimizing,zhang2010greente,heller2010elastictree}, and a recent study of operational ISP networks shows that the opportunity persists outside research backbones~\cite{rollin2024sleep}. Learned controllers replace the optimizer: reinforcement learning has been used to put data-center links to sleep~\cite{wang2022dcndrl} and to trade delay against energy in SDN~\cite{frohlich2021rl}, and the works closest to ours map each traffic matrix to a precomputed configuration and report large speedups~\cite{gomezdelahiz2025noms,gomezdelahiz2026tgcn}. We reimplement this snapshot principle as baseline B4 because we did not have access to the original code. Learned traffic engineering~\cite{xu2023teal,perry2023dote,almasan2022enero} also decides without pricing the change between configurations. FlexDATE~\cite{ye2023flexdate} limits the disturbance of rerouting but does not put links to sleep.

Changing forwarding state is neither free nor instantaneous~\cite{reitblatt2012abstractions,jin2014dionysus}, and power-state transitions affect device lifetime~\cite{chiaraviglio2015lifetime}. Online decisions with switching costs form metrical task systems~\cite{borodin1992mts}. Learning-augmented algorithms for them show that following a predictor blindly can be costly and that holding the current state is a robust fallback~\cite{antoniadis2023mts,christianson2023dart}. Our setting is a metrical task system with a finite state space whose offline optimum is computable, which makes imitation learning with DAgger~\cite{ross2011dagger} natural, and our hysteresis and static baselines are simple state-holding rules. Section~\ref{sec:related-full} of the Supplementary Material gives a full review.

"""
s = s[:ra] + RELATED_SHORT + s[rb:]

# 1. take the floats out
flt = {}
for m in list(re.finditer(r"\\begin\{(table\*?|figure\*?|algorithm)\}.*?\\end\{\1\}\n?", s, re.S)):
    lab = re.search(r"\\label\{([^}]+)\}", m.group(0))
    if lab and lab.group(1) in MOVE_FLOATS:
        flt[lab.group(1)] = m.group(0)
for blk in flt.values():
    s = s.replace(blk, "")

# 2. take the text blocks out (a subsection runs to the next (sub)section)
def cut(head):
    global s
    a = s.index(head)
    nxt = [j for j in (s.find("\n" + BS + "subsection{", a + 1), s.find("\n" + BS + "section", a + 1)) if j > 0]
    if head.startswith(BS + "section"):
        nxt = [s.find("\n" + BS + "section", a + 1)]
    b = min(nxt)
    blk = s[a:b + 1]
    s = s[:a] + s[b + 1:]
    return blk
blocks = [related_full] + [cut(BS + "section{" + t + "}") for t in MOVE_SECS] + [cut(BS + "subsection{" + t + "}") for t in MOVE_SUBS]
s = s.replace(BS + "section{Discussion}", ROBUST + BS + "section{Discussion}", 1)
s = s.replace(BS + "section{Conclusion}", LIMITS + BS + "section{Conclusion}", 1)

# 3. supplementary: each block as a section, followed by the floats it references
supp_body, used = [], set()
for blk in blocks:
    blk = re.sub(r"^\\(sub)?section\{", lambda m: BS + "section{", blk)
    supp_body.append(blk)
    for lab in re.findall(r"\\ref\{([^}]+)\}", blk):
        if lab in flt and lab not in used:
            used.add(lab); supp_body.append(flt[lab])
rest = [l for l in MOVE_FLOATS if l not in used]
if rest:
    supp_body.append(BS + "section{Notation, Parameters, and Additional Figures}\n" + "\n".join(flt[l] for l in rest))

pre = s[:s.index(BS + "begin{document}")].replace(BS + "documentclass[5p,times]{elsarticle}", BS + "documentclass[preprint,12pt]{elsarticle}")
pre = re.sub(r"\\journal\{[^}]*\}\n", "", pre)
title = re.search(r"\\title\{(.*?)\}\n", s, re.S).group(1)
counters = "".join(BS + "renewcommand{" + BS + "the" + c + "}{S" + BS + "arabic{" + c + "}}\n" for c in ("section", "table", "figure", "algorithm"))
supp = (pre + counters + BS + "begin{document}\n" + BS + "begin{center}{" + BS + "Large Supplementary Material}" + BS + "\\[6pt]\n"
        + title + BS + "\\[6pt]\nAdeel Ahmad, Toqeer Ali Syed, Ali Akarma" + BS + "end{center}\n\n"
        "This file holds the algorithms, the secondary experiments, and the tables and figures that complement the article. "
        "Equation, section, and table numbers without the prefix S refer to the article. All values are generated from the experiment files in "
        + BS + "url{https://github.com/adeliusa486/-lira-sdn-energy}.\n\n"
        + "\n\n".join(x.replace("[t]", "[h!]") for x in supp_body)
        + "\n" + BS + "bibliographystyle{elsarticle-num}\n" + BS + "bibliography{references}\n" + BS + "end{document}\n")

# 4. compile both once, then turn cross-document references into literal numbers
def write():
    (SUB / "manuscript.tex").write_text(s, encoding="utf-8", newline="\n")
    (SUB / "supplementary.tex").write_text(supp, encoding="utf-8", newline="\n")
def build():
    for f in ("manuscript.tex", "supplementary.tex"):
        subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", f], cwd=SUB, capture_output=True)
def labels(aux):
    t = (SUB / aux).read_text(encoding="utf-8", errors="ignore")
    return dict(re.findall(r"\\newlabel\{([^}]+)\}\{\{([^}]*)\}", t))
write(); build()
lm, ls = labels("manuscript.aux"), labels("supplementary.aux")
def resolve(text, own, other):
    def rep(m):
        cmd, lab = m.group(1), m.group(2)
        if lab in own or lab not in other:
            return m.group(0)
        return ("(" + other[lab] + ")") if cmd == "eqref" else other[lab]
    return re.sub(r"\\(ref|eqref)\{([^}]+)\}", rep, text)
s, supp = resolve(s, lm, ls), resolve(supp, ls, lm)
write(); build()
print("moved:", [b.split("}")[0] for b in blocks], "floats:", list(flt))

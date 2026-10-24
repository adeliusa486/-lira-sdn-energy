# JNCA submission package

Upload to Elsevier Editorial Manager (Journal of Network and Computer Applications, research article, subscription route).

| File | Upload as |
|---|---|
| `manuscript.pdf` + `manuscript.tex`, `references.bib`, `generated/` | Manuscript (LaTeX source and PDF) |
| `supplementary.pdf` | Supplementary material (Sections, Tables and Figures S1 to S16) |
| `highlights.txt` | Highlights (5 bullets, each at most 85 characters) |
| `cover_letter.pdf` | Cover letter |

Rebuild: `python submission/build_submission.py`, then `latexmk -pdf manuscript.tex supplementary.tex cover_letter.tex` in this folder.

Length: the manuscript is typeset in Elsevier's journal layout (elsarticle 5p) and is 10 pages including references (39 references). Related work in full, algorithms, secondary experiments, robustness details, the full limitations, and 16 tables and figures are in `supplementary.pdf` (24 pages); the article cites them as Section, Table, and Fig. S1 to S16. Abstract 248 words, 7 keywords. Highlights are a separate file because elsarticle prints them on an extra page.

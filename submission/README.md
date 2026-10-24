# JNCA submission package

Upload to Elsevier Editorial Manager (Journal of Network and Computer Applications, research article, subscription route).

| File | Upload as |
|---|---|
| `manuscript.pdf` + `manuscript.tex`, `references.bib`, `generated/` | Manuscript (LaTeX source and PDF) |
| `supplementary.pdf` | Supplementary material (Tables S1 to S10) |
| `highlights.txt` | Highlights (5 bullets, each at most 85 characters) |
| `cover_letter.pdf` | Cover letter |

Rebuild: `python submission/build_submission.py`, then `latexmk -pdf manuscript.tex supplementary.tex cover_letter.tex` in this folder.

Length: 39 pages in the 12 pt review format. In Elsevier's final two-column layout (5p) the article prints at 16 pages including references. Abstract 248 words, 7 keywords.

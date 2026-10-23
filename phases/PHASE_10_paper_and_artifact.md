# Phase 10 — Paper Writing (IEEE LaTeX) + Artifact

**Goal:** A submission-ready IEEE **journal** paper (target IEEE TGCN; `\documentclass[journal]{IEEEtran}`, about 13–14 pages) and a public artifact. The draft already exists in `paper/main.tex`. This phase replaces its placeholders with measured results. The section plan below was written for the earlier conference version. The journal version adds a Background/Motivation section, a notation table, Propositions 1–4, a Discussion section, and the extra experiments E9, E10, E13 and E14, plus TM-noise robustness.
**Module:** `paper/{main.tex, references.bib, figures/*.tex, tables/*.tex, data/*}`

## Steps
1. Use `paper/PAPER_GENERATION_PROMPT.md` (the user's IEEE prompt, adapted) with: the title, the abstract with the filled-in numbers from `results/headline.json`, `references_verified.bib`, and `results/summary/*.csv`.
2. **Section plan (8 pages + refs):** I Intro (gap + contributions) · II Related Work (taxonomy table vs. gap matrix) · III Problem Formulation (E, R, W, sequential objective) · IV LiRA Framework & Architecture (TikZ figure) · V Algorithms (DP oracle, DAgger training, safety, drift: Algorithms 1–2) · VI Experimental Setup (datasets table, hardware, hyperparameters table) · VII Results (E1 table, Pareto, time series, transitions CDF, latency, ablation, drift, emulation) · VIII Comparative Analysis / Discussion · IX Limitations · X Conclusion.
3. **Figures (TikZ/PGFPlots, data read from `paper/data/`):** architecture; control-loop workflow; training/testing pipeline; Pareto front; one-week time series; transition CDF; latency vs size; drift timeline; ablation bars.
4. **Formatting rules from the prompt:** one paragraph per source line, every float has `\caption`+`\label` and is `\ref`-ed, `\%` escaped, `IEEEtran` conference class.
5. **Checks:**
   - `latexmk -pdf` with 0 errors and 0 undefined references; check overfull boxes.
   - Script `tools/check_numbers.py` (to be written): every number in `main.tex` results sections must appear in `results/`.
   - Every `\cite` key is in `references_verified.bib`.
   - Run the peer-review skill, then forensic-manuscript-audit, then humanize-latex.
6. **Artifact:** a public repo with README, `environment.yml`, a Dockerfile, a `make reproduce-E1` target, data download scripts (no redistribution of restricted data), and a Zenodo DOI.

## Exit gate
PDF ≤ page limit, all checks pass, the anonymised version is ready for double-blind review (no self-identifying artifact links; use an anonymous repository link).

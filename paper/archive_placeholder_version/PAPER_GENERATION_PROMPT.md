# IEEE Paper Generation Prompt (adapted for an A* submission)

Use in Phase 10. Your original prompt is kept below with **three changes**, all needed so the paper holds up at an A* venue:

1. **Results come from `results/`, not invented.** The original asked for "believable" generated numbers. For a real submission every number must be measured. Give the model `results/headline.json`, `results/summary/*.csv` and the `paper/data/*.dat` files, and tell it: *"Use only these numbers. If a metric is not in these files, leave it out."*
2. **References come only from `references_verified.bib`.** The model may not add BibTeX entries. Any new citation goes through `tools/verify_refs.py` first.
3. **Plots read data files.** PGFPlots figures use `\addplot table {data/xxx.dat}`, so the plots match the experiments.

Inputs to attach: title, abstract (with X/Y/Z/T filled from `headline.json`), `references_verified.bib`, `results/summary/*.csv`, `paper/data/*.dat`, `IMPLEMENTATION_PLAN.md` §2 (notation).

---

## Original prompt (with changes marked ▶)

You are an expert academic researcher, IEEE conference author, and LaTeX engineer. Generate a COMPLETE camera-ready IEEE conference paper from the provided title, abstract ▶ **and the attached measured results, notation and verified bibliography**. Output a FULL LATEX PROJECT: `main.tex`, `references.bib` (▶ copy of `references_verified.bib`, cited subset only), TikZ figures embedded, tables, equations, algorithms. Approx. 6–8 IEEE pages (▶ check the target venue's limit).

**Paragraph formatting:** each paragraph is ONE continuous source line; new paragraph = blank line; no hard wrapping.

**LaTeX:** `\documentclass[conference]{IEEEtran}`; compile-ready; no duplicate packages; every figure/table/equation has `\caption`/`\label` (equations: `\label`) and is referenced with `\ref`; escape `%` as `\%`; unique labels and keys; avoid overfull boxes.

**Structure:** Title, Authors (▶ anonymised for double-blind), Abstract, Index Terms; I Introduction (gap + contribution list); II Related Work; III Problem Formulation; IV Proposed Framework and System Architecture; V Algorithms; VI Experimental Setup; VII Results and Discussion; VIII Comparative Analysis; IX Limitations; X Conclusion and Future Work; References.

**Figures (TikZ/PGFPlots, soft colours, rounded boxes, readable at column width):** architecture; control loop / data flow; training & testing pipeline; Pareto front (energy vs. transitions); one-week time series; transition CDF; latency vs. topology size; ablation bars; drift timeline. ▶ No accuracy/confusion-matrix figures unless they add insight; cost metrics are the main story.

**Results:** ▶ measured only (see change 1): energy savings, retention X, config-change reduction Y, transition reduction Z, MLU violations, decision latency T (median/p99), lifetime AF, emulation loss/latency, ablation, drift recovery, mean ± 95% CI and significance tests. No "TBD".

**Tables:** dataset table, hyperparameter table, main comparison, ablation, emulation, regret vs. oracle. Fit in one column, or use `table*`.

**Maths:** power model, R(c,c'), W(c,c'), the sequential objective, the DP recursion, the cost-sensitive imitation loss, drift test statistics. Notation must match `IMPLEMENTATION_PLAN.md` §2.

**Algorithms:** `algorithm` + `algorithmic`: (1) DP oracle + DAgger training; (2) online LiRA control loop with safety layer and drift-triggered retraining.

**References:** 35–50, IEEE style, all with DOI or URL, ▶ only from `references_verified.bib`.

**Writing:** concise, human, no marketing words, no exaggerated claims, consistent terms (use "configuration", "power-state transition", "reconfiguration" the same way everywhere).

**Final checks:** compiles; no undefined references; no placeholders; every number appears in `results/` (▶ `tools/check_numbers.py`); bibliography complete.

**Title:** Stop Flipping the Switch: Lifetime- and Reconfiguration-Aware Learning for Energy-Efficient Software-Defined Networks
**Abstract:** see `README`/original; fill [X], [Y], [Z], [T] from `results/headline.json`.

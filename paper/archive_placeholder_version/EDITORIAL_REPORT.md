# Editorial Report

## Update — journal version v2 (2026-10-18)
- **Title:** *Lifetime- and Reconfiguration-Aware Sequential Learning for Energy-Efficient Software-Defined Networks*.
- **Format:** `\documentclass[journal]{IEEEtran}` for IEEE TGCN. 13 pages. 0 errors, 0 overfull boxes, all labels referenced, no paragraph split across lines. The abstract is 245 words, within IEEE's 250-word limit.
- **Added:**
  - Background and Motivation section with a new figure;
  - notation table (Table II);
  - Proposition 1: snapshot regret grows linearly with the horizon;
  - Proposition 3: DAgger performance bound with an explicit bound on u;
  - complexity subsection and Discussion section (4 subsections);
  - dwell-time CDF;
  - three-panel sensitivity figure (θ, χ, TM noise);
  - statistics, library-size, model-family and rolling-fold tables.
- **References:** 59 cited, all verified. The 9 new ones are GreenTE, ENERO, MAGNNETO, Bengio et al. (EJOR), DeepBSC (ToN), Vishwanath et al. (JSAC), Zheng et al. (Electronics), INSOMNIA and NeuTM. Their metadata came from doi.org. They are cited only for what their title or abstract states.
- **New placeholders** (all from `tools/make_placeholder_data.py`):
  - motivation shares (59%, 38%, 61%);
  - dwell CDF;
  - θ, χ and noise sweeps (the χ curves are computed exactly from the wear model);
  - Table VII (statistics), Table VIII (K), Table X (models), Table XII (folds).
- **Author block:** IEEE template placeholders. Fill in real names, affiliations and the funding acknowledgment. IEEE Transactions papers also need author biographies at the final stage, not at submission.
- **To check:** the TGCN page limit and overlength charges in the current author guidelines.
- The conference version is kept as `main_conference_v1.tex` and `.pdf`.

---

# Editorial Report — conference draft v1 (2026-10-18)

**Classification:** Case A (incomplete). The method, formulation, figures and structure are complete. No experiments have run yet, so every result is a realistic placeholder, and the PDF prints a red *Draft notice* while `\placeholderstrue` is set (`main.tex`, preamble).

**Build:** `latexmk -pdf main.tex` gives 0 errors, 0 undefined references, 0 overfull boxes and 0 BibTeX warnings. The PDF is 10 pages (about 8.6 pages of text and 1.4 pages of references). `tools/check_paragraphs.py` finds no paragraphs split across lines, no unreferenced labels and no references to missing labels.

## 1. Key improvements made in the review pass
- **Accuracy fixes:**
  - The abstract claimed real traces for all three topologies. It now says Nobel-Germany is semi-synthetic.
  - The Pareto-gap statement was corrected to 0.6–2.2 pp, after checking it against the plotted data.
  - An unverified claim about SNDlib's Nobel-Germany data was rewritten so it no longer asserts a fact about SNDlib.
- **Notation:** two symbol clashes were removed. Reconfiguration weights α,β,γ became η₁,η₂,η₃, so they no longer clash with α^off. The softmax temperature κ became β, so it no longer clashes with capacity κₑ. Δ_h became Δ_hr, so it no longer clashes with the history length h.
- **Rigor:** the proof of Proposition 1 now states the edge weights and the infeasible-node handling explicitly. The cost-to-go and Q-function are split into two numbered lines. Propositions 1 and 2 are cited where they are used.
- **Content added:**
  - why link toggles are priced separately from flow-mods;
  - the β→0 limit of the soft-target loss;
  - a deployment-considerations paragraph (inputs needed, how operators set λ_R and λ_W, how the system fails safely);
  - a reproducibility statement.
- **Figures:**
  - Fig. 1 band labels no longer overlap the boxes.
  - Legends were moved above the plots in Figs. 5–8.
  - Fig. 7 now has readable x-ticks and no overfull box.
- **Bibliography:** reduced to the 50 cited entries (dropped `mnih2015dqn`). Every entry has a DOI or URL, and all were verified against Crossref, arXiv or a live URL by `tools/verify_refs.py`.
- **Preamble:** removed unused packages (`textcomp`, `multirow`) and TikZ libraries, plus `\IEEEoverridecommandlockouts`.

## 2. Assumptions and placeholders introduced
| Item | Where | Source of placeholder |
|---|---|---|
| All results: S, Ch., Tr., latency, J, regret, MLU violations, AF | Abstract, Sec. I (61.4, 214.6), Tables IV–VIII, Figs. 4–8 | `tools/make_placeholder_data.py` (derived values computed, not hand-typed) |
| CI₉₅ = [93.9, 95.4], Wilcoxon p-values, Cliff's δ 0.71–0.94 | Sec. VII-A, VII-C | placeholder |
| Training time 3.1 h, labeling 41 s, MIP gap 4.7% | Sec. VII-D | placeholder |
| Model-family and K-sensitivity numbers | Sec. VII-E | placeholder |
| Hardware (2× Xeon Gold 6338, A100, 256 GB) | Sec. VI-D | placeholder; replace with your real machine |
| Port power 30/5/3 W; α^off = 0.5; χ = 0.6 h; prices 0.2%/0.08% | Table III | modeling assumptions; justify or replace with measured or cited values |
| Topology Zoo sizes (GtsCe 149/193, Cogent 197/245) | Table II | from memory; check against the GraphML files |
| Nobel-Germany 60-day semi-synthetic series | Sec. VI-A | design decision from the plan (Phase 2) |

## 3. Missing elements (blocking submission)
1. **Measured results.** Run Phases 2–9 and then regenerate `data/*.dat`, `results_macros.tex` and the tables from `results/`. Every number in Section 2 above must change to a measured value. Only then set `\placeholdersfalse`.
2. **Competitor full texts.** Gómez-delaHiz et al. (NOMS 2025, TGCN 2026) have not been read in full. Table I marks them "--" for reconfiguration, wear, sequential and drift. If they handle any of these, Table I, the Introduction and the contribution list must be narrowed.
3. **Recent literature:** only about 7 cited papers are from 2021–2026. A* reviewers will expect more recent DRL and GNN green-routing work (see `LITERATURE_REVIEW.md` §J).
4. **Venue page limit.** The paper is 10 pages including references. If the limit is 8 + references, the likely cuts are Fig. 3 (pipeline), Table I (move to text), and shorter Sections VIII and IX.

## 4. Action items for the authors
- [ ] Replace placeholders with measured values (Phase 9 scripts write `paper/data/` and `results_macros.tex`).
- [ ] Read the two competitor papers and update Table I and Section I.
- [ ] Check dataset facts (link counts, spans, TM counts) against the downloaded files (Phase 2).
- [ ] Justify the power and wear parameters by citation or measurement, or keep them clearly labeled as assumptions with the sensitivity study (E9).
- [ ] Add 8–10 verified 2021–2026 references through `tools/verify_refs.py`, then run `tools/clean_bib.py`.
- [ ] Before submission: run `tools/check_paragraphs.py`, then the humanize-latex pass, then a peer-review simulation.

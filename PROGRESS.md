# Project Progress Log (memory file)

Update this file at the end of every work session: what was done, decisions made, numbers measured, open issues. Newest entries at the top.

## Status board

| Phase | Status | Exit gate met | Notes |
|---|---|---|---|
| 1 Literature & refs | ✅ done | ☑ | 60 verified, 15 from 2021–2026 (count gate met). Decision 2026-10-18: no IEEE Xplore access, so competitor numbers are dropped. B4 is our own reimplementation and the paper does not quote their figures |
| 2 Data | ✅ done | ☑ | Abilene 12/15, 48,108 TMs; GÉANT 22/36, 10,784 TMs; Nobel 17/26, 30-day semi-synthetic (SNDlib has 1 day). Tests pass |
| 3 Models | ✅ code+tests | ☐ | Power constants still status VERIFY in `configs/power.yaml` |
| 4 Config library | ✅ all 3 | ☐ | Coverage 100%. Abilene has only 60 connected link states (K capped at 61) |
| 5 Oracle & baselines | ✅ code+tests | ☑ | DP = MILP to 1e-14 on real data. B0,B1,B2,B3,B5,B6,B7 implemented; full runs = Phase 9 |
| 6 Snapshot ML | ✅ | ☑ | B4 = XGBoost + safety layer |
| 7 LiRA policy | ✅ | ☐ | Equals oracle; no gain over hysteresis on real traces. Static rule = LiRA in 11 of 12 settings (E17) |
| 8 Drift | ✅ | ☐ | Results in E8 |
| 9 Emulation & experiments | ✅ (PPO not possible: torch broken) | ☐ | E1-E17 finished; `paper/results/FINDINGS.md` sections 6-7 |
| 10 Paper & artifact | ✅ draft v3 after forensic audits | ☐ | `paper/main.tex` compiles, no placeholders, anonymous authors. `REPRODUCE.md`, `reproduce.ps1`, pinned `requirements.txt` |

## Headline numbers (fill from `results/headline.json` only)
- X (energy-savings retention): —
- Y (config-change reduction): —
- Z (link-transition reduction): —
- T (median decision latency): —

## Decisions log
- 2026-10-18: The method is named **LiRA** (Lifetime- and Reconfiguration-Aware learner). Imitation of an exact DP (Viterbi) oracle over a configuration library, with DAgger, cost-sensitive loss, a feasibility safety layer, and ADWIN/Page-Hinkley drift triggers.
- 2026-10-18: Results must be measured. The paper prompt was changed so it reads `results/` and `references_verified.bib` only.
- 2026-10-18: Direct competitors are Gómez-delaHiz et al., NOMS 2025 (10.1109/NOMS57970.2025.11073657) and IEEE TGCN 2026 (10.1109/TGCN.2026.3724271). Their method defines baseline B4.

## Session log
### 2026-10-23 — Session 4 (forensic audits, E15-E17, paper v3)
- Ran both forensic skills. Reports: `reports/repo_forensic_audit_2026-10-23.md` (fraud risk LOW, score 7/10) and `reports/forensic_writing_audit_2026-10-23.md` (68 issues, 4 Critical). Both end with a remediation section.
- Main audit findings: (1) every online method decides interval t with the realized D_t, so the safety layer has oracle information. (2) Nobel base LiRA is a constant policy (config 1 in 2,159 of 2,160 test intervals). (3) Nobel high load: LiRA's sequence equals the oracle's in every interval and seed, because the safety layer switches exactly when the default is infeasible. (4) DAgger round 0 is the selected policy in 56 of 60 runs. (5) B2 beats LiRA in 3 of 4 Nobel scenarios and was not discussed. (6) Three typed claims were false ("only setting", "within 0.2% of one", "did not change which configuration").
- New experiments: E15 per-interval exact MILP lower bound (`experiments/run_milp.py --mode bound`), E16 decisions on D_{t-1} (`run_stale.py`, 3 seeds), E17 static configuration + LiRA fallback (`run_static.py`). The first E15 design (24-interval multi-period MILP windows) hit the 180 s limit with 2-22% gaps and used a non-valid flow-mod surrogate, so it was replaced before any result was used.
- E15: 21,203 single-interval MILPs, all optimal. The library loses at most 0.045% against the bound, and the oracle is within 0.55% of it (Nobel stress), 0.000% on Abilene, 0.011% on GÉANT.
- E16: costs move by at most 0.002%. Nobel violations 0.05/0.19/0.19% (B2, B4, B6, base/high load/stress), the same as always-on. A 0.05 margin does not remove them. E17: static = LiRA in 11 of 12 settings. Only Nobel stress differs (static 902.0, LiRA 898.6, B2 895.4, O* 894.3).
- Paper now 14 pages (was 13): check the TGCN page limit. Run logs of E15-E17 are in `results/runlogs/`.
- Paper v3: abstract 249 words, every typed number now a macro, B2 and the static rule in every Nobel comparison, mechanisms stated, new subsections "Information Available to the Controller", "What the Library Gives Up", "Decisions on the Previous Interval's Traffic". Fixed the `\\,s` line break in the abstract, Algorithm 1 label, B4 fallback, O* scope, wrong cross-reference, overfull Table XI.
- Repo: README rewritten, `REPRODUCE.md` and `reproduce.ps1` added, `requirements.txt` pinned (unused torch, optuna, pulp, sb3, gurobipy removed), one-off scripts and the duplicate `main_v2.tex` moved to `paper/tools/archive_oneoff/`, `evaluate()` docstring documents that J has no violation penalty.
- **Still open:** author names and affiliations (anonymous), a second noisy real trace (none available offline), DRL baseline (torch broken in this environment), hardware testbed, reference [38] metadata (preprint cited, COLT 2018 version not verified).

### 2026-10-19 — Session 3 (emulation, paper rewrite, no placeholders)
- Mininet 2.3.0 + OVS 3.7.1 found in WSL2 Ubuntu and used for E11 (`experiments/emulate_mininet.py`, `run_emulation.sh`, `emu_analyze.py`). Results in `paper/results/E11_emulation/`.
- Rewrote the paper (`paper/main.tex`, 13 pp, IEEE TGCN `[journal]{IEEEtran}`) around the measured findings: new title, honest abstract and claims. All numbers, tables and plot data are generated from `paper/results/` by `paper/tools/make_paper_assets.py` into `paper/generated/`. Placeholder version archived in `paper/archive_placeholder_version/`.
- Ran the peer-review skill: `paper/results/PEER_REVIEW_main_v2.md`; fixed its Critical/High items (constant-policy disclosure 30/60 runs, multiplicity caveat, B4 classifier dependence, wording).
- **To do before submission:** author names/affiliations (anonymous for now), a second noisy real trace, full multi-period MILP baseline, optional PPO, hardware testbed. Real traces show no benefit of LiRA over a snapshot rule; this is stated in the paper.
- Rebuild the paper: `python paper/tools/make_paper_assets.py` then `cd paper; latexmk -pdf main.tex`.

### 2026-10-19 — Session 2b (experiments run, results saved)
- Built Phase 6 (B4 classifier), Phase 7 (LiRA: DAgger, cost-sensitive loss, safety layer), Phase 8 (ADWIN + Page-Hinkley retraining, library refresh) in `lira/policy`, `experiments/`.
- Ran experiments E1–E10, E12–E14 (see `paper/results/README_RESUME.md` for what is done, pending, and not runnable). Report: `paper/results/RESULTS.md`, regenerate with `python experiments/make_report.py`.
- Default prices follow the paper: change = 0.2% and transition = 0.08% of daily always-on energy.
- **Main finding:** on real Abilene/GEANT traffic LiRA ties all baselines (the oracle is a constant config). Only Nobel (semi-synthetic) shows differences. The paper's claim and all placeholder numbers must be revised next session.
- All pending runs finished later the same day; findings in `paper/results/FINDINGS.md`. **Next:** decide the claim, decide the paper's claim, regenerate `paper/data/*.dat` and tables from CSVs, set `\placeholdersfalse` only after that.

### 2026-10-18 — Session 2 (Phases 2–5 + pilot)
- Paper: added the missing IEEE Transactions template parts (`\IEEEpeerreviewmaketitle`, Data Availability, Acknowledgment, author biographies). Removed the invented hardware line, which is now a red TODO. Solver is HiGHS. Nobel is 30 days. P^dyn=5 W, P^sl=3 W and α^off=0.5 are now the same in paper and `configs/power.yaml`.
- Code: package `lira/` (data, models, library, oracle, baselines), 18 passing tests, `scripts/pilot_experiment.py`.
- Data: SNDlib downloads with hashes in `data/MANIFEST.json`. GÉANT had 687 all-zero intervals and 11 volume spikes (>10× daily median), which were removed. Scaling uses the **99.9th percentile** of training MLU (= 0.5), because one anomalous hour in GÉANT made scaling to the raw max meaningless.
- **Pilot result (test split, K=32, λR=λW=1, no ML):** Abilene: the perfect snapshot rule changes config only 0.19×/day, so there is almost no flapping. Nobel: the snapshot rule makes 64 changes/day, but plain hysteresis (δ=0.005) removes 99.8% of them at 0.02% regret to the oracle. **Risk to the paper:** with idle-dominated power, the "just add hysteresis" objection holds for exact snapshot decisions. Possible reasons LiRA could still matter: (a) a *learned* B4 makes noisy predictions, (b) higher load or load-proportional power, (c) larger topologies (GÉANT). Check these in the next session before writing any claim.
- GÉANT done: coverage 99.99%, 53 candidates, DP = MILP. Pilot on GÉANT: the snapshot rule makes **0 changes** in 28 test days (one config is optimal all month, 29.9% savings). Same risk as Abilene.

### 2026-10-18 — Session 1c (journal conversion)
- The user asked for a more academic title and a journal paper. New title: *Lifetime- and Reconfiguration-Aware Sequential Learning for Energy-Efficient Software-Defined Networks*.
- Converted `paper/main.tex` to IEEE journal format for TGCN (13 pp). The conference version is saved as `paper/main_conference_v1.*`.
- Added 9 verified recent references (60/60 candidates pass). New tools: `tools/search_literature.py` (Crossref search with abstracts) and `tools/doi2bib.py` (official BibTeX from a DOI).
- The title change does not require rerunning any phase. Phases 2–9 are still needed because all results are placeholders.

### 2026-10-18 — Session 1b (paper draft)
- Wrote the full IEEE draft `paper/main.tex`: 8 TikZ/PGFPlots figures, 8 tables, 15 equations, 2 algorithms, 2 propositions. Bibliography = 50 verified, cited entries.
- Placeholder results come from `paper/tools/make_placeholder_data.py` (one script, internally consistent). The PDF shows a red draft notice while `\placeholderstrue`.
- Ran the user's Q1 polishing prompt as the review pass. Report: `paper/EDITORIAL_REPORT.md`.
- Paper helper tools: `tools/clean_bib.py` (cited-only bib) and `tools/check_paragraphs.py` (one line per paragraph, label/ref check).

### 2026-10-18 — Session 1
- Created the plan, the 10 phase modules, the datasets/experiments spec and the literature review.
- Wrote `tools/verify_refs.py`. Fixed 2 wrong DOIs (Chiaraviglio 2015, Vasić 2010). Added the competitor papers and 2021–2023 learned-TE papers.
- **Next:** read the two competitor papers in full and fill the "?" cells in the gap matrix. Then start Phase 2 (download SNDlib + Abilene + GÉANT).

## Open issues
- [ ] Check whether the competitors already model reconfiguration or wear (no IEEE Xplore access; the paper only reimplements the snapshot principle as B4).
- [x] Length of the Nobel-Germany dynamic TM series in SNDlib: one day (2026-10-18). 30-day semi-synthetic series used.
- [x] Target venue: IEEE TGCN journal (2026-10-18).
- [x] Solver: HiGHS only, no Gurobi.
- [ ] Author names, affiliations and biographies (needs the user).
- [ ] Second real trace with noisy demands (none available offline).
- [ ] Verify reference [38] (Chen, Goel, Wierman): preprint cited, the COLT 2018 version needs `tools/verify_refs.py` with network access.

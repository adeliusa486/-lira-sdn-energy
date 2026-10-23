# Forensic Writing Audit: paper/main.tex

Manuscript: *Sequence-Aware Learning for Energy-Efficient Software-Defined Networks: An Exact Oracle and an Empirical Study of When History Matters* (IEEE TGCN draft, 13 pages, anonymous).
Audit date: 2026-10-23. Source: `paper/main.tex` (657 lines, one paragraph per source line), its inputs `paper/generated/results_macros.tex` and 13 `paper/generated/tab_*.tex` tables, the compiled `paper/main.pdf` (extracted with `pdftotext -layout`), and the rendered reference list.
Earlier version used for comparison: `paper/archive_placeholder_version/main_v1_placeholders.tex` (the placeholder-results draft of 2026-10-18). The project is not under git, so no other version exists.
Every number the prose relies on was checked against `paper/results/` with a script (`verify_claims.py`). Locations are `main.tex` line numbers unless a file is named.

---

## 1. Executive Diagnostic

**Evidence and claim alignment** is the main weakness. The paper is honest in its body, but its abstract, introduction, discussion and conclusion describe two results in a way the data do not support. The 97.7% cut in configuration changes on Nobel-Germany comes from a LiRA policy that is a constant classifier, holding configuration 1 for 2,159 of 2,160 test intervals. The "LiRA reaches the oracle under high load" result comes from the safety layer, which sees the realized traffic of the interval it configures. Every ablation that keeps that layer scores the same 880.9. Three typed claims are false: "the only setting" (line 68), "within 0.2% of one" (line 547) and "did not change which configuration the static policy uses" (line 587).

**Technical precision** suffers in five definitions: B4's safety layer is not LiRA's (line 376), O* is a lower bound only over library sequences (line 376), Algorithm 1 pairs states with the wrong label (line 324), the objective starts from c_0 while the evaluation starts free (line 160), and the disruption term uses the training mean matrix (line 140).

**Reasoning structure** has one contradiction across sections. The introduction motivates learning by solver speed (line 53), and Section VII-F says the same solver times "are compatible with five-minute intervals" (line 565).

**Terminology** has two collisions. "Snapshot rule" names both the exact rule of Eq. (7) and the learned classifier B4, and "transitions" names both link power-state toggles (Table IV) and configuration changes (abstract, line 613).

**Paragraph and section structure** is mostly sound. Seven paragraphs carry too many facts at once (lines 363, 376, 380, 415, 426, 565, 613), and the same four-sentence summary of the findings appears in the abstract, the introduction, the discussion and the conclusion.

**Natural academic voice** is good. Sentences are short and direct, and the text keeps a skeptical stance ("This paper tests that hypothesis rather than assuming it", "LiRA is no worse and no better"). That voice should survive the repairs.

**AI-rewrite patterns** are weak at the sentence level. The damage is at the level of reasoning: mechanisms were compressed out of the headline claims, and one caveat from the first draft was dropped (Section 10).

---

## 2. Coverage Verification

- First manuscript line reviewed: 1 (`\documentclass[journal]{IEEEtran}`)
- Last manuscript line reviewed: 657 (`\end{document}`)
- Total line range reviewed: 1 to 657, all lines
- Sections reviewed: Title, Abstract, Index Terms, I Introduction, II Related Work (A to D), III Problem Formulation (A to F), IV Framework (A to E), V Algorithms, VI Setup (A to D), VII Results (A to I), VIII Discussion, IX Limitations, X Conclusion, Data Availability, References
- Equations reviewed: 10 numbered equations (1) to (10)
- Propositions and proofs reviewed: 4 (Propositions 1 to 4)
- Algorithms reviewed: 2
- Tables reviewed: 14 (I to XIV), including all 13 generated table files
- Figures and captions reviewed: 6 (Figs. 1 to 6), including the plot data of Figs. 3 to 6
- Generated macros reviewed: 112 in `results_macros.tex`
- Reference section reviewed: yes, 51 rendered entries in the PDF
- Unreviewed regions: NONE. Preamble lines 2 to 27 contain packages, colors and TikZ styles only and were checked for content, not for prose

---

## 3. Critical Issues

```
Issue I-01
Location: Line 68
Section: I Introduction
Severity: Critical
Priority: P1
Category: D Evidence/claim

Original passage:
"and the only setting in which LiRA is better than tuned hysteresis in cost (higher load, \nobhlJLiRA\ against \nobhlJBSix) is not statistically significant."

Problem:
The claim is false. In the Nobel-Germany stress scenario LiRA costs 898.6 and B6 costs 899.4 (Table V, generated/tab_scen.tex). LiRA is better than tuned hysteresis in two settings, high load and stress, and ties it in the high-dynamic-power setting (883.7 both).

Why it matters:
A reviewer who reads Table V will find the contradiction in the introduction, which damages trust in the rest of the paper.

Underlying pattern:
Hand-typed comparative claim not derived from the result files (P-03).

What to restore/check:
State the comparison for every Nobel scenario from Table V, with B2 included, and generate the wording from the data.

Related issues:
I-03, I-19
```

```
Issue I-02
Location: Lines 44, 68, 426, 626, 648
Section: Abstract, Introduction, Results VII-A, Discussion, Conclusion
Severity: Critical
Priority: P1
Category: D Evidence/claim, B Reasoning

Original passage:
Line 44: "LiRA reduces configuration changes and link transitions by \nobY\% at unchanged savings"
Line 626: "In the first case, a sequence-aware learner removes nearly all changes without losing energy."
Line 648: "sequence awareness removes \nobY\% of its configuration changes at no loss of energy"

Problem:
In the setting these sentences describe (Nobel-Germany, base), the trained LiRA policy is a ConstantModel in all five seeds (E1_main/nobel_base_info.json). It holds configuration 1 for 2,159 of 2,160 test intervals, and its 0.27 changes per day are safety-layer switches. The 97.7% figure therefore measures "never change" against a flapping B4, not a learned sequence decision. Line 415 discloses the constant policy, but the sentences above present the reduction as the learner's achievement.

Why it matters:
The reader of the abstract and conclusion will believe that a history-conditioned learner produced the reduction. The paper's own body says otherwise.

Underlying pattern:
Mechanism omitted from a headline result (P-01).

What to restore/check:
Name the mechanism wherever the 97.7% appears: the policy holds the configuration that was optimal on the training period, and any rule that does so (Static + fallback, E17) gives the same reduction.

Related issues:
I-03, I-14, I-15, I-25
```

```
Issue I-03
Location: Lines 44, 68, 443, 628
Section: Abstract, Introduction, Results VII-B, Discussion
Severity: Critical
Priority: P1
Category: D Evidence/claim, B Reasoning

Original passage:
Line 443: "LiRA is the only method that reaches the oracle (\nobhlJLiRA\ against \nobhlJBSix\ for B6 and \nobhlJBFour\ for B4)"
Line 628: "and, in the high-load setting, a lower cost than hysteresis, although not a significant one."

Problem:
LiRA's test sequence equals the oracle's in all 2,160 intervals and all five seeds (E1_main/nobel_highload_seqs.npz). Line 514 explains why: "the expert is nearly constant, so all variants that keep the safety layer reach the oracle cost". The safety layer checks feasibility on the realized D_t (line 299), so it switches exactly when the default configuration becomes infeasible, which is what the oracle does. The best DAgger round is 0 in all five seeds. Line 443 also omits the rolling-horizon B2, which reaches 882.2, closer to the oracle than B6 (887.0).

Why it matters:
The only positive cost result for LiRA is attributed to learning, while the paper's own ablation attributes it to a safety layer with perfect same-interval information. A non-learning optimiser comes within 0.14% and is not mentioned.

Underlying pattern:
Mechanism omitted (P-01) and selective baseline comparison (P-02).

What to restore/check:
Report B2 and the static rule (E17) next to LiRA. State the mechanism. Report the same comparison under one-interval-old information (E16).

Related issues:
I-01, I-04, I-19
```

```
Issue I-04
Location: Lines 168, 287, 299, 632
Section: III-E, IV-D, VIII Discussion
Severity: Critical
Priority: P1
Category: C Technical precision, D Evidence/claim

Original passage:
Line 299: "The guarantee holds for the estimate $\hat D_t$. In our evaluation the estimate equals the realized matrix, so violations occur only when no library member is feasible."
Line 632: "so a mispredicting model degrades to higher energy use and not to congestion, as long as the all-on configuration is feasible"

Problem:
The assumption that the controller knows D_t when it configures interval t governs every online result: B4, B6, B7, B2, LiRA and the 0.00% violation columns. It appears once, inside the safety-layer subsection. Line 632 then transfers a guarantee that holds "for the estimate" to realized congestion, which the evaluation never tests.

Why it matters:
A reader who skips Section IV-D will read the zero-violation results as a property of the methods. A deployed controller configures interval t from D_{t-1} or a forecast.

Underlying pattern:
Buried modelling assumption (P-06) and theory-to-deployment scope transfer (P-11).

What to restore/check:
Move the information assumption to Section VI. Report results under D_{t-1} (E16). Limit line 632 to accurate estimates and quote the measured violations.

Related issues:
I-03, I-33
```

---

## 4. High-Priority Issues

```
Issue I-05
Location: Line 376
Section: VI-B Baselines
Severity: High
Priority: P1
Category: C Technical precision

Original passage:
"We also report the offline oracle $\mathrm{O}^\star$, which uses the future and is a lower bound."

Problem:
O* is optimal over library sequences only. It is not a lower bound for B1, B3 or B5, which choose any link state. On the GÉANT subsample B1 saves 29.8478% against 29.8455% for the library snapshot optimum (E5 opt-baseline CSV).

Why it matters:
"Lower bound" without a scope is a mathematical claim the paper does not prove.

Underlying pattern:
Qualifier dropped (P-06).

What to restore/check:
Restrict the claim to library controllers, and report the library-free bound (E15).

Related issues:
I-31
```

```
Issue I-06
Location: Line 547
Section: VII-E Wear
Severity: High
Priority: P1
Category: D Evidence/claim

Original passage:
"whereas the most-cycled links of the other methods stay within 0.2\% of one."

Problem:
LiRA's most-cycled link has AF 1.0024 (E4_per_link_wear/nobel_base_per_link.csv), which is 0.24% above one.

Why it matters:
A checkable number is wrong.

Underlying pattern:
Hand-typed number (P-03).

What to restore/check:
Generate the maximum AF of each method as a macro.

Related issues:
I-07, I-22
```

```
Issue I-07
Location: Line 587
Section: VII-G Traffic Drift
Severity: High
Priority: P1
Category: D Evidence/claim

Original passage:
"The shifts did not change which configuration the static policy uses, because the library stays feasible, and its cost changed by at most 0.74\% relative to the unshifted stream, which is the cost of the additional traffic itself."

Problem:
On Nobel-Germany the hotspot shift doubles the static policy's switches from 0.41 to 0.82 per day (E8_drift/nobel_drift.csv). Part of the 0.74% is therefore switching cost, not "the cost of the additional traffic itself".

Why it matters:
The sentence states an absence of effect that the data contradict for one of three topologies.

Underlying pattern:
Hand-typed claim (P-03) and unsupported causal gloss (P-05).

What to restore/check:
State per topology what changed, from the drift CSV.

Related issues:
I-28
```

```
Issue I-08
Location: Line 514
Section: VII-D Ablation
Severity: High
Priority: P1
Category: D Evidence/claim

Original passage:
"Removing the previous-configuration input raises the cost to \ablStressNoPrev, removing the cost-sensitive weights to \ablStressNoCS, removing DAgger to \ablStressNoDagger, and removing the lag features to \ablStressNoLag."

Problem:
The list is governed by "raises the cost to", but removing the lag features lowers the cost (895.6 against 897.4 for the full policy).

Why it matters:
A mixed-sign result reads as uniform support for every component.

Underlying pattern:
Negative result absorbed into a positive list (P-02).

What to restore/check:
Separate the lag-feature result and say that it lowers the cost.

Related issues:
I-15
```

```
Issue I-09
Location: Line 376
Section: VI-B Baselines
Severity: High
Priority: P1
Category: C Technical precision

Original passage:
"an XGBoost classifier that maps the current traffic features to the energy-optimal feasible library member, with the same safety layer as LiRA."

Problem:
B4 falls back to the cheapest feasible configuration by energy (`safe_batch`, lira_policy.py:44). LiRA falls back to Eq. (9), which adds the reconfiguration and wear costs (lira_policy.py:142-144).

Why it matters:
The difference changes which configuration each method takes when its choice is infeasible, so "same" misdescribes the comparison.

Underlying pattern:
Method description drifted from code.

What to restore/check:
Describe B4's fallback as the energy-optimal feasible configuration.

Related issues:
I-10
```

```
Issue I-10
Location: Line 324 (Algorithm 1, line 4)
Section: V Algorithms
Severity: High
Priority: P1
Category: C Technical precision, Math-prose alignment

Original passage:
"\State $\mathcal{D}\gets\{(s_t,c^\star_{t-1})\}$ along the oracle trajectory, with weights $w$"

Problem:
The training pair is (state, label). The state s_t already contains c*_{t-1}. The label is c*_t (lira_policy.py:196).

Why it matters:
As written, the algorithm trains the policy to predict the configuration it already has.

Underlying pattern:
Notation error in a formal object.

What to restore/check:
Write the pair as (s_t, c*_t) with s_t built from c*_{t-1}.

Related issues:
none
```

```
Issue I-11
Location: Lines 53 and 565
Section: I Introduction, VII-F Decision Time
Severity: High
Priority: P1
Category: B Reasoning, Cross-section consistency

Original passage:
Line 53: "exact solvers need seconds per traffic matrix on realistic topologies (Section~\ref{sec:res-time}), which is slow for control loops that run every few minutes."
Line 565: "These times are compatible with five-minute intervals but not with sub-second control, which is where learned decisions help."

Problem:
The introduction says seconds are too slow for five-minute loops, and the cited section says they are fast enough.

Why it matters:
The motivation for learned controllers contradicts the paper's own measurement.

Underlying pattern:
Motivation inherited from the snapshot-learning literature and not re-checked against the results.

What to restore/check:
Motivate learning by what the paper measures: solver times grow with topology size (TA2: 11.4 s), and learned decisions cost under 2 ms, which matters for larger networks or shorter intervals.

Related issues:
I-39
```

```
Issue I-12
Location: Line 44 (abstract) and line 613
Section: Abstract, VII-I Emulation
Severity: High
Priority: P1
Category: D Evidence/claim, Typesetting

Original passage:
"a Mininet emulation of \emuTrans\ transitions shows that each change takes about \emuTransS\\,s and loses a few probe packets."

Problem:
Of the 1.11 s, 1.0 s is the modeled wake-up delay, a constant the emulator sleeps for (emulate_mininet.py:162). The measured part is 99 ms of rule installation. The source also contains `\\,s`, which prints a line break and a stray ",s" in the abstract of the PDF.

Why it matters:
The abstract presents an assumed constant as a measurement, and the abstract is visibly broken.

Underlying pattern:
Measured and modeled quantities merged (P-06).

What to restore/check:
Report the measured rule-installation time and name the modeled delay. Fix the macro call.

Related issues:
I-16
```

```
Issue I-13
Location: Line 648
Section: X Conclusion
Severity: High
Priority: P1
Category: D Evidence/claim, Scope

Original passage:
"On two real traces, a snapshot rule is already optimal, and the oracle and LiRA coincide with it."

Problem:
On Abilene B4 costs 0.014% more than the oracle, and the exact snapshot rule of Eq. (7) changes configuration 0.19 times per day and costs 0.14% more (E1 Abilene base). Line 415 says "within 0.02%". Only on GÉANT is the snapshot classifier exactly optimal.

Why it matters:
The conclusion upgrades "within 0.02%" to "optimal".

Underlying pattern:
Claim strength drift across sections (P-10).

What to restore/check:
Use the Results-section wording with the measured gap.

Related issues:
I-17
```

```
Issue I-14
Location: Line 628
Section: VIII Discussion
Severity: High
Priority: P1
Category: D Evidence/claim

Original passage:
"The learner is useful when prices or traffic make the optimal sequence non-constant."

Problem:
The two non-constant settings do not show this. Under high load every variant with the safety layer reaches the oracle (line 514). Under stress LiRA costs 898.6, B6 899.4 and the oracle 894.3, and the differences are not significant (Table V).

Why it matters:
The discussion asserts a benefit that no experiment isolates.

Underlying pattern:
Mechanism omitted (P-01) and scope inflation (P-11).

What to restore/check:
State what the evidence supports: the oracle and the safety layer carry the results, and the learned component adds at most a small, non-significant gain in one scenario.

Related issues:
I-02, I-03
```

```
Issue I-15
Location: Lines 63, 272, 283, 326-331 (Algorithm 1)
Section: I, IV-C, V
Severity: High
Priority: P1
Category: D Evidence/claim, C Technical precision

Original passage:
Line 272: "Among the rounds, we keep the policy with the lowest sequence cost on the validation period."

Problem:
Round 0, plain imitation of the oracle trajectory, has the lowest validation cost in 56 of 60 E1 runs (E1_main/*_info.json, lira_best_round). DAgger data enter the deployed policy only in four Nobel stress runs. The paper presents DAgger and Proposition 3 as properties of the learner without this fact.

Why it matters:
Readers will attribute LiRA's results to DAgger.

Underlying pattern:
Mechanism omitted (P-01).

What to restore/check:
Report the selected-round count next to the constant-policy count.

Related issues:
I-02, I-08
```

```
Issue I-16
Location: Line 44 and line 613 versus Table IV (line 423) and line 426
Section: Abstract, VII-I, VII-A
Severity: High
Priority: P1
Category: Terminology

Original passage:
Line 44: "a Mininet emulation of \emuTrans\ transitions"
Line 613: "B4 makes \emuTrans\ transitions on this day"
Table IV header: "Transitions/d" (link power-state toggles)

Problem:
"Transitions" counts link power-state toggles in Table IV and line 426, and configuration changes in the abstract and line 613. The 18 emulated "transitions" are 18 configuration changes that toggle 36 links (emulation_summary.csv, links_toggled).

Why it matters:
A reader compares 18 "transitions" with "23.4 link transitions per day" and gets a wrong picture.

Underlying pattern:
Same term for two objects (P-04).

What to restore/check:
Use "configuration change" for c_{t-1} ≠ c_t and "link transition" for a power-state toggle, everywhere.

Related issues:
I-17
```

```
Issue I-17
Location: Lines 44 (last sentence), 68 (last sentence), 175-178, 426, 648
Section: Abstract, Introduction, III-F, VII-A, Conclusion
Severity: High
Priority: P2
Category: Terminology

Original passage:
Line 44: "and that on smooth real traffic a simple snapshot rule already suffices."
Line 426: "whereas the exact snapshot rule would change \nobSnapChg\ times per day."

Problem:
"Snapshot rule" means Eq. (7), solved exactly, in lines 175, 178 and 426, and the learned classifier B4 in lines 44, 68 and 648. The two behave differently: the exact rule changes 63.7 times per day on Nobel, B4 11.7.

Why it matters:
The abstract's closing claim is ambiguous between two methods with very different flapping.

Underlying pattern:
Terminology collision (P-04).

What to restore/check:
Reserve "snapshot rule" for Eq. (7) and "snapshot classifier" for B4.

Related issues:
I-13, I-16
```

```
Issue I-18
Location: Line 44
Section: Abstract
Severity: High
Priority: P1
Category: E Structural, Venue compliance

Original passage:
the whole abstract (279 words)

Problem:
IEEE Transactions abstracts must have 150 to 250 words. The abstract also carries eleven numbers, which crowd out the method.

Why it matters:
The submission system can reject the abstract, and the density hides the main message.

Underlying pattern:
Over-compression (P-07).

What to restore/check:
Cut to at most 250 words and keep only the numbers a reader needs to judge the claims.

Related issues:
I-02, I-03, I-12
```

```
Issue I-19
Location: Lines 426, 443, 626
Section: VII-A, VII-B, VIII
Severity: High
Priority: P1
Category: D Evidence/claim, Negative-result preservation

Original passage:
Line 426: "Hysteresis (B6) achieves \nobBsixChg\ changes per day, so LiRA is not better than a tuned hysteresis rule"

Problem:
B2 equals B6 on Nobel base (875.3, 0.13 changes per day, Table IV) and reaches 882.2 under high load. The paper never discusses B2 on Nobel, although Table IV lists it.

Why it matters:
A non-learning optimiser with a persistence forecast matches or beats LiRA in three of four Nobel scenarios. Leaving it out flatters LiRA.

Underlying pattern:
Selective comparison (P-02).

What to restore/check:
Discuss B2 next to B6 in every Nobel comparison.

Related issues:
I-01, I-03
```

---

## 5. Medium-Priority Issues

```
Issue I-20
Location: Line 63
Section: I Introduction
Severity: Medium
Priority: P1
Category: Reader orientation, Cross-reference

Original passage:
"and Section~\ref{sec:res-main} reports that our drift study does not validate them"

Problem:
`sec:res-main` is Section VII-A, "Do Real Traces Need Sequence Awareness?". The drift study is Section VII-G, which has no label.

Why it matters:
The reader is sent to the wrong section.

Underlying pattern:
Traceability error (P-08).

What to restore/check:
Label the drift subsection and cite it.

Related issues:
I-21, I-22
```

```
Issue I-21
Location: Line 630
Section: VIII Discussion
Severity: Medium
Priority: P1
Category: D Evidence/claim, Cross-reference

Original passage:
"because the oracle runs in seconds (Section~\ref{sec:res-time})"

Problem:
Section VII-F reports B1, B3, B4, B5 and LiRA times. The oracle time is not there. It is 3.6 s for 48,108 Abilene intervals (results/labels_abilene_K32.json).

Why it matters:
A claim points to a section that does not support it.

Underlying pattern:
Traceability error (P-08).

What to restore/check:
Report the DP run time in Section VII-F as a macro.

Related issues:
I-20
```

```
Issue I-22
Location: Line 565
Section: VII-F Decision Time
Severity: Medium
Priority: P1
Category: Cross-table consistency

Original passage:
"Solving the integer program per traffic matrix (B1) takes a median of \nobIlpMs\,ms on Nobel-Germany and \ilpGeant\,s on G\'{E}ANT"

Problem:
`\ilpGeant` (4.1 s) comes from three repetitions on one matrix (scalability.csv). Table X, cited in the same sentence, shows 3.53 s over 60 matrices (`\geaIlpS`).

Why it matters:
The text and the table disagree on the same quantity.

Underlying pattern:
Wrong macro (P-08).

What to restore/check:
Use the 60-matrix median.

Related issues:
I-06
```

```
Issue I-23
Location: Line 525
Section: VII-D Library Size
Severity: Medium
Priority: P1
Category: C Technical precision, Unsupported mechanism

Original passage:
"Requested sizes above \KactualMax\ yield the same library, because the greedy pruning stops when no configuration lowers the energy further."

Problem:
The candidate pool for Nobel-Germany has 51 configurations (results/library_nobel_report.json). Pruning has a fill-up stage, so sizes above 51 are capped by the pool, not by the stopping rule.

Why it matters:
The stated mechanism is wrong.

Underlying pattern:
Unsupported causal gloss (P-05).

What to restore/check:
State the candidate count.

Related issues:
I-31
```

```
Issue I-24
Location: Line 415
Section: VII-A
Severity: Medium
Priority: P2
Category: C Technical precision

Original passage:
"The snapshot classifier B4 changes configuration \abiBFourchg\ times per day on Abilene and never on G\'{E}ANT, so the reductions $Y$ and $Z$ are undefined."

Problem:
Y and Z are undefined on GÉANT only. On Abilene they are defined but rest on fewer than one change on average over 41.8 days (0.019 per day).

Why it matters:
The logical connective "so" is wrong for half of the statement.

Underlying pattern:
Compressed causal chain.

What to restore/check:
Separate the two traces.

Related issues:
none
```

```
Issue I-25
Location: Line 415
Section: VII-A
Severity: Medium
Priority: P1
Category: C Technical precision

Original passage:
"In these settings LiRA reduces to ``stay in the best configuration'', and its ablations are trivial."

Problem:
The constant policy holds the configuration that was best on the training period. On Nobel base that is configuration 1, while the test-period oracle uses configuration 2, which is why LiRA (875.9) costs more than the oracle (874.7).

Why it matters:
"The best configuration" hides the source of LiRA's gap to the oracle.

Underlying pattern:
Qualifier dropped (P-06).

What to restore/check:
Write "the configuration that was optimal on the training period".

Related issues:
I-02
```

```
Issue I-26
Location: Line 501
Section: VII-C Classifier
Severity: Medium
Priority: P2
Category: Unsupported mechanism

Original passage:
"The random forest, whose averaging over trees smooths the decision boundary, is nearly as stable as LiRA"

Problem:
No experiment measures decision-boundary smoothness. The explanation is plausible but untested.

Why it matters:
An interpretation is presented as an observed mechanism.

Underlying pattern:
Unsupported causal gloss (P-05).

What to restore/check:
Mark it as a likely explanation or remove it.

Related issues:
I-27
```

```
Issue I-27
Location: Line 626
Section: VIII Discussion
Severity: Medium
Priority: P2
Category: Unsupported mechanism

Original passage:
"This happens with noisy demands and with classifiers that have jagged decision boundaries"

Problem:
"Jagged decision boundaries" is not measured. The observed fact is that XGBoost, LightGBM and the MLP flap and the random forest does not.

Why it matters:
Same as I-26.

Underlying pattern:
P-05.

What to restore/check:
Name the classifiers instead of the mechanism.

Related issues:
I-26
```

```
Issue I-28
Location: Line 587
Section: VII-G Traffic Drift
Severity: Medium
Priority: P2
Category: Scope

Original passage:
"This experiment shows that drift is not a problem in our data, but it does not validate the detectors."

Problem:
The experiment shows that three injected shifts did not change the optimal configuration. It says nothing about drift in general or about the drift present in the traces.

Why it matters:
A narrow result is stated as a property of "our data".

Underlying pattern:
Scope inflation (P-11).

What to restore/check:
Limit the claim to the injected shifts.

Related issues:
I-07
```

```
Issue I-29
Location: Line 84
Section: II-C Related Work
Severity: Medium
Priority: P2
Category: Literature claim

Original passage:
"These methods optimize each traffic matrix independently."

Problem:
DOTE [10] maps a window of past traffic matrices to a configuration, so it does not treat matrices independently. What the cited methods share is that none prices the change between consecutive configurations.

Why it matters:
The gap statement is broader than the literature supports.

Underlying pattern:
Literature generalisation.

What to restore/check:
State the distinction as "no reconfiguration cost".

Related issues:
none
```

```
Issue I-30
Location: Lines 44, 68, 428, 437
Section: Abstract, Introduction, VII-A, Fig. 3 caption
Severity: Medium
Priority: P2
Category: D Evidence/claim, Consistency

Original passage:
Line 44: "nearly every change saves less than one percent of the interval energy"
Line 437: "Nearly all changes save less than 0.1\% of the interval energy."

Problem:
Two thresholds describe the same 96 changes. The data: every change saves less than 0.5%, and 95 of 96 (99%) save less than 0.1% (generated/gain_hist.dat). "Nearly every ... less than one percent" understates the result.

Why it matters:
The strongest and simplest statement is lost, and the abstract and the caption disagree.

Underlying pattern:
Claim drift (P-10).

What to restore/check:
Use one threshold, generated from the histogram.

Related issues:
I-46
```

```
Issue I-31
Location: Line 525 and Table VIII caption (line 529)
Section: VII-D
Severity: Medium
Priority: P2
Category: D Evidence/claim

Original passage:
Table VIII column "Coverage (\%)"

Problem:
The column is coverage on validation matrices (run_main.py:250), and the library builder solved integer programs for uncovered validation matrices (build_library.py:87). 100.0% is built in.

Why it matters:
The reader takes it as out-of-sample coverage.

Underlying pattern:
Buried assumption (P-06).

What to restore/check:
Report test coverage.

Related issues:
I-23
```

```
Issue I-32
Location: Lines 514, 643 versus Table V
Section: VII-D, IX
Severity: Medium
Priority: P1
Category: Cross-table consistency

Original passage:
Line 643: "and stress scenario (\ablStressFull\ against \ablStressO\ for the oracle)"

Problem:
Line 643 quotes 897.4 (ablation, seeds 0 to 2). Table V shows 898.6 for the same LiRA (seeds 0 to 4). The difference is the seed set, which the text does not say.

Why it matters:
Two values for one quantity.

Underlying pattern:
P-08.

What to restore/check:
Quote the five-seed value outside the ablation and state the seed set in the ablation caption.

Related issues:
I-22
```

```
Issue I-33
Location: Line 380
Section: VI-C Metrics
Severity: Medium
Priority: P1
Category: C Technical precision

Original passage:
"the sequence cost $J$ of \eqref{eq:objective}"

Problem:
Eq. (6) holds "subject to (1)", but the reported J has no violation penalty (common.py:96-138). This is why "no safety layer" (889.9) scores below the oracle (894.3). Line 514 explains the effect only for the ablation.

Why it matters:
Readers comparing J across methods with violations will misread it.

Underlying pattern:
P-06.

What to restore/check:
Define the reported J and say that violations are reported separately.

Related issues:
I-04
```

```
Issue I-34
Location: Line 380
Section: VI-C Metrics
Severity: Medium
Priority: P2
Category: C Technical precision

Original passage:
"The cost $J$ includes the modeled wear credit of sleeping links, so it is not an energy figure"

Problem:
The size of the credit matters for interpretation. With the default prices, a sleeping link earns λ_W(1-α)/n_d = 0.04 per interval, while sleeping it saves 0.9/|E| of energy (0.035 on Nobel, 0.025 on GÉANT, 0.06 on Abilene). On two topologies the wear credit exceeds the energy saving.

Why it matters:
J rewards sleeping more for lifetime than for energy, which a reader cannot see.

Underlying pattern:
P-06.

What to restore/check:
State the two per-link values.

Related issues:
I-33
```

```
Issue I-35
Location: Lines 160-164
Section: III-E
Severity: Medium
Priority: P2
Category: Math-prose alignment

Original passage:
"Given an initial configuration $c_0$, the sequential problem selects $c_1,\dots,c_T\in\mathcal{C}$ that minimize"

Problem:
The evaluation and the oracle start free: no switching cost is charged at the first interval of a test segment (common.py `evaluate`, `viterbi(c0=None)`), and no cost is charged across an unfilled gap.

Why it matters:
Small, but the reported J is not exactly Eq. (6).

Underlying pattern:
P-06.

What to restore/check:
State the free start and the segment rule in Section VI-C.

Related issues:
I-33
```

```
Issue I-36
Location: Line 140
Section: III-C
Severity: Medium
Priority: P2
Category: C Technical precision

Original passage:
"and moves a share $B(c',c)\in[0,1]$ of the traffic to different paths"

Problem:
B is computed on the mean training traffic matrix, not on D_t (common.py `component_matrices(..., od[train].mean)`).

Why it matters:
R is a fixed K x K table, which is what makes the DP exact. The prose suggests a traffic-dependent cost.

Underlying pattern:
P-06.

What to restore/check:
Name the reference matrix.

Related issues:
none
```

```
Issue I-37
Location: Line 376
Section: VI-B
Severity: Medium
Priority: P2
Category: C Technical precision

Original passage:
"B0 keeps all links on."

Problem:
B0 also routes each demand on its shortest path (routing.py:41). That is why B0 violates θ in 0.05% of Nobel intervals while load-balanced library members do not (Table IV).

Why it matters:
Readers will wonder why the all-on network violates the bound.

Underlying pattern:
P-06.

What to restore/check:
State B0's routing.

Related issues:
none
```

```
Issue I-38
Location: Line 613
Section: VII-I
Severity: Medium
Priority: P2
Category: Terminology

Original passage:
"Each configuration installs one shortest-dominant path per origin--destination pair"

Problem:
The emulator installs the path with the largest split share (emu_export.py), which is not necessarily the shortest. "Shortest-dominant" is not a defined term.

Why it matters:
The routing used in the emulation is unclear.

Underlying pattern:
P-04.

What to restore/check:
Write "the path that carries the largest share of the demand".

Related issues:
none
```

```
Issue I-39
Location: Line 565
Section: VII-F
Severity: Medium
Priority: P2
Category: Unsupported claim

Original passage:
"but not with sub-second control, which is where learned decisions help."

Problem:
The paper has no sub-second experiment.

Why it matters:
The sentence closes the speed argument with an untested claim.

Underlying pattern:
P-05.

What to restore/check:
Tie the speed argument to the measured growth with topology size.

Related issues:
I-11
```

```
Issue I-40
Location: Line 363
Section: VI-A Datasets
Severity: Medium
Priority: P2
Category: E Structural, Cognitive load

Original passage:
the whole paragraph (sources, Nobel generator, noise, cleaning, splits, scaling, scenarios)

Problem:
One paragraph carries seven separate decisions and nine numbers.

Why it matters:
The scenario definitions, which later results depend on, are buried at its end.

Underlying pattern:
Overloaded paragraph (P-07).

What to restore/check:
Split into data, preprocessing and scenarios.

Related issues:
I-41, I-42
```

```
Issue I-41
Location: Line 380
Section: VI-C
Severity: Medium
Priority: P2
Category: E Structural

Original passage:
the whole paragraph (metrics, X/Y/Z, prices, seeds, statistics, interpretation of J)

Problem:
Metrics, prices, statistics and a caveat on J share one paragraph.

Why it matters:
The statistical procedure is hard to find.

Underlying pattern:
P-07.

What to restore/check:
Separate prices and statistics.

Related issues:
I-40
```

```
Issue I-42
Location: Line 415
Section: VII-A
Severity: Medium
Priority: P2
Category: E Structural

Original passage:
"A caveat applies to the whole study: in \liraConstRuns\ of \liraTotalRuns\ LiRA runs ..."

Problem:
A study-wide caveat is the last sentence of the paragraph on real traces.

Why it matters:
The caveat governs Sections VII-A to VII-D but reads as a remark on Abilene and GÉANT.

Underlying pattern:
Information order.

What to restore/check:
Give the caveat its own paragraph at the start of the Results, together with the DAgger count and the information protocol.

Related issues:
I-02, I-15
```

```
Issue I-43
Location: Lines 44, 63
Section: Abstract, Introduction
Severity: Medium
Priority: P2
Category: Reader orientation

Original passage:
Line 44: "we use this solution to train LiRA, a history-conditioned policy"

Problem:
The acronym LiRA is never expanded. The first draft expanded it (main_v1_placeholders.tex:66, "We call the resulting framework LiRA (Lifetime- and Reconfiguration-Aware learning)").

Why it matters:
Readers do not learn what the name stands for.

Underlying pattern:
Qualification removal during the rewrite.

What to restore/check:
Expand the acronym at first use in the introduction.

Related issues:
none
```

```
Issue I-44
Location: Lines 104-116, 133, 268, 404
Section: III, IV-C, Table III
Severity: Medium
Priority: P2
Category: Notation

Original passage:
"$G=(V,E)$ & Network graph; $E$ is the set of undirected links" and "$E(c,D)$ & Energy of $c$ under traffic $D$"

Problem:
E denotes both the link set and the energy, and Eq. (2) uses both in one line. δ denotes the dwell time (line 268) and the ADWIN and Page-Hinkley parameters (Table III). α denotes the sleep factor and a Page-Hinkley parameter.

Why it matters:
Readers must disambiguate from context.

Underlying pattern:
Notation collision.

What to restore/check:
Rename the Page-Hinkley symbols in Table III and write the dwell time with a distinct symbol. Keeping E for both is common, but say so.

Related issues:
I-51
```

```
Issue I-45
Location: Line 312
Section: V Algorithms
Severity: Medium
Priority: P2
Category: Epistemic boundary

Original passage:
"Reconfigurations follow a make-before-break order"

Problem:
Only the Mininet emulation implements the order. The flow-level simulator has no transient.

Why it matters:
The reader may think simulated results include transition effects.

Underlying pattern:
Simulation versus emulation boundary.

What to restore/check:
Say where the order is implemented.

Related issues:
I-12
```

```
Issue I-46
Location: Line 428
Section: VII-A
Severity: Medium
Priority: P2
Category: D Evidence/claim

Original passage:
"Fig.~\ref{fig:gain} shows why the flapping is harmless to remove. Among the \gainChanges\ configuration changes of B4 in the test period, \gainLowShare\% save less than one percent of the interval energy, and the median saving is \gainMedian\%."

Problem:
The figure shows that the changes save little energy, not why. The 96 changes are seed 0 only. "100% save less than one percent" and "the median saving is 0.00%" are awkward ways to say "every change saves less than 0.5%, and the median is below 0.01%".

Why it matters:
A verb overclaims and the sample is not identified.

Underlying pattern:
P-10.

What to restore/check:
State the seed and use the clearer thresholds.

Related issues:
I-30
```

```
Issue I-47
Location: Lines 44, 68, 626, 648
Section: Abstract, Introduction, Discussion, Conclusion
Severity: Medium
Priority: P2
Category: Repetition

Original passage:
Line 68: "Our findings are mixed, and we report them as measured. On the two real traces ..."

Problem:
The same summary (real traces constant, Nobel flaps, hysteresis matches, high load not significant) appears four times with nearly the same sentences.

Why it matters:
Potentially redundant. The repetition also spreads the I-01 to I-03 errors to four places.

Underlying pattern:
Redundant summaries (P-09).

What to restore/check:
Keep the full summary in the abstract and introduction, and let the discussion interpret instead of repeating.

Related issues:
I-01, I-02, I-03
```

```
Issue I-48
Location: Line 380
Section: VI-C
Severity: Medium
Priority: P2
Category: Statistical language

Original passage:
"We compare per-day sequence costs of LiRA and each baseline with the Wilcoxon signed-rank test"

Problem:
Only B4, B6 and B7 are tested (run_main.py:149). B2 is not.

Why it matters:
"Each baseline" overstates the test coverage.

Underlying pattern:
P-10.

What to restore/check:
Name the three comparisons.

Related issues:
I-19
```

```
Issue I-49
Location: Line 643
Section: IX Limitations
Severity: Medium
Priority: P2
Category: C Technical precision

Original passage:
"a non-trivial learned policy is evaluated only on G\'{E}ANT, where it equals the oracle"

Problem:
On GÉANT the XGBoost policy is non-constant as a model but outputs one configuration for the whole test split, so it is constant in effect.

Why it matters:
"Non-trivial" suggests a learned decision rule was exercised there.

Underlying pattern:
P-01.

What to restore/check:
Say that its outputs are constant on the test split.

Related issues:
I-02
```

```
Issue I-50
Location: Lines 227, 319-321
Section: IV-A, Algorithm 1
Severity: Medium
Priority: P2
Category: Math-prose alignment

Original passage:
"\Require training traces $D_{1:T}$" and "\State $\mathcal{C}\gets$ \Call{BuildLibrary}{$D_{1:T}$}"

Problem:
Line 227 says integer programs are solved "for uncovered training and validation matrices", so the library also uses validation data. Algorithm 1 says training traces only.

Why it matters:
Small inconsistency between text and algorithm.

Underlying pattern:
P-08.

What to restore/check:
Name the validation matrices in Algorithm 1.

Related issues:
I-31
```

---

## 6. Low-Priority Issues

```
Issue I-51
Location: Lines 125, 196-197, 289
Section: III-A, Fig. 1, IV-D
Severity: Low
Priority: P2
Category: Reader orientation
Original passage: "\mathrm{MLU}(c,D)=\max..." and "TM traces $D_{1:T}$" and "$\hat D_t$"
Problem: MLU is expanded only at line 363, "TM" is never defined, and \hat D_t is missing from Table I.
Why it matters: Undefined symbols at first use.
Underlying pattern: Notation introduced late.
What to restore/check: Expand MLU at Eq. (1), use "traffic matrix" in Fig. 1, add \hat D_t to Table I.
Related issues: I-44
```

```
Issue I-52
Location: Line 637
Section: IX
Severity: Low
Priority: P3
Category: Precision
Original passage: "one backbone (Abilene, 2004) and one research network (G\'{E}ANT, 2005)"
Problem: Both are research and education backbones.
Why it matters: Implies a contrast that does not exist.
Underlying pattern: Loose description.
What to restore/check: "two research and education backbones".
Related issues: none
```

```
Issue I-53
Location: Line 363
Section: VI-A
Severity: Low
Priority: P2
Category: Hidden assumption
Original passage: "which is shorter than the seven days we require"
Problem: The reason for seven days is not stated (weekly features and a chronological split need at least a week).
Why it matters: The requirement reads as arbitrary.
Underlying pattern: P-06.
What to restore/check: Give the reason.
Related issues: I-40
```

```
Issue I-54
Location: Line 468 (Fig. 4 caption)
Section: VII-B
Severity: Low
Priority: P3
Category: Figure language
Original passage: "B4 switches repeatedly between neighboring configurations"
Problem: Configuration indices are arbitrary labels, so "neighboring" has no meaning.
Why it matters: Suggests an order that does not exist.
Underlying pattern: Loose description.
What to restore/check: "between two configurations".
Related issues: none
```

```
Issue I-55
Location: Line 617 (Table XIV caption)
Section: VII-I
Severity: Low
Priority: P2
Category: Measured versus computed
Original passage: "Link-Hours Are the Emulated Active Link Time"
Problem: Link-hours are computed from the replayed configuration sequence (emulate_mininet.py, link_on_seconds), not measured.
Why it matters: Same boundary as I-12.
Underlying pattern: P-06.
What to restore/check: Say "computed from the replayed configurations".
Related issues: I-12
```

```
Issue I-56
Location: Line 565
Section: VII-F
Severity: Low
Priority: P3
Category: Number formatting
Original passage: "\abiLatLiRA\,ms and \nobLatLiRA\,ms where the policy is constant and \geaLatLiRA\,ms"
Problem: Three decimals for LiRA, two for B4, and 0.008 ms is the cost of returning a constant.
Why it matters: Inconsistent precision.
Underlying pattern: Formatting.
What to restore/check: One precision, and call the constant case what it is.
Related issues: none
```

```
Issue I-57
Location: Line 628
Section: VIII
Severity: Low
Priority: P2
Category: Cross-reference
Original passage: "a way to measure the gap to it (the regret in Table~\ref{tab:scen})"
Problem: Table V reports J, not regret.
Why it matters: Small mismatch.
Underlying pattern: P-08.
What to restore/check: "the cost gap to O* in Table V".
Related issues: none
```

```
Issue I-58
Location: Lines 57, 68, 628, 632
Section: I, VIII
Severity: Low
Priority: P3
Category: F AI-style wording
Original passage: "The natural hypothesis", "Our findings are mixed, and we report them as measured.", "a principled target", "The oracle is the more durable contribution", "a natural monitoring signal"
Problem: Evaluative adjectives and meta-commentary that add no information.
Why it matters: Mild generic voice.
Underlying pattern: P-10 (evaluative wording).
What to restore/check: Replace with the concrete property meant.
Related issues: none
```

```
Issue I-59
Location: Line 651
Section: Data Availability
Severity: Low
Priority: P2
Category: Completeness
Original passage: "The traffic matrices are public: Abilene and G\'{E}ANT from SNDlib"
Problem: The Nobel-Germany day also comes from SNDlib, and the semi-synthetic series comes from the released generator.
Why it matters: Incomplete provenance.
Underlying pattern: Omission.
What to restore/check: Name both.
Related issues: none
```

```
Issue I-60
Location: Table XI (generated/tab_scale.tex), main.log line 1026
Section: VII-F
Severity: Low
Priority: P3
Category: Layout
Original passage: Table XI
Problem: 6.7 pt overfull box.
Why it matters: The table runs into the margin.
Underlying pattern: Layout.
What to restore/check: Reduce column separation.
Related issues: none
```

```
Issue I-61
Location: Line 426
Section: VII-A
Severity: Low
Priority: P3
Category: Statistical language
Original passage: "The test uses only eight daily samples"
Problem: The eighth sample is a half day (7.5 test days).
Why it matters: Minor precision.
Underlying pattern: Omission.
What to restore/check: Mention the half day.
Related issues: none
```

```
Issue I-62
Location: Line 443
Section: VII-B
Severity: Low
Priority: P2
Category: Traceability
Original passage: "higher load makes the optimal sequence non-constant (\nobhlLiRAchg\ changes per day)"
Problem: The oracle's change rate is printed with LiRA's macro. The values are equal, but the sentence describes the oracle.
Why it matters: Breaks if LiRA changes.
Underlying pattern: P-08.
What to restore/check: Add an oracle macro.
Related issues: none
```

```
Issue I-63
Location: Line 447 (Table V caption)
Section: VII-B
Severity: Low
Priority: P3
Category: Caption precision
Original passage: "(Mean over Five Seeds)"
Problem: O* is deterministic.
Why it matters: Minor.
Underlying pattern: Caption scope.
What to restore/check: "for B4, B6 and LiRA".
Related issues: none
```

```
Issue I-64
Location: Line 268
Section: IV-C
Severity: Low
Priority: P3
Category: Methods detail
Original passage: "and its dwell time $\delta_{t-1}$ in intervals"
Problem: The dwell feature is capped at 288 intervals and scaled to [0, 1] (lira_policy.py, DWELL_CAP).
Why it matters: Reproduction detail.
Underlying pattern: Omission.
What to restore/check: Add the cap.
Related issues: I-44
```

```
Issue I-65
Location: Line 80
Section: II-B
Severity: Low
Priority: P3
Category: Clarity
Original passage: "because we could not run the original code"
Problem: The reason (code not public) is unstated.
Why it matters: Reads as a failed attempt.
Underlying pattern: Vague reason.
What to restore/check: State the reason.
Related issues: none
```

```
Issue I-66
Location: Reference [38]
Section: References
Severity: Low
Priority: P3
Category: Reference completeness
Original passage: "N. Chen, G. Goel, and A. Wierman, ... 2018. [Online]. Available: https://arxiv.org/abs/1803.10366"
Problem: The paper appeared at COLT 2018. The entry cites the preprint.
Why it matters: Reviewers prefer the archival version.
Underlying pattern: Reference metadata.
What to restore/check: Verify with tools/verify_refs.py before changing.
Related issues: none
```

```
Issue I-67
Location: Line 600
Section: VII-H
Severity: Low
Priority: P3
Category: Vague claim
Original passage: "The ranking is stable."
Problem: The ranking is not defined, and in fold 2 B6 (350.5) beats LiRA (351.1).
Why it matters: Vague.
Underlying pattern: P-10.
What to restore/check: State what holds in every fold.
Related issues: none
```

```
Issue I-68
Location: Line 454
Section: VII-B
Severity: Low
Priority: P3
Category: Figure language
Original passage: "LiRA and the oracle lie at the low-cost, low-change end of the front"
Problem: No front is computed. Fig. 5 shows sweep points.
Why it matters: Minor.
Underlying pattern: Loose term.
What to restore/check: "of the plotted points".
Related issues: none
```

---

## 7. Recurring Manuscript-Wide Patterns

| ID | Pattern | Frequency | Sections | Typical examples | Likely source | Repair strategy |
|----|---------|-----------|----------|------------------|---------------|-----------------|
| P-01 | Mechanism omitted from a headline result | 7 | Abstract, I, VII-A, VII-B, VIII, IX, X | I-02, I-03, I-14, I-15, I-25, I-49 | reasoning compression | Name the mechanism (constant policy, safety layer, round 0) next to every result it produces |
| P-02 | Selective comparison | 4 | Abstract, I, VII-B, VII-D | I-03, I-08, I-19 | reasoning compression | Report B2 and the static rule wherever LiRA is compared |
| P-03 | Hand-typed numbers | 11 typed, 3 wrong | I, VII | I-01, I-06, I-07 | mixed | Generate every number from the results |
| P-04 | Terminology collision | 4 terms | throughout | I-16, I-17, I-38, "flow-rule updates" vs "flow-modification messages" vs "forwarding entries" | language | One term per object |
| P-05 | Unsupported causal gloss | 6 | VII, VIII | I-23, I-26, I-27, I-07, I-39 | mixed | State the observation, or mark the explanation as untested |
| P-06 | Buried modelling assumption | 9 | III, IV, VI | I-04, I-33 to I-37, I-45, I-55 | structure | Collect the evaluation protocol in Section VI |
| P-07 | Overloaded paragraph | 7 | Abstract, VI, VII | I-18, I-40, I-41, I-42, lines 426, 565, 613 | structure | Split by function |
| P-08 | Traceability error | 6 | I, VII, VIII, IX | I-20, I-21, I-22, I-32, I-57, I-62 | structure | Labels and macros for every cross-reference and number |
| P-09 | Redundant summaries | 4 copies | Abstract, I, VIII, X | I-47 | AI rewrite or drafting | One full summary, then interpretation |
| P-10 | Claim-strength drift | 6 | across sections | I-13, I-30, I-46, I-48, I-58, I-67 | mixed | Use the Results wording everywhere |
| P-11 | Scope inflation in interpretation | 4 | VIII, X, VII-G | I-04, I-13, I-14, I-28 | reasoning | Limit claims to the tested settings |

---

## 8. AI-Rewrite Signature Analysis

| Signature | Level | Evidence |
|-----------|-------|----------|
| Generic academic phrasing | Mild | "The practical conclusion is that" (68), "A caveat applies to the whole study" (415) |
| Abstraction inflation | Mild | "sequence awareness" used for both hysteresis and LiRA (44, 626, 648) |
| Nominalization | Mild | "the benefit of sequence awareness depends on the traffic" (68) |
| Excessive hedging | Absent | claims are direct, sometimes too direct |
| Excessive certainty | Moderate | "is already optimal" (648), "The learner is useful" (628), "the layer is needed" (514) |
| Formulaic transitions | Mild | few "therefore", "thus" |
| Repetitive sentence structures | Moderate | number lists such as "B4 then makes ..., B6 makes ..., and LiRA makes ..." (443, 501, 514) |
| Artificial paragraph scaffolding | Mild | "Our findings are mixed, and we report them as measured." (68) |
| Over-compression | Moderate | abstract (279 words, 11 numbers), line 426 |
| Loss of causal explanation | Strong | the mechanisms behind the 97.7% and the high-load result are absent where the results are claimed |
| Loss of authorial voice | Mild | the skeptical voice survives |
| Terminology drift | Moderate | P-04 |
| Claim inflation | Moderate | I-01, I-13, I-14 |
| Scope inflation | Mild | I-28 |
| Qualification removal | Moderate | LiRA expansion and the realized-violation caveat of the first draft were dropped (Section 10) |
| Excessive symmetry | Moderate | Discussion "In the first case ... In the second case ..." (626) |
| Excessive parallelism | Mild | contribution bullets |
| Redundant summaries | Moderate | P-09 |
| Unnatural sophistication | Absent | plain vocabulary throughout |
| Generic significance statements | Mild | "The oracle is the more durable contribution" (628) |
| Loss of concrete actors | Mild | "sequence awareness removes" (648) |
| Excessive passive voice | Absent | |
| Unnecessary meta-language | Mild | "This paper tests that hypothesis rather than assuming it." (59), which does carry the paper's stance and should stay |

---

## 9. Authorial Voice Loss

The voice is intact at the sentence level. The text is direct, avoids filler, and states negative results plainly: "LiRA therefore offers no measurable advantage there" (68), "LiRA is no worse and no better" (415), "it does not validate the detectors" (587). Keep these.

What is weakened is the explanatory voice in the summary sections. The Results explain mechanisms (line 514, "the expert is nearly constant, so all variants that keep the safety layer reach the oracle cost"), but the abstract, discussion and conclusion speak of "LiRA", "sequence awareness" and "the learner" as agents that achieve results. The concrete actors (a constant classifier, a safety layer with same-interval information, a rolling-horizon optimiser) disappear in exactly the places readers read first.

---

## 10. Scientific Reasoning Loss

Only one earlier version exists on disk, the placeholder-results draft `paper/archive_placeholder_version/main_v1_placeholders.tex`. Its numbers were placeholders, so only its statements of method and scope can be compared.

1. **Realized violations.** The first draft said (v1 line 371): "The guarantee holds for the estimate $\hat{D}_t$. Violations with respect to the realized $D_t$ can still occur when traffic grows within an interval, and we report them as a metric." The current text says (line 299): "The guarantee holds for the estimate $\hat D_t$. In our evaluation the estimate equals the realized matrix, so violations occur only when no library member is feasible." The first version kept a boundary between estimate and reality and promised to measure what crosses it. The current version is honest about the protocol, but the boundary, and the measurement, are gone. Line 632 then states the deployment guarantee without it. This is the most consequential loss.

2. **The name.** v1 line 66: "We call the resulting framework LiRA (Lifetime- and Reconfiguration-Aware learning)." The current text never expands LiRA. The loss came with the title change.

3. **The oracle as lower bound.** v1 line 462: "We also report the offline oracle O$^\star$ as a lower bound." The current line 376 keeps the claim. It was harmless in a draft without non-library baselines. The current draft reports B1, B3 and B5, which are not bounded by O*. The claim survived a change of context that made it wrong.

---

## 11. Section-by-Section Diagnosis

**Title and Index Terms.** No writing problem. "When History Matters" matches the findings. Keep "negative results" in the index terms.

**Abstract (line 44).** Main writing problem: 279 words and 11 numbers. Structural problem: no sentence on the evaluation protocol. Main AI-rewrite problem: over-compression. Scientific risk: I-02, I-03, I-12. Repair: cut to 250 words, name the mechanisms, report B2, fix `\\,s`.

**I Introduction (lines 53-70).** Writing problem: the speed motivation (I-11). Structural problem: the findings paragraph repeats the abstract (I-47). Scientific risk: I-01. Repair: rewrite the motivation from measured times, correct the "only setting" claim, expand LiRA.

**II Related Work (lines 72-88).** Writing problem: one overgeneralisation (I-29). Structure is sound: each subsection ends with the difference to this paper. Repair: I-29 only.

**III Problem Formulation (lines 90-181).** Writing problem: notation collisions (I-44, I-51). Structural problem: the free start and the reference matrix for B are not stated (I-35, I-36). Scientific risk: low. The proposition and its proof are correct as stated (checked: the regret bound uses ⌈T/2⌉ ≥ ⌊T/2⌋ even intervals). Repair: I-35, I-36, I-51.

**IV Framework (lines 183-308).** Writing problem: the information assumption sits in IV-D (I-04). Scientific risk: Proposition 3 motivates a DAgger policy that is rarely deployed (I-15). Repair: move the assumption, report the round count.

**V Algorithms (lines 310-357).** Writing problem: Algorithm 1 label (I-10). Boundary problem: make-before-break (I-45). Repair: both.

**VI Setup (lines 359-409).** Writing problem: overloaded paragraphs (I-40, I-41). Precision problems: B4 fallback, O* scope, B0 routing, J definition (I-05, I-09, I-33, I-37). Repair: split paragraphs, add an "evaluation protocol" paragraph.

**VII Results (lines 411-622).** Writing problem: typed numbers (P-03) and terminology (I-16). Structural problem: the study-wide caveat is buried (I-42). Scientific risk: I-03, I-06, I-07, I-08, I-19. Repair: correct the claims, add B2 and the new experiments.

**VIII Discussion (lines 624-632).** Main problem: it repeats results and claims a benefit of the learner (I-14). Repair: interpret the oracle, the safety layer and the information assumption.

**IX Limitations (lines 634-644).** Mostly complete and honest. Missing: the information protocol, the DAgger count, the seed set of 897.4. Repair: add them.

**X Conclusion (line 648).** Problem: "already optimal" (I-13) and "sequence awareness removes" (I-02). Repair: use the Results wording.

**Data Availability and References.** I-59 and I-66 only.

---

## 12. Highest-Leverage Repair Plan

1. Restore the evaluation protocol: state in Section VI that every online method sees D_t, and report the D_{t-1} results (E16). This fixes I-04 and frames I-03.
2. Restore the mechanisms behind the two headline results in the abstract, introduction, results, discussion and conclusion: constant policy, safety layer, round 0, and the static rule (E17). This fixes I-02, I-03, I-14, I-15, I-25, I-49.
3. Restore the full comparison: B2 next to B6 everywhere (I-19), and the corrected "only setting" claim (I-01).
4. Correct the false or out-of-scope statements: I-05, I-06, I-07, I-08, I-09, I-10, I-13, I-23, I-24.
5. Make every number traceable: macros for the typed numbers and the cross-references (I-20, I-21, I-22, I-32, I-62).
6. Resolve the terminology collisions (I-16, I-17, I-38) and the notation (I-44, I-51).
7. Restore buried assumptions: J without penalty, wear-credit size, free start, reference matrix for B, B0 routing, make-before-break boundary (I-33 to I-37, I-45).
8. Shorten the abstract to 250 words (I-18) and remove the repeated summary from the discussion (I-47).
9. Split overloaded paragraphs (I-40 to I-42).
10. Polish: I-52 to I-68.

---

## 13. Global Editing Rules for This Manuscript

- Every number in the text comes from a macro generated from `paper/results/`.
- Name the mechanism next to every result: which policy, which layer, which information.
- Compare LiRA with B2, B6 and the static rule whenever a cost is compared.
- "Snapshot rule" means Eq. (7). "Snapshot classifier" means B4.
- "Configuration change" means c_{t-1} ≠ c_t. "Link transition" means one link changes power state.
- Say "lower bound" only with its scope.
- Do not attribute an effect to "sequence awareness" or "the learner" when a constant policy or the safety layer produces it.
- State whether a quantity is measured, computed or modeled.
- Keep the skeptical sentences that report negative results.

---

## 14. MASTER ISSUE INDEX

| ID | Lines | Section | Category | Severity | Priority | Pattern |
|---|---|---|---|---|---|---|
| I-01 | 68 | I | Evidence | Critical | P1 | P-03 |
| I-02 | 44, 68, 426, 626, 648 | Abstract, I, VII-A, VIII, X | Evidence, reasoning | Critical | P1 | P-01 |
| I-03 | 44, 68, 443, 628 | Abstract, I, VII-B, VIII | Evidence, reasoning | Critical | P1 | P-01, P-02 |
| I-04 | 168, 287, 299, 632 | III, IV-D, VIII | Precision, evidence | Critical | P1 | P-06, P-11 |
| I-05 | 376 | VI-B | Precision | High | P1 | P-06 |
| I-06 | 547 | VII-E | Evidence | High | P1 | P-03 |
| I-07 | 587 | VII-G | Evidence | High | P1 | P-03, P-05 |
| I-08 | 514 | VII-D | Evidence | High | P1 | P-02 |
| I-09 | 376 | VI-B | Precision | High | P1 | code drift |
| I-10 | 324 | V | Math-prose | High | P1 | notation |
| I-11 | 53, 565 | I, VII-F | Reasoning | High | P1 | consistency |
| I-12 | 44, 613 | Abstract, VII-I | Evidence, typesetting | High | P1 | P-06 |
| I-13 | 648 | X | Evidence, scope | High | P1 | P-10 |
| I-14 | 628 | VIII | Evidence | High | P1 | P-01, P-11 |
| I-15 | 63, 272, 283, 326-331 | I, IV-C, V | Evidence | High | P1 | P-01 |
| I-16 | 44, 613, 423, 426 | Abstract, VII | Terminology | High | P1 | P-04 |
| I-17 | 44, 68, 175-178, 426, 648 | throughout | Terminology | High | P2 | P-04 |
| I-18 | 44 | Abstract | Structure, compliance | High | P1 | P-07 |
| I-19 | 426, 443, 626 | VII, VIII | Evidence | High | P1 | P-02 |
| I-20 | 63 | I | Cross-reference | Medium | P1 | P-08 |
| I-21 | 630 | VIII | Cross-reference | Medium | P1 | P-08 |
| I-22 | 565 | VII-F | Consistency | Medium | P1 | P-08 |
| I-23 | 525 | VII-D | Mechanism | Medium | P1 | P-05 |
| I-24 | 415 | VII-A | Precision | Medium | P2 | compression |
| I-25 | 415 | VII-A | Precision | Medium | P1 | P-01 |
| I-26 | 501 | VII-C | Mechanism | Medium | P2 | P-05 |
| I-27 | 626 | VIII | Mechanism | Medium | P2 | P-05 |
| I-28 | 587 | VII-G | Scope | Medium | P2 | P-11 |
| I-29 | 84 | II-C | Literature | Medium | P2 | generalisation |
| I-30 | 44, 68, 428, 437 | Abstract, I, VII-A | Consistency | Medium | P2 | P-10 |
| I-31 | 525, 529 | VII-D | Evidence | Medium | P2 | P-06 |
| I-32 | 514, 643 | VII-D, IX | Consistency | Medium | P1 | P-08 |
| I-33 | 380 | VI-C | Precision | Medium | P1 | P-06 |
| I-34 | 380 | VI-C | Precision | Medium | P2 | P-06 |
| I-35 | 160-164 | III-E | Math-prose | Medium | P2 | P-06 |
| I-36 | 140 | III-C | Precision | Medium | P2 | P-06 |
| I-37 | 376 | VI-B | Precision | Medium | P2 | P-06 |
| I-38 | 613 | VII-I | Terminology | Medium | P2 | P-04 |
| I-39 | 565 | VII-F | Unsupported | Medium | P2 | P-05 |
| I-40 | 363 | VI-A | Structure | Medium | P2 | P-07 |
| I-41 | 380 | VI-C | Structure | Medium | P2 | P-07 |
| I-42 | 415 | VII-A | Structure | Medium | P2 | order |
| I-43 | 44, 63 | Abstract, I | Orientation | Medium | P2 | qualification removal |
| I-44 | 104-116, 133, 268, 404 | III, IV, Table III | Notation | Medium | P2 | notation |
| I-45 | 312 | V | Boundary | Medium | P2 | P-06 |
| I-46 | 428 | VII-A | Evidence | Medium | P2 | P-10 |
| I-47 | 44, 68, 626, 648 | four sections | Repetition | Medium | P2 | P-09 |
| I-48 | 380 | VI-C | Statistics | Medium | P2 | P-10 |
| I-49 | 643 | IX | Precision | Medium | P2 | P-01 |
| I-50 | 227, 319-321 | IV-A, V | Math-prose | Medium | P2 | P-08 |
| I-51 | 125, 196-197, 289 | III, Fig. 1, IV | Orientation | Low | P2 | notation |
| I-52 | 637 | IX | Precision | Low | P3 | loose |
| I-53 | 363 | VI-A | Assumption | Low | P2 | P-06 |
| I-54 | 468 | Fig. 4 | Figure | Low | P3 | loose |
| I-55 | 617 | Table XIV | Measured vs computed | Low | P2 | P-06 |
| I-56 | 565 | VII-F | Formatting | Low | P3 | format |
| I-57 | 628 | VIII | Cross-reference | Low | P2 | P-08 |
| I-58 | 57, 68, 628, 632 | I, VIII | AI wording | Low | P3 | P-10 |
| I-59 | 651 | Data | Completeness | Low | P2 | omission |
| I-60 | Table XI | VII-F | Layout | Low | P3 | layout |
| I-61 | 426 | VII-A | Statistics | Low | P3 | omission |
| I-62 | 443 | VII-B | Traceability | Low | P2 | P-08 |
| I-63 | 447 | Table V | Caption | Low | P3 | scope |
| I-64 | 268 | IV-C | Methods | Low | P3 | omission |
| I-65 | 80 | II-B | Clarity | Low | P3 | vague |
| I-66 | Ref. [38] | References | Metadata | Low | P3 | reference |
| I-67 | 600 | VII-H | Vague | Low | P3 | P-10 |
| I-68 | 454 | VII-B | Figure | Low | P3 | loose |

---

## 15. COMPLETENESS CHECK

- Every section, line 1 to 657, was read. Every `\input` (1 macro file, 13 tables) was read in source and in the PDF.
- All 10 numbered equations, 4 propositions, 2 algorithms, 14 tables and 6 figures were checked against prose and data.
- The reference list was read in the PDF. Reference verification itself was not repeated (the project uses `tools/verify_refs.py`).
- Each pattern was searched across the whole file after its first example (term counts for "snapshot rule", "transition", "LiRA" expansion, typed numbers).
- Writing problems and scientific problems are separated by category.
- No passage was rewritten in this report.
- No earlier version was described that was not read.

---

## 16. Remediation Status (same day)

The repairs were applied to `paper/main.tex` and `paper/tools/make_paper_assets.py`. The pre-audit text is kept as `paper/tools/archive_oneoff/main_v2_duplicate_of_main.tex`, so every change can be diffed. Three experiments were added to support the repairs: E15 (per-interval lower bound), E16 (decisions on D_{t-1}) and E17 (static configuration with LiRA's fallback).

| ID | Status | Repair |
|---|---|---|
| I-01 | Fixed | Introduction now says LiRA's learned component beats the static rule in one scenario (stress) and that B2 is cheaper still there |
| I-02 | Fixed | Abstract, introduction, results, discussion and conclusion state that the Nobel base policy is constant (holds one configuration in 2,159 of 2,160 intervals) and that three non-learning rules match it |
| I-03 | Fixed | Section VII-B explains the exact match (near-constant expert plus a safety layer that sees D_t), cites B2 (882.2) and the static rule, and E16 shows the violations under D_{t-1} |
| I-04 | Fixed | New Section VI-C on the information protocol. Line 299 and the deployment paragraph now restrict the guarantee to accurate estimates and cite E16 |
| I-05 | Fixed | O* is "a lower bound for every controller restricted to the library", and Section VII-G bounds the rest |
| I-06 | Fixed | Generated values (B4 1.117, LiRA 1.0024, others 1.000) |
| I-07 | Fixed | Per-topology statement with generated switch rates (0.41 to 0.82 per day on Nobel) |
| I-08 | Fixed | Lag-feature removal reported as lowering the cost, "small and of mixed sign" |
| I-09 | Fixed | B4's energy-only fallback described |
| I-10 | Fixed | Algorithm 1 pairs s_t with c*_t |
| I-11 | Fixed | Introduction cites the measured solver times, Section VII-F says speed alone does not require a learned controller here |
| I-12 | Fixed | Emulation text separates the modeled 1 s wake-up from the measured 99 ms. The abstract no longer contains the broken macro call |
| I-13 | Fixed | "within 0.014% of the oracle" |
| I-14 | Fixed | Discussion limits LiRA's contribution to the stress scenario |
| I-15 | Fixed | Round-zero count in Sections IV-C, VII and IX |
| I-16 | Fixed | "Configuration change" throughout the emulation text, the intro bullet and the Table XVI caption |
| I-17 | Fixed | "Snapshot rule" now only names Eq. (7). The abstract and conclusion say "snapshot classifier" |
| I-18 | Fixed | Abstract has 249 words |
| I-19 | Fixed | B2 in Table V and in every Nobel comparison |
| I-20 | Fixed | Drift subsection labelled `sec:res-drift` and cited |
| I-21 | Fixed | DP run time (3.6 s for 48,108 intervals) reported in Section VII-F |
| I-22 | Fixed | Text uses the 60-matrix median (3.5 s) |
| I-23 | Fixed | Candidate pool of 51 configurations |
| I-24 | Fixed | GÉANT and Abilene separated |
| I-25 | Fixed | "the configuration that was optimal on the training period" |
| I-26, I-27 | Fixed | The random-forest explanation is marked as untested, and the discussion names the classifiers |
| I-28 | Fixed | "The injected shifts did not change the optimal configuration" |
| I-29 | Fixed | "None of these methods prices the change from one configuration to the next" |
| I-30 | Fixed | One threshold family from the histogram: no change above 0.41%, 99% below 0.1% |
| I-31 | Fixed | Table VIII reports test coverage |
| I-32 | Fixed | Ablation caption and text name seeds 0 to 2. The limitations quote the five-seed value |
| I-33 | Fixed | Section VI-D defines the reported J |
| I-34 | Fixed | Wear credit 0.040 against energy savings of 0.025 to 0.060 per sleeping link |
| I-35 | Fixed | Free start and gap rule stated in Section VI-D |
| I-36 | Fixed | B measured on the mean training matrix |
| I-37 | Fixed | B0 routing stated |
| I-38 | Fixed | "the path that carries the largest share of its demand" |
| I-39 | Fixed | Removed the sub-second claim |
| I-40, I-41 | Fixed | Dataset and metrics paragraphs split |
| I-42 | Fixed | Study-wide caveat moved to a results preamble |
| I-43 | Fixed | LiRA expanded in the contribution list |
| I-44 | Partly fixed | Dwell time is now ℓ, and Table III names the Page-Hinkley parameters in words. E still denotes both the link set and the energy, which is common usage |
| I-45 | Fixed | Make-before-break limited to the emulation |
| I-46 | Fixed | "shows that", seed 0 stated, clearer thresholds |
| I-47 | Partly fixed | The discussion now interprets instead of repeating. Abstract and introduction keep the summary by design |
| I-48 | Fixed | "with those of B4, B6, and B7" |
| I-49 | Fixed | GÉANT policy described as constant in output |
| I-50 | Fixed | Algorithm 1 names the validation traces |
| I-51 | Fixed | MLU expanded at Eq. (1), D̂_t in Table I, "traffic" instead of "TM" in Fig. 1 |
| I-52 to I-65, I-67, I-68 | Fixed | As listed in the issue entries |
| I-66 | Not changed | Reference [38] keeps the preprint. Changing it needs `tools/verify_refs.py` with network access |

New text was checked against the data in the same way as the original (all new numbers are macros). Two claims written during the repair were corrected before the final build: "the same sequence" under D_{t-1} (only the cost and change rate are the same) and "fallback switches" in the drift paragraph (the data give configuration changes).

Build: `latexmk` reports no errors, no warnings and no overfull boxes. The paper grew from 13 to 14 pages because of Sections VI-C, VII-G and VII-I and Tables XII and XIV. Check the TGCN page limit before submission.

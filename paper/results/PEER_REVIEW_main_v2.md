# Targeted peer review of `paper/main_v2.tex` (IEEE TGCN): claim-evidence alignment and statistical validity

Classification: empirical methods paper with a learned controller. Severity: Standard. Scope: ranked issues only.

## Ranked issues

| # | Severity | Issue | Location | Evidence in the paper | Action taken |
|---|---|---|---|---|---|
| 1 | Critical | **The headline method is not exercised in half of the experiments.** In 30 of 60 LiRA runs (all of Abilene, Nobel base and high-dynamic-power) the trained policy is a constant classifier, because the oracle uses one configuration in training. Ablations and model-choice results are therefore trivially identical in those settings. | Sec. VII-A to VII-C, Tables IV, VII, VI | `ConstantModel` count from `E1_main/*_info.json` | Disclosed in Sec. VII-A and in the limitations, with the count |
| 2 | Critical | **The only positive result rests on semi-synthetic, i.i.d.-noise traffic and 8 test days.** Smallest attainable two-sided Wilcoxon p-value with 8 pairs is 0.0078, and the Holm correction covers only 3 comparisons per setting, not the 12 settings. | Sec. VI-A, VII-A, Table V | `stats_wilcoxon_holm.csv` | Added the multiplicity caveat and the power limit to Sec. VII-A and Table V caption |
| 3 | High | **The reported reductions $Y$, $Z$ depend on the chosen B4 classifier.** With XGBoost B4 flaps 12.8 times per day, but with a random forest 0.5, so a 97.7% reduction is relative to a flapping baseline of our own choosing. | Abstract, Sec. VII-A, VII-C, Table VI | `E13_model_choice` | Abstract and Sec. VII-A now state the random-forest figure |
| 4 | High | **Abstract overstates equality**: "matches them and the oracle exactly" while B4 costs 0.014% more on Abilene (7227.7 vs 7226.7). | Abstract | Table IV | Reworded to "within 0.02% of the oracle cost" |
| 5 | High | **The cost $J$ includes a modeled wear credit that dominates it** (sleeping links earn a negative term), so $J$ is not an energy figure and its absolute values are not comparable to energy. | Sec. III-D, Tables IV, V | $J$ below always-on energy | Added a note on the composition of $J$ in Sec. V-C |
| 6 | High | **Drift is listed as a contribution but not validated.** The detectors fire without shifts and the threshold sits at the grid maximum on two traces. | Sec. I contributions, Sec. VII-G | Table XII | Contribution bullet reworded as a component, not a result |
| 7 | Medium | **Zero-width confidence intervals** for deterministic or constant outcomes read as high precision. | Tables IV, VII | `0.00$\pm$0.00` entries | Caption states that identical seeds give zero width because the policy is constant |
| 8 | Medium | **Emulation covers B4 only for transitions** and routes each demand on one dominant path, whereas the simulator splits traffic. LiRA appears as a single, transition-free run. | Sec. VII-I | Setup of the emulation | Limitation already stated; kept |
| 9 | Medium | **B2 is not the multi-period MILP** and no deep reinforcement learning baseline exists; novelty over imitation of an exact DP is modest. | Sec. VI-B, IX | Text | Kept as stated limitation |
| 10 | Low | Power and wear parameters are assumed; the sensitivity study varies only $\chi$ and $\alpha$, not port power. | Sec. VI-D, VII-E | Table III | Kept as stated limitation |

## Meta-review (area chair view)

Recommendation in current form: **major revision**. The exact oracle, the validation against a MILP, the explicit negative result on real traces, and the transparent reporting are real strengths. The main risks are that (i) the learned component is trivial in many settings, (ii) the positive evidence depends on a synthetic series and a short test window, and (iii) the improvement over a tuned hysteresis rule is not significant. The reframing around "when history matters" is the correct response to these risks. A stronger paper would add real traces with temporal structure and measured router power.

Estimated acceptance probability: about 20% in the current form and about 40% if a second noisy real trace and a full multi-period MILP baseline were added.

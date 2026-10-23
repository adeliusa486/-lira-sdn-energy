# Literature Review & Reference Verification

**Verification status (2026-10-18):** 51/51 entries in `references_candidate.bib` passed `tools/verify_refs.py` (DOI checked on Crossref, title fuzzy match ≥ 0.9, year ±1; arXiv IDs checked on arXiv; URL-only entries returned HTTP 200). Report: `results/ref_verification.csv`. Clean file: `references_verified.bib`.

**What "verified" means here:** the paper exists and the metadata is correct. It does **not** mean we have checked what the paper says. Before citing a paper for a specific claim (a number, a method detail), open it and confirm. Mark that in column "Content checked" below.

Fixes made during verification:
- `chiaraviglio2015lifetime`: the first DOI was wrong (pointed to a cognitive-radio paper). Corrected to `10.1109/MCOM.2015.7105670`.
- `vasic2010eate`: wrong DOI corrected to `10.1145/1791314.1791341`.
- OpenFlow, XGBoost, Mininet: Crossref stores only the main title. Accepted.
- Lu 2019 (TKDE) and SNDlib (Networks): Crossref year is the online-first year (2018 / 2009). Use the issue year in the paper.

---

## A. Green networking foundations
| Key | Contribution | Use in paper | Content checked |
|---|---|---|---|
| gupta2003greening | First proposal to sleep network interfaces | Intro motivation | ☐ |
| bianzino2012survey, bolla2011energy | Surveys of green networking | Related work, background | ☐ |
| chiaraviglio2012minimizing | ISP energy minimisation ILP, power model, heuristics | Formulation, power model, B1 | ☐ |
| heller2010elastictree | Data-centre link/switch sleeping (ElasticTree) | B5 heuristic | ☐ |
| vasic2010eate | Online energy-aware TE (EATe) | Related work (online methods) | ☐ |
| mahadevan2009power, restrepo2009energy | Measured device power profiles | Power constants (Phase 3) | ☐ |

## B. Energy efficiency in SDN
| kreutz2015sdn, mckeown2008openflow | SDN / OpenFlow background | Intro | ☐ |
| assefa2019survey | Survey of SDN energy methods and optimisation models | Related work | ☐ |
| assefa2018mersdn | ML predicts parameters for energy-aware routing heuristic | Related work (ML+green SDN) | ☐ |
| maaloul2018carrier | ILP + heuristics for switching off nodes/links in SDN carrier Ethernet | Related work, ILP baseline design | ☐ |
| frohlich2021rl | RL (random neural network) for energy-aware routing in an SDN controller | Related work (RL) | ☐ |

## C. Direct competitors — snapshot ML replacing the solver ⚠ most important
| Key | Notes |
|---|---|
| gomezdelahiz2025noms | NOMS 2025. ML-driven configuration for energy-efficient SDN; per public abstract, maps traffic matrices to near-optimal precomputed configurations, reports energy savings up to 53% and big speedups over heuristics. |
| gomezdelahiz2026tgcn | IEEE TGCN 2026. Scalable follow-up framework by the same group. |

**Action in Phase 1:** read both in full. Write down: topologies and datasets used (likely overlapping Abilene/GÉANT/Nobel-Germany), the classifier, how configurations are generated, the label definition, energy model, reported accuracy and savings. These define baseline B4 in Phase 6, and our numbers must be comparable. If the user is an author of these papers, cite them as prior work and present this paper as the sequential extension. Double-blind rules apply: cite in the third person.

## D. Network update / reconfiguration cost
| reitblatt2012abstractions | Consistent network updates | Why reconfiguration is costly | ☐ |
| jin2014dionysus | Update scheduling, update time and congestion | R(c,c') definition, emulation | ☐ |
| bonetto2013multiperiod | **Multi-period power-aware topology design with reconfiguration costs** (optical) — closest optimisation precedent | B2 design; must be clearly separated from our learning contribution | ☐ |

## E. Device lifetime / wear
| chiaraviglio2015lifetime | Sleep modes can shorten or lengthen lifetime: temperature vs thermal-cycling model | Wear model W (Phase 3) | ☐ |
| chiaraviglio2014impact | Lifetime model for energy-efficient techniques | Wear model parameters | ☐ |
| wiatr2016lifetime | Lifetime-aware provisioning in green optical networks | Related work: lifetime-aware optimisation | ☐ |

## F. Online decisions with switching costs
| lin2013rightsizing | Data-centre right-sizing with switching cost (lazy capacity provisioning) | Theory link, a baseline idea | ☐ |
| borodin1992mts | Metrical task systems | Framing the sequential problem | ☐ |
| chen2018obd | Smoothed online convex optimisation | Related theory | ☐ |

## G. ML for traffic engineering
| valadarsky2017learning, rusek2020routenet | Learning to route, GNN network model | Related work | ☐ |
| xu2023teal, perry2023dote, abuzaid2021ncflow, narayanan2021pop | Fast/learned TE solvers (2021–2023) | Show the "replace the solver" trend, which is snapshot-based | ☐ |
| mnih2015dqn, schulman2017ppo | DRL | B8 | ☐ |
| ross2011dagger | DAgger imitation learning | LiRA training | ☐ |
| chen2016xgboost, ke2017lightgbm, breiman2001rf, hochreiter1997lstm | Model families | Models | ☐ |
| deb2002nsga2 | NSGA-II | GA baseline, library | ☐ |

## H. Drift, datasets, tools
| gama2014drift, lu2019drift, bifet2007adwin, page1954cusum | Drift surveys and detectors | Phase 8 | ☐ |
| orlowski2010sndlib, uhlig2006geant, zhang2003tomogravity, knight2011zoo | Datasets | Phase 2 | ☐ |
| lantz2010mininet, ryu, gurobi, huangfu2018highs | Tools | Setup | ☐ |

---

## I. Research-gap matrix (fill as papers are read)

| Work | ML / fast decisions | Energy | Reconfig. cost | Device wear | Sequential / history | Drift adaptation | Real TM traces |
|---|---|---|---|---|---|---|---|
| chiaraviglio2012minimizing | ✗ | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| bonetto2013multiperiod | ✗ (MILP/heur.) | ✓ | ✓ | ✗ | ✓ | ✗ | ✓ |
| chiaraviglio2015lifetime | ✗ | ✓ | ✗ | ✓ | – | ✗ | – |
| vasic2010eate | ✗ (online heuristic) | ✓ | partial | ✗ | partial | ✗ | ? |
| assefa2018mersdn | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ? |
| frohlich2021rl | ✓ (RL) | ✓ | ✗ | ✗ | ✓ | ✗ | ✗ |
| gomezdelahiz2025noms / 2026tgcn | ✓ | ✓ | ? (check) | ? (check) | ? (check) | ? (check) | ? (check) |
| xu2023teal, perry2023dote | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ |
| **LiRA (ours)** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

The "?" cells for the direct competitors **must** be filled from the full text before writing the paper. If they already include any of these, the novelty claim must be narrowed.

## J. Still to find (Phase 1, target ≥ 15 papers from 2021–2026 in total)
Search terms: "DRL link sleeping SDN", "multi-agent energy routing", "GNN energy-aware routing", "energy-aware traffic engineering 2024", "switching cost online network configuration", "concept drift network traffic classification", "sleep mode lifetime 2020", "hybrid SDN energy". Places to search: IEEE Xplore (TGCN, TNSM, JSAC, INFOCOM, NOMS, CNSM), ACM DL (SIGCOMM, CoNEXT, e-Energy), Elsevier (Computer Networks, JNCA). Add each to the bib and re-run the checker.

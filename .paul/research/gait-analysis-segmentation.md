# Research: Gait-Analysis Segmentation Techniques Transferable to 1D Swim Encoder Signals

**Date:** 2026-07-10
**Agent:** general-purpose (web/literature research)
**Scope constraints baked in:**
- Single 1D encoder channel (position → velocity → acceleration @ 100 Hz). No IMU array/gyro/force plate.
- 25-yard single lap: dive/push-off → underwater glide+kick → breakout → steady stroking → wall touch. No flip turns.
- Two equally-weighted problems: **(A)** 5-phase boundary segmentation, **(B)** individual stroke-cycle segmentation.
- **Latency budget: full analysis ≤10 s, possibly on a mobile phone.** Compute cost is a first-class axis.
- **Labels:** a small hand-labeled set (~5–30 swims) is feasible. Few-label methods favored; hundreds-of-labels methods marginal.
- Anchor on the 1D signal; note pose/video fusion only as future opportunities.

---

## Executive summary

- **(A) and (B) want different tool classes.** (A) phase boundaries = a *change-point / regime-segmentation* problem plus a *fixed-order state model*. (B) stroke cycles = a *periodicity / repeated-motif / template* problem. Don't force one method to do both.
- **Shortlist for (A):** (1) deterministic **Finite State Machine / rule cascade** over the phase physics (dive spike → decaying-velocity glide → breakout → periodic stroking → decel-to-zero); (2) a **change-point detector** — PELT (offline, exact, near-linear) or FLOSS (matrix-profile semantic segmentation) as an unsupervised cross-check; (3) a small **left-to-right HMM** encoding the fixed ordering. All <1 s, few-to-zero labels.
- **Shortlist for (B):** (1) **subsequence-DTW template matching** (Barth et al. 2015 msDTW — 97–98% F1 for stride segmentation with one averaged template); (2) **matrix-profile motif discovery / FLOSS** for label-free cycle boundaries; (3) the **existing trough detector reframed as ZUPT-style "reset at glide minima."** DTW = the few-labels win; matrix profile = the unsupervised win.
- **Autocorrelation gives cadence cheaply and robustly** and should feed a *refractory / min-stroke-time* constraint into whatever cycle segmenter is chosen — cheapest single robustness upgrade.
- **The current CWT ridge is a known-weak periodicity estimator** in exactly the documented way (mode-mixing, ridge-railing at the analysis-band edge — matches the 120-SPM ceiling railing). Fixes: detrend-before-transform (already done) and EEMD-over-EMD; but autocorrelation/matrix-profile cadence is simpler and faster than further wavelet tuning.
- **Deep learning (TCN/BiLSTM/U-Net)** hits 92–96% F1 but is the wrong first move: needs hundreds of labeled cycles; inference <1 s but label+train+mobile-infra cost is disproportionate for a single-channel, fixed-structure problem classical methods already solve. Phase-2 option only.
- **Validate with the gait-standard event protocol:** tolerance-window TP/FP matching (±250 ms common), precision/recall/F1 for boundary events, and signed timing-error distribution (mean ± SD, MAE ms) on true positives. Maps cleanly onto the 5–30 labeled swims.

---

## 1. Rule / threshold / zero-crossing & peak-valley detection
**How:** detect events directly — velocity peaks (mid-stroke), troughs (glide minima), accel zero-crossings (peak-velocity instants), threshold crossings — gated by *min stroke time + refractory periods*. Classic single-accelerometer gait-event baseline.
**Lit:** baseline in Barth 2015 & Zrenner 2018; refractory constraint from autocorrelation average stride time (Moe-Nilssen & Helbostad 2004).
**Maps to:** (B) directly (troughs = boundaries, peaks = arm-pull markers); (A) partially (dive spike, wall-touch zero).
**Pros:** ~zero compute (O(n)), interpretable, no training, already the trough backup. **Cons:** threshold-fragile across swimmers/speeds; breaststroke arm-kick dip creates spurious minima; no global-optimal boundary set.
**Compute:** <10 ms. **Labels:** none (few help tune thresholds).

## 2. Autocorrelation / dominant-period methods
**How:** unbiased autocorrelation peaks at step/stride period; peak heights = regularity/symmetry. Gives cadence + average cycle length, not individual events.
**Lit:** Moe-Nilssen & Helbostad 2004 (canonical); Tura et al. 2012 (how few cycles needed — relevant: only ~8–15 cycles per 25yd swim).
**Maps to:** (B) — supplies stroke rate + *expected cycle length* that constrains every other segmenter. Weak for (A) but periodicity onset = breakout cue.
**Pros:** extremely cheap (one FFT-based autocorr), robust, no labels, degrades gracefully. **Cons:** average period not individual boundaries; assumes local stationarity.
**Compute:** <50 ms. **Labels:** none.

## 3. Change-point / segmentation algorithms → Problem (A)
**How:** detect indices where mean/variance/spectral regime changes. Most direct formal match to phase boundaries.
**Methods & lit:**
- **PELT** — Killick, Fearnhead & Eckley 2012 (JASA). Exact global optimum, near-linear. **Best offline choice for (A)** — one pass, penalty (BIC/MBIC) tuned to ~4 boundaries.
- **Binary Segmentation** — greedy, faster, approximate.
- **BOCPD** — Adams & MacKay 2007. Online run-length posterior; good if live in-swim feedback ever wanted.
- **CUSUM** — cheap online single-shift (dive-onset trigger, wall-touch stop).
- **Sliding-window / Bottom-Up / SWAB** — Keogh et al. 2001/2004; PLA knots = candidate boundaries.
**Maps to:** (A) — 5 phases = 4 regime changes with distinct signatures. **Pros:** PELT exact, unsupervised, fast; phase count roughly known → easy penalty tuning. **Cons:** naive Gaussian cost may over-split the *periodic* stroking phase — combine with max-K or spectral cost.
**Compute:** PELT ≪1 s at ~2500 samples; BOCPD/CUSUM trivial. **Labels:** none.

## 4. Template matching & DTW → Problem (B), the few-labels winner
**How:** build 1+ cycle templates from labeled cycles; slide *subsequence-DTW*; warping-cost minima mark instances. Multi-dim variant aligns channels jointly.
**Lit:**
- **Barth et al. 2015**, *Multi-Dimensional Subsequence DTW on inertial data*, Sensors 15(3):6419. **Flagship: one msDTW template → F1 97–98%**, beating peak detection by up to 15 F1. Strongest direct analog to (B).
- **Zrenner et al. 2018**, Sensors 18(12):4194 — method-comparison context.
- **Roth et al. 2021** (J. NeuroEng. Rehabil.) — HMM slightly beat DTW (92.1% F1) on 146k free-living strides. Key caveat: DTW excellent, not always top.
**Maps to:** (B) — canonical "split into comparable cycles," precisely the small-label case (template needs only a handful of clean cycles). **Pros:** few labels; robust to speed/amplitude warping (good for fatigue-slowed late cycles); interpretable. **Cons:** needs a *clean* template (breaststroke arm+kick double-bump makes design non-trivial); O(n·m) per template (still cheap here, scales with template count).
**Compute:** ~tens of ms/template. **Labels:** low (5–15 marked cycles). **→ Recommended first prototype for (B).**

## 5. Hidden Markov Models / state-space → Problem (A), natural fixed-order fit
**How:** *left-to-right* HMM (states advance, never revisit); Viterbi assigns each sample to a phase. Fixed dive→glide→breakout→stroke→touch order = textbook left-right HMM.
**Lit:**
- **Mannini & Sabatini 2012**, *HMM gait segmentation, foot-mounted gyroscope*, Gait & Posture 36(4):657 — four-state left-right HMM on a *single 1D channel*. Closest structural analog.
- **Taborri et al. 2014** (Sensors 14(9):16212) — HMM phase segmentation; documents subject-specific-training cost.
- **Taborri et al. 2015** (Sensors 15(9):24514) — inter-subject (generalized) HMM training viable → may not need per-swimmer labels.
- **Roth et al. 2021** — hierarchical HMM, 92.1% F1, beat DTW.
**Maps to:** (A) primarily; (B) with per-cycle sub-states. **Pros:** encodes ordering as hard prior (can't output glide-before-dive); Viterbi O(n·states²) trivial; trainable on few labeled sequences given tiny state space. **Cons:** emission-model choice matters (Gaussian on velocity+accel a reasonable start); needs *some* labels; more moving parts than FSM for same ordering.
**Compute:** train seconds; inference <100 ms. **Labels:** small (5–30 swims viable for 5-state).

## 6. Finite State Machine / rule-based partitioning → Problem (A), cheapest deterministic option
**How:** hand-code guarded transitions: `PUSH_OFF` (accel > spike) → `GLIDE` (high & monotone-decaying velocity, no periodicity) → `BREAKOUT` (periodicity onset) → `STROKING` (sustained periodic) → `FINISH` (velocity → 0 near lap end).
**Lit:** FSM real-time gait phase detection in exoskeletons (ACM HRI 2025, 10.1145/3776734.3794551); threshold-as-FSM equivalence + jerk-threshold events standard in prosthesis/exoskeleton control (review arXiv:2310.09735).
**Maps to:** (A) — 5 phases = textbook fixed-sequence FSM; no turns/repeats so it never loops. **Pros:** deterministic, ~zero compute, fully interpretable/debuggable, zero training, transitions expressible in known phase physics. **Cons:** manual threshold tuning, brittle at phase edges (breakout is the fuzzy one); no confidence. **Best paired with change-point/HMM cross-check for the breakout boundary.**
**Compute:** negligible. **Labels:** none (few to tune). **→ Recommended first prototype for (A).**

## 7. Matrix Profile family → both (A) and (B)
**How:** for every subsequence, distance to its nearest neighbor. **FLOSS/FLUSS** = semantic segmentation via arc-crossing counts (few crossings = regime boundary). **Motif discovery** = most-repeated subsequence (= stroke cycle). **Discords** = anomalies (dive/touch). **SPRING** = streaming subsequence match.
**Lit:** Gharghabi et al. 2017 (Matrix Profile VIII, IEEE ICDM) + 2019 extension (DMKD 33:96–130). Impl: `stumpy` (Python), `tsmp` (R), aeon `FLUSSSegmenter`.
**Maps to:** (A) via FLOSS arc-counting (label-free cross-check on PELT); (B) via motif discovery (repeated stroke shape = top motif, occurrences = cycles, no template). **Pros:** domain-agnostic, near parameter-free (just subseq length ≈ cycle length from autocorr), unsupervised. **Cons:** naive O(n²) but STOMP/SCRIMP/`stumpy` → milliseconds at ~2500 samples; FLOSS assumes segments internally self-similar (fine for stroking, less for one-shot dive/glide).
**Compute:** ms with `stumpy`. **Labels:** none. **→ Strong unsupervised second prototype for both.**

## 8. Wavelet / CWT ridge & EMD/EEMD
**How:** CWT ridge traces instantaneous stroke frequency (current method). EMD → intrinsic mode functions; peak-detect the stroke-rhythm IMF. EEMD adds noise ensembles to fix EMD mode-mixing.
**Lit:** EEMD gait-series extraction from accelerometry (Chin. Phys. B 19(5):058701, 2010) — **EEMD beats EMD under intermittent noise, prevents mode mixing**. EMD+Hilbert walking-transition detection (PMC10002180). Current ridge-railing / near-zero-node issues are documented failure modes; mitigations = detrend-before-transform (already done) + analysis band that doesn't clip true rate (the 120-SPM railing = band-clipping).
**Maps to:** (B). **Pros:** adaptive, no template. **Cons:** CWT ridge fiddly (band selection, railing, near-zero nodes — matches placeholder experience); EMD mode-mixing; EEMD fixes but slower than autocorr/matrix-profile for the same cadence answer. **→ Don't invest further in CWT tuning as primary; use autocorr/matrix-profile motif for cadence/cycles; keep EEMD in reserve.**
**Compute:** heaviest classical option (EEMD ensemble ×N sifting) but ≪10 s; EEMD the one to watch on mobile. **Labels:** none.

## 9. Zero-Velocity Update (ZUPT) / stance-phase analog → robust anchors for (B) + glide detection
**How:** foot-mounted INS resets at momentary zero-velocity (stance) intervals. Swim analog: inter-stroke velocity minima (glide) = zero-velocity-like anchors; underwater glide = a sustained high-then-decaying interval to bracket.
**Lit:** Skog, Händel, Nilsson & Rantakokko 2010, *Evaluation of Zero-Velocity Detectors* (IEEE TIM) — SHOE detector, likelihood-ratio tests, adaptive/double-threshold variants (better minima detection than raw threshold).
**Maps to:** (B) — reframes trough backup as principled "reset at inter-stroke minima" with windowed energy/variance statistics; (A) partially — glide = high-velocity low-oscillation interval before stroking. **Pros:** cheap, robust, physical, no labels; anchors also stabilize DTW/matrix-profile boundaries. **Cons:** breaststroke mid-cycle arm-kick dip can masquerade as between-stroke minimum — min-stroke-time refractory (§2) is the guard.
**Compute:** negligible. **Labels:** none. **→ Adopt Skog-style windowed-statistic minima to upgrade the trough segmenter.**

## 10. Deep-learning sequence segmentation (TCN, U-Net/1D-CNN, LSTM/BiLSTM)
**How:** network outputs per-sample phase labels / event probabilities; peak-pick the probability track.
**Lit:** Kidziński et al. 2019 (LSTM gait events, ~10–13 ms error, beat Zeni heuristic); Filtjens et al. 2021 (TCN events during turning); hybrid CNN-BiLSTM (PMC9655831); TCN F1 up to 95.9%/93.8% (arXiv 2203.00503); DL stride-segmentation data-quantity study (RG 397125126).
**Maps to:** (A) and (B). **Pros:** highest ceiling; handles arm+kick ambiguity once trained; inference <1 s. **Cons (decisive):** needs *hundreds* of labeled cycles (5–30 swims marginal-to-insufficient); adds train + model-versioning + on-device runtime (TFLite/CoreML); buys little over classical on a single-channel fixed-structure problem. **Verdict: not first move.** Revisit if classical plateaus and cycles accumulate (possibly auto-labeled by the classical pipeline).
**Compute:** train offline (min–hrs, GPU helps); inference <1 s mobile. **Labels:** high — the disqualifier now.

---

## Comparison tables
Ratings ★–★★★★★. Compute: more stars = cheaper/faster. Labels: more stars = fewer needed.

### Problem (A) — phase segmentation
| Method | Accuracy | Compute | Few-label | Impl. effort (low=good) | Robustness |
|---|---|---|---|---|---|
| **FSM / rule cascade** | ★★★☆ | ★★★★★ | ★★★★★ | Low | ★★★ (breakout edge) |
| **PELT change-point** | ★★★★ | ★★★★★ | ★★★★★ | Low | ★★★★ |
| **FLOSS matrix-profile** | ★★★★ | ★★★★☆ | ★★★★★ | Low–Med | ★★★★ |
| **Left-right HMM** | ★★★★★ | ★★★★☆ | ★★★★ | Med | ★★★★ |
| **BOCPD (online)** | ★★★☆ | ★★★★☆ | ★★★★★ | Med | ★★★ |
| **Deep TCN/U-Net** | ★★★★★ | ★★★☆ | ★ | High | ★★★★ |

### Problem (B) — stroke-cycle segmentation
| Method | Accuracy | Compute | Few-label | Impl. effort | Robustness |
|---|---|---|---|---|---|
| **Subsequence-DTW template** | ★★★★★ | ★★★★☆ | ★★★★ | Med | ★★★★ |
| **Matrix-profile motif** | ★★★★ | ★★★★☆ | ★★★★★ | Low–Med | ★★★★ |
| **Trough / ZUPT anchors** | ★★★☆ | ★★★★★ | ★★★★★ | Low | ★★★ (arm-kick dip) |
| **Autocorrelation (cadence only)** | ★★★ | ★★★★★ | ★★★★★ | Low | ★★★★★ |
| **CWT ridge (current)** | ★★★ | ★★★☆ | ★★★★★ | Med (fiddly) | ★★ (railing) |
| **EEMD peak-pick** | ★★★☆ | ★★★ | ★★★★★ | Med | ★★★ |
| **Deep seq. model** | ★★★★★ | ★★★★ | ★ | High | ★★★★ |

---

## Validation methodology (map to the 5–30 labeled swims)
1. **Ground truth:** hand-mark, per swim, 4 phase boundaries (A) + each stroke start (B).
2. **Tolerance-window matching:** detected event = TP if within tolerance of a labeled event, else FP; unmatched labels = FN. Gait standard ~±250 ms (500 ms centered); report 2–3 tolerances (±100/±250 ms).
3. **Detection metrics:** precision/recall/F1 for boundaries (A) and stroke starts (B) — as in Barth 2015, HMM/DTW comparisons, TCN papers.
4. **Timing-error distribution:** TP-only signed error (mean ± SD) + MAE ms (Kidziński-style; DL ceiling ~10–13 ms, coarser is fine).
5. **Count metrics:** stroke-count error, phase-count error per swim.
6. **Cross-validation:** leave-one-swim-out (or leave-one-swimmer-out); report per-swim spread, not just pooled mean.
7. **Baseline to beat:** current CWT/trough segmenter, same protocol — direct comparability like the gait peak-vs-DTW-vs-HMM papers.

## Cycle time-normalization (reusable for B)
Resample each cycle to **0–100% cycle (~101 points, linear/spline)** so different-duration cycles are directly comparable and ensemble-averageable. Universal gait convention; validates per-cycle comparison + fatigue-drift across slowing late-lap cycles. Sources: instrumented-gait practice (Physiopedia); Helwig et al. 2011 (temporal alignment beyond linear — DTW-based alignment if linear warp distorts sub-phase timing). CV/variance-ratio across normalized cycles = fatigue/consistency metric.

## Swimming-specific literature (what transfers)
- **Macro-Micro IMU swim analysis** (Sensors 2021, PMC7841373) — segments **push-off → glide → stroke prep → swimming → turn**, essentially the exact phase list; confirms the phase problem is well-posed and *decaying velocity + periodicity onset* are the discriminative cues (→ FSM/HMM features).
- **Stroke phases via 3D wrist trajectory** (Sensors 2019, PMC6683631) — per-cycle sub-labeling; relevant for pose/video fusion.
- **Le Sage et al. 2011** (Sports Engineering) — real-time on-device stroke-rate extraction (CPM error 0.07–0.34, SD <2 CPM); proof (B) cadence is solvable on constrained hardware.
- **Ganzevles / Mooney** velocity-profiling + IMU-swim reviews (Sensors 2015) — periodic velocity oscillation = one-per-stroke, the exploitable structure underpinning the bump-per-cycle model.
- **Delgado-Gonzalo 2016 / Brunner 2019** (ISWC 2019) — lap/style segmentation via DL; reinforces the "needs data" caveat.
- **What transfers most:** the macro-micro phase list validates Problem-A structure/cues; the DTW/HMM stride-segmentation line transfers directly to Problem B (velocity bump = stride analog). IMU-swim papers use richer multi-axis signals — the single 1D encoder channel is *cleaner and lower-noise* for periodicity, which favors simpler classical methods over their DL pipelines.

---

## Recommended experimental plan
All comfortably inside ≤10 s, buildable from ~5–30 labels.

**Problem (A):**
1. **FSM / rule cascade (first).** Encode dive-spike, decaying-glide, periodicity-onset (breakout), sustained-periodic, decel-to-zero as ordered guarded transitions. <10 ms, zero training, debuggable vs labeled boundaries. Cheapest, most interpretable, phase physics known.
2. **PELT change-point as independent unsupervised check.** Penalty → ~4 boundaries; agreement with FSM = confidence, disagreement (expect breakout edge) = the hard boundary to instrument. Add **FLOSS** as a third parameter-light opinion.
3. **Left-right HMM only if 1+2 leave breakout noisy.** 5-state Gaussian on (velocity, accel); trainable on labeled swims; Viterbi enforces ordering.

**Problem (B):**
1. **Subsequence-DTW template (first).** Barth 2015 method, proven 97–98% F1, best use of the small label budget — one averaged breaststroke template (careful arm+kick double-bump), slide msDTW, cost minima.
2. **Matrix-profile motif discovery as unsupervised cross-check.** `stumpy`, subseq length from autocorr cadence; top motif = stroke shape, occurrences = cycles. Milliseconds, no labels.
3. **Upgrade trough backup to Skog-style windowed-minima (ZUPT) + autocorrelation refractory gate.** Cheap robustness floor / defensible fallback boundary set.

Run all candidates through one tolerance-window F1 + timing-error protocol vs the current CWT/trough baseline. Retire CWT-ridge tuning unless EEMD beats the autocorr/matrix-profile cadence head-to-head (literature suggests not worth the mobile compute).

**Bottom line:** For a single 1D channel with fixed phase order, tiny label budget, ≤10 s mobile — classical wins decisively. Build **FSM (A)** + **subsequence-DTW template (B)** first, cross-check with **matrix-profile (FLOSS for A, motif for B)**, keep **ZUPT trough** as the robust floor, hold **HMM** and **deep learning** in reserve.

---

## Sources
**DTW / template (B):** [Barth 2015 msDTW — MDPI](https://www.mdpi.com/1424-8220/15/3/6419) · [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4435165/) · [Zrenner 2018 — Sensors](https://www.mdpi.com/1424-8220/18/12/4194) · [Roth 2021 HMM vs DTW — JNER](https://jneuroengrehab.biomedcentral.com/articles/10.1186/s12984-021-00883-7) · [Optimal warping-path selection 2024 — PubMed](https://pubmed.ncbi.nlm.nih.gov/38433858/)
**HMM (A):** [Mannini & Sabatini 2012 — PubMed](https://pubmed.ncbi.nlm.nih.gov/22255307/) · [Taborri 2014 — Sensors](https://www.mdpi.com/1424-8220/14/9/16212/htm) · [Taborri 2015 inter-subject — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC4610555/) · [Mannini & Sabatini online HMM — PubMed](https://pubmed.ncbi.nlm.nih.gov/25014927/)
**Change-point (A):** [Killick PELT 2012 — RG PDF](https://www.researchgate.net/publication/48180788_Optimal_Detection_of_Changepoints_With_a_Linear_Computational_Cost) · [ruptures PELT docs](https://centre-borelli.github.io/ruptures-docs/user-guide/detection/pelt/) · [Adams & MacKay 2007 BOCPD — RG](https://www.researchgate.net/publication/1771282_Bayesian_Online_Changepoint_Detection) · [Keogh SWAB survey — UCI PDF](https://ics.uci.edu/~pazzani/Publications/survey.pdf)
**Matrix profile (A+B):** [Gharghabi FLOSS/FLUSS — Springer DMKD](https://link.springer.com/article/10.1007/s10618-018-0589-3) · [RG PDF](https://www.researchgate.net/publication/321894569_Matrix_Profile_VIII_Domain_Agnostic_Online_Semantic_Segmentation_at_Superhuman_Performance_Levels) · [aeon FLUSSSegmenter](https://www.aeon-toolkit.org/en/latest/api_reference/auto_generated/aeon.segmentation.FLUSSSegmenter.html)
**FSM / rule (A):** [FSM gait phase in exoskeletons — ACM HRI 2025](https://dl.acm.org/doi/10.1145/3776734.3794551) · [Gait-phase algorithms review — arXiv 2310.09735](https://arxiv.org/pdf/2310.09735)
**Autocorrelation (B):** [Moe-Nilssen & Helbostad 2004 — ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0021929003002331) · [Tura 2012 — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC3305516/)
**ZUPT (B):** [Skog 2010 zero-velocity detectors — Wiley ch.](https://onlinelibrary.wiley.com/doi/10.1002/9781119699910.ch5) · [double-threshold ZUPT — RG](https://www.researchgate.net/publication/350537083)
**Wavelet / EMD (B):** [EEMD gait-series 2010 — IOPscience](https://iopscience.iop.org/article/10.1088/1674-1056/19/5/058701) · [EMD+Hilbert transitions — PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC10002180/)
**Deep learning:** [TCN/CNN gait events — arXiv 2503.00794](https://arxiv.org/pdf/2503.00794) · [CNN-BiLSTM — PMC9655831](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9655831/) · [DL stride-segmentation data study — RG](https://www.researchgate.net/publication/397125126)
**Validation & normalization:** [Marker-based GED protocol — Frontiers 2022](https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2022.868928/full) · [IMU GED benchmark — RG](https://www.researchgate.net/publication/394362913) · [Helwig 2011 temporal alignment — RG](https://www.researchgate.net/publication/47298545_Methods_to_temporally_align_gait_cycle_data)
**Swimming-specific:** [Macro-Micro IMU swim — PMC7841373](https://pmc.ncbi.nlm.nih.gov/articles/PMC7841373/) · [Stroke phases 3D wrist — PMC6683631](https://pmc.ncbi.nlm.nih.gov/articles/PMC6683631/) · [IMU-swim systematic review — RG](https://www.researchgate.net/publication/267642711) · [Style recognition + lap counting ISWC 2019 — ACM](https://dl.acm.org/doi/10.1145/3341163.3347719)

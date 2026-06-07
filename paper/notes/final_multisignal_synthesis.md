# Final Multi-Signal Synthesis

**Date:** 2026-06-07
**Type:** Synthesis of locked evidence (not a new analysis stage).

## Timing and scope

- This note was created **after** the Stage 3–7 outputs were locked.
- It was created **after** the Stage 4 oracle-gap band assignment, the Stage 5
  calibration threshold assignment, the Stage 6 feature–label stability band
  assignment, and the Stage 7 positive-control unit clarification.
- This note does **not** run any experiment and does **not** rerun Stages 3–7.
- This note does **not** change source code, docs, results, thresholds, or prior notes.
- It is a synthesis of locked evidence, **not** a new analysis stage.
- It does **not** introduce a binary Stage 7 detected/not-detected flag.

This note separates three layers throughout: (1) **raw diagnostic evidence**,
(2) **locked decision rules** (docs/02, docs/03 §9), and (3) **cautious final
interpretation**.

## Locked evidence summary

### Stage 3 — Primary performance

- AUROC is **stable** under the locked threshold (drop `< 0.02`): the largest
  in-domain → transfer AUROC drop is `-0.0006` (i.e. transfer AUROC is not lower).
- Mean AUROC by context/model (raw evidence): in-domain hgb 0.652 / logreg 0.636 /
  rf 0.612; temporal 0.659 / 0.653 / 0.622; cross-segment 0.653 / 0.641 / 0.613.
- Temporal AUROC is **slightly higher** than in-domain for each model; this is
  **not** interpreted as "improvement" or as proof of "no shift."
- Temporal Brier is worse (≈0.175 temporal vs ≈0.128 in-domain) despite stable
  ranking, which is consistent with a calibration / probability-scale interpretation
  (the temporal test base rate, ≈0.233, differs from in-domain ≈0.156), not a
  ranking collapse.
- Performance alone does **not** indicate severe degradation.

### Stage 4 — Oracle-gap diagnostic

- Temporal `oracle_gap_auroc` is **small** across all model/seeds, range ≈
  **0.0083–0.0164** (all `< 0.02`).
- Cross-segment `oracle_gap_auroc` is **small or negative**, range ≈
  **−0.0073 to +0.0061**; no gap reaches the large band (`>= 0.05`).
- Under the locked oracle-gap diagnostic this argues against **large detectable**
  relationship drift in the tested transfers.
- **Caveat:** the cross-segment oracle/source training samples are asymmetric (the
  oracle trains on the smaller target segment, credit_card), so small or negative
  cross-segment gaps must **not** be overread as evidence of "no drift."

### Stage 5 — Calibration diagnostic

- **Temporal:** all rows are `calibration_poor` and diagnostic recalibration
  `fixes_most` (raw ECE10 ≈ 0.071–0.081 reduced to ≈ 0.005–0.029). This supports a
  **calibration / base-rate / prior / probability-scale shift** interpretation.
- The recalibration is **diagnostic-only / oracle-style**: it uses the observed
  target/test default rate and is **not** a deployable production correction.
- **Cross-segment:** logreg/hgb are not poor by the raw thresholds; RF is poor via
  slope/intercept.
- **RF slope/intercept "poor" also appears in-domain** (in-domain RF slope ≈ 0.58,
  intercept ≈ −0.61), so RF calibration slope/intercept must **not** be treated as
  drift-specific evidence.
- **Rule D does not apply.** Rule D requires calibration to remain poor **after**
  recalibration **together with** a large oracle gap. Here temporal recalibration
  fixes most of the ECE **and** oracle gaps are small. The calibration evidence is
  therefore closer to a **Rule B-style** prior/base-rate/probability-scale shift
  than to a Rule D base-rate-plus-deeper-relationship-drift pattern.

### Stage 6 — Feature–label stability diagnostic

- Locked numeric metric (mean `delta_abs_auc_strength`, ratio vs noise baseline):
  - **temporal numeric = moderate / borderline** (≈ **2.49×**);
  - **cross-segment numeric = low** (≈ **1.75×**).
- Locked categorical metric (weighted-mean `delta_abs_risk_difference`, ratio vs
  noise baseline):
  - **temporal categorical = low** (≈ **1.43×**);
  - **cross-segment categorical = low** (≈ **0.86×**).
- **[Descriptive only, not the locked band metric]** the temporal Spearman ratio is
  **high** (≈ **4.83×**) and is reported transparently as a sensitivity caveat; it
  was **not** the locked band metric and is not used to assign a band.
- Stage 6 is **marginal / univariate** (per-feature associations) and does **not**
  prove full multivariate `P(y | x)` stability.

### Stage 7 — Positive-control sensitivity

- Stage 7 is **not** collapsed into a binary detected/not-detected flag (the
  unit/aggregation and row-alignment were not locked).
- Positive-control `oracle_gap_auroc` increases **monotonically** weak → medium →
  strong for **every** model/seed curve.
- **[Descriptive only] same-model/seed margin** (strong vs same-model/seed real
  temporal gap + 0.05):
  - **RF strong exceeds** the threshold across RF seeds (strong ≈ 0.079–0.081 vs
    thresholds ≈ 0.065–0.066);
  - **logreg strong remains below** (≈ 0.042 vs ≈ 0.058);
  - **hgb strong is close but below** (≈ 0.058 vs ≈ 0.060).
- **[Descriptive only] aggregate-mean margin** (mean synthetic gap vs mean real
  temporal gap):
  - **strong** exceeds by ≈ **+0.055** (`>= 0.05`);
  - **weak** (≈ +0.006) and **medium** (≈ +0.021) do **not**.
- These are **descriptive sensitivity readings, not locked decision rules.**
- Stage 7 supports sensitivity to **larger** injected relationship shifts
  (especially strong / RF) but does **not** demonstrate guaranteed sensitivity to
  weak/subtle drift; sensitivity is **model- and level-dependent**.

## Multi-signal interpretation

- The real-data pattern does **not** show strong evidence of **large detectable**
  relationship drift under the locked diagnostics.
- The dominant real-data pattern is: (1) stable ranking / AUROC; (2) small oracle
  gaps; (3) temporal calibration / base-rate / prior / probability-scale issues that
  are largely correctable in this diagnostic setting; (4) mostly low-to-moderate
  marginal feature–label instability.
- This does **not** prove the **absence** of relationship drift. Smaller or subtler
  drift may remain **below the diagnostic's sensitivity boundary**, which is
  strongest for larger injected shifts and is model-dependent.

## Decision-rule proximity

- **Rule E** (diagnostic insufficient) is **too strong**: Stage 7 shows a monotone
  response and large-shift sensitivity (especially RF strong and the descriptive
  aggregate-strong reading), so this is not a complete diagnostic failure.
- **Rule G** in its pure form (a fully working positive control) is **too strong**:
  Stage 7 sensitivity is model- and level-dependent and the aggregation unit was not
  locked.
- **Rule D does not apply**: its required pattern (calibration remaining poor after
  diagnostic recalibration **and** a large oracle gap) is not present — temporal
  recalibration fixes most of the ECE and oracle gaps are small.
- The **real-data side** has strong calibration / base-rate-shift evidence
  consistent with a **Rule B-style** prior/base-rate/probability-scale
  interpretation, but the final interpretation is constrained by the Stage 7
  sensitivity limits.
- **The overall pattern is closest to Rule F, with no single binary Stage 7
  detection flag introduced**: the diagnostic appears sensitive to large injected
  relationship shifts but may miss subtle drift, so real-data null / weak-drift
  findings must be interpreted cautiously.

## Final thesis

Across the locked diagnostics, the real transfer settings do not show strong
evidence of large detectable relationship drift. The dominant real-data pattern is
small oracle gaps plus calibration / probability-scale issues and mostly
low-to-moderate marginal feature–label instability. The positive-control
sensitivity curve indicates that the diagnostic responds to larger injected
relationship shifts, especially at strong perturbation levels and for RF, but
sensitivity is model- and level-dependent; therefore smaller or subtler drift cannot
be ruled out.

## Claims not made

- We do **not** claim that no relationship drift exists.
- We do **not** claim the positive control passed as a single binary fact.
- We do **not** claim all diagnostics are stable.
- We do **not** claim calibration proves drift.
- We do **not** claim RF slope/intercept proves drift (it also appears in-domain).
- We do **not** ignore the Stage 6 Spearman sensitivity (reported transparently).
- We do **not** claim weak/medium positive-control behavior invalidates the whole
  diagnostic.
- We do **not** claim the cross-segment small/negative oracle gap proves no drift.
- We do **not** claim that temporal AUROC being slightly higher means there is no
  shift.
- We do **not** claim that the diagnostic recalibration is a deployable production
  fix (it is oracle-style / diagnostic-only).
- We do **not** claim that Rule D applies.

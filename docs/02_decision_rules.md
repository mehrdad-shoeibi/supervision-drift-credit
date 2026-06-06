# 02 — Decision Rules

**Status: LOCKED before any official experiment.**

These decision rules are pre-registered and committed before any official run.
They map the combined pattern of results (primary + diagnostics + positive
control) onto a pre-specified conclusion. They are not edited after seeing
official results.

The thresholds used to operationalize "stable", "small", "low", "poor", and
"large" are recorded in `docs/03_data_dictionary_and_assumptions.md` and are
also locked before execution. The noise baselines from Stage 6 and the positive
control from Stage 7 provide the reference scale for these judgments.

---

## Decision rules

**A) Stable everywhere.**
If AUROC is stable, oracle gap is small, and feature–label instability is low:
conclude that the observed shift **does not provide evidence of strong P(y|x)
supervision drift** in this credit setting.

**B) Calibration-only, fixed by base-rate correction.**
If raw calibration is poor but intercept / base-rate recalibration fixes most of
it: conclude that the main deployment risk is **prior / base-rate shift**
affecting probability calibration, **not ranking failure**.

**C) Localized relationship drift, ranking preserved.**
If oracle gap is large or feature–label instability is high **while AUROC
remains stable**: conclude that **localized relationship drift may exist, but
ranking is preserved** by redundant stable predictors.

**D) Prior shift plus deeper drift.**
If raw calibration remains poor **after** intercept / base-rate recalibration
**and** oracle gap is large: conclude that **both prior / base-rate shift and
deeper P(y|x) / relationship drift may be present**.

**E) Diagnostic insufficient (positive control fails).**
If the synthetic positive control is **not detected at medium or strong**
perturbation levels: conclude that the **diagnostic framework is insufficient**
and **do not make strong drift-detection claims**.

**F) Diagnostic detects only large shifts.**
If the synthetic positive control is detected **only at strong** perturbation but
not at weak/medium: conclude that the diagnostic can detect **large** relationship
shifts but **may miss subtle drift**; real-data null findings must be interpreted
**cautiously**.

**G) Stable real data with a working positive control.**
If all real-data diagnostics are stable **and** the synthetic positive control
works: conclude that this credit-risk case shows **limited evidence of harmful
supervision drift under the locked tests**, and the contribution is **the
diagnostic protocol and the negative / contrastive evidence**, not a failure
claim.

---

## Notes on use

- Rules E and F gate the interpretive strength of every other rule: a null
  real-data finding (Rule A/G) is only credible if the positive control
  demonstrates the diagnostic is sensitive (Stage 7).
- Rules are evaluated against the locked primary tests (`2013 -> 2016` temporal;
  largest -> second-largest `purpose` cross-segment). Exploratory sensitivity
  analyses, if any, do not trigger these rules.
- Where multiple rules could apply, all applicable conclusions are reported; the
  rules are diagnostic descriptors, not mutually exclusive verdicts.

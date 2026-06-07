# Stage 5 Calibration Method Audit v1

## Scope note

This is a read-only implementation audit prepared before polishing Methods v2. It does
not add analysis, change results, thresholds, or decision rules, and it does not edit
Methods v1 or the manuscript. It does not create tables or figures, and it does not run
experiments or compute new calibration values. It draws on the locked notes and on
read-only inspection of the relevant source files. Its purpose is to verify the exact
implementation of (1) the diagnostic recalibration, (2) the calibration slope and
intercept estimation, and (3) the ECE computation, so that the Methods v2 wording is
implementation-accurate.

## Files inspected

Locked notes and docs (read only):
- paper/notes/methods_section_draft_v1.md
- paper/notes/stage5_calibration_threshold_assignment.md
- paper/notes/method_protocol_rationale_v1.md
- paper/notes/method_open_caveats_audit_v1.md
- paper/notes/results_section_draft_v2.md, discussion_section_draft_v2.md,
  final_multisignal_synthesis.md, results_discussion_outline.md (context)
- docs/00_design_lock.md, docs/01_analysis_protocol.md, docs/02_decision_rules.md,
  docs/03_data_dictionary_and_assumptions.md

Source/code (read only, not executed):
- src/05_calibration_diagnostic.py: the Stage 5 driver. It computes ECE at three bin
  counts (near lines 29 to 31), calls the calibration intercept and slope routine (near
  line 19), sets the target rate to the observed test default rate (near line 39), and
  calls the recalibration routine (near line 47).
- src/utils.py: the shared implementations: ece_equal_frequency (near line 449),
  calibration_intercept_slope (near line 471), base_rate_recalibrate (near line 501),
  and the logit and clip helpers used by these routines.

No binary artifacts, parquet files, pickle or joblib files, or full CSV result files
were inspected, and no script or notebook was executed.

## Current Methods v1 wording under audit

1. Calibration slope and intercept wording: "Calibration is characterized separately
   using the expected calibration error (ECE) under equal-frequency bins, together with
   a calibration intercept and slope estimated by regressing the outcome on the model
   logit."

2. Diagnostic recalibration wording: "It also applies a diagnostic recalibration, an
   intercept and base-rate adjustment fitted using the observed target-context default
   rate."

This audit checks whether these two descriptions are implementation-accurate.

## ECE implementation

ECE is computed by ece_equal_frequency (src/utils.py, near line 449). The function sorts
predictions, splits the rank order into bins of approximately equal count using an
array split, and sums the count-weighted absolute difference between mean predicted
probability and observed outcome rate per bin. The bins are therefore equal-frequency
(quantile) bins, not equal-width. The Stage 5 driver computes ECE at 5, 10, and 20 bins
(src/05_calibration_diagnostic.py, near lines 29 to 31); the locked thresholds and band
notes use the 10-bin ECE. This is confirmed by implementation code. The Methods v1
wording, "expected calibration error (ECE) under equal-frequency bins," is accurate.

## Calibration slope/intercept implementation

The calibration intercept and slope are estimated by calibration_intercept_slope
(src/utils.py, near line 471). The routine forms the model logit z = logit(p) and fits a
logistic regression of the binary outcome on z, using
LogisticRegression(C=1e6, max_iter=5000, solver="lbfgs"); the fitted intercept and the
single coefficient on z are reported as the calibration intercept and slope. The large C
value means minimal regularization, so this is effectively an unregularized logistic
calibration of the outcome on the model logit. Predicted probabilities are clipped to
the range (1e-6, 1 - 1e-6) before the logit is taken, via the logit and clip helpers.
A single-class target is handled by returning missing values with a warning, and fit
failures are caught and recorded.

The Methods v1 wording, "a calibration intercept and slope estimated by regressing the
outcome on the model logit," is accurate. For Methods v2, the description can optionally
be made slightly more precise by stating that the regression is a logistic regression of
the outcome on the model logit with minimal regularization, and that probabilities are
clipped before the logit transformation.

## Diagnostic recalibration implementation

The diagnostic recalibration is base_rate_recalibrate (src/utils.py, near line 501). It
applies a single additive shift on the logit scale, logit(p_recal) = logit(p_clipped) +
delta, and selects the scalar delta by monotone bisection so that the mean recalibrated
probability equals the target rate. The target rate is the observed target-context
default rate, set in the Stage 5 driver as the mean of the test labels
(src/05_calibration_diagnostic.py, near line 39) and passed to the routine (near line
47). This is an intercept-only adjustment on the logit scale; it does not fit a slope,
and it is not isotonic. It uses target-context label information (the observed default
rate), so it is oracle-style and not deployable.

The Methods v1 phrase, "an intercept and base-rate adjustment fitted using the observed
target-context default rate," is accurate. For precision, Methods v2 can state that the
recalibration is a single intercept shift on the logit scale chosen so that the mean
predicted probability matches the observed target-context default rate, which makes
explicit that no slope term is fitted. The audit notes that the calibration slope and
intercept measurement (a two-parameter logistic fit) and the diagnostic recalibration
(a one-parameter intercept shift) are distinct procedures, and both are described
correctly in Methods v1.

## Recommended Methods v2 wording

For Section 3 (metrics): "Calibration is characterized using the expected calibration
error (ECE) under equal-frequency (quantile) bins, together with a calibration intercept
and slope obtained from a logistic regression of the outcome on the model logit with
minimal regularization; predicted probabilities are clipped to a small interval before
the logit transformation."

For Section 4.3 (calibration diagnostic): "The diagnostic recalibration applies a single
intercept shift on the logit scale, chosen so that the mean predicted probability matches
the observed target-context default rate. Because it uses target-context label
information, it is an oracle-style counterfactual and is not deployable, and it is used
only to separate a probability-scale or base-rate explanation from deeper relationship
change."

These wordings keep the recalibration described as oracle-style and not deployable, and
keep the calibration and oracle-gap layers complementary rather than statistically
independent. They avoid over-specific claims beyond what the implementation supports.

## Implications for Methods v2

Methods v1 is implementation-accurate in both Section 3 and Section 4.3; the recommended
changes are wording-only refinements for precision (naming the logistic calibration fit,
noting the probability clipping, and stating that the recalibration is a single
intercept shift on the logit scale). The change is wording-only and does not affect
interpretation. No analysis rerun is needed, and no result value changes are needed.

## Recommended next step

- Review this audit.
- Then create Methods section draft v2 using methods_section_draft_v1.md,
  stage5_calibration_method_audit_v1.md, method_open_caveats_audit_v1.md, and
  method_protocol_rationale_v1.md.
- Methods v2 should apply the precise calibration wording above, verify the calibration
  description, and reduce any unnecessary overlap with the Discussion.

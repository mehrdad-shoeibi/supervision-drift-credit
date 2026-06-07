# Method Open Caveats Audit v1

## Scope note

This is a read-only audit note prepared before drafting the Methods section or the
Figure 1 specification. It does not add analysis, change results, thresholds, or
decision rules, and it does not edit the manuscript. It does not create tables or
figures, and it does not run experiments. It draws on the locked notes and on
read-only inspection of the relevant source files. Its purpose is to clarify three
methodological caveats: (1) the positive-control feature-choice rationale; (2) the
oracle-gap capacity caveat; and (3) the complementarity, rather than statistical
independence, of the calibration and oracle-gap diagnostics. Where a statement is
inferential rather than directly locked, it is labeled as methodological framing.

## Files inspected

Locked notes and docs (read only):
- paper/notes/method_protocol_rationale_v1.md
- paper/notes/results_section_draft_v2.md
- paper/notes/discussion_section_draft_v2.md
- paper/notes/final_multisignal_synthesis.md
- paper/notes/results_discussion_outline.md
- paper/notes/table_figure_plan_v1.md
- paper/notes/stage4_oracle_gap_band_assignment.md
- paper/notes/stage5_calibration_threshold_assignment.md
- paper/notes/stage6_feature_label_stability_band_assignment.md
- paper/notes/stage7_positive_control_unit_clarification.md
- docs/02_decision_rules.md
- docs/03_data_dictionary_and_assumptions.md (section 9 thresholds)
- docs/01_analysis_protocol.md (Stage 7 section, via read-only grep)

Source/code (read only, not executed):
- src/07_positive_control_synthetic_drift.py: the Stage 7 implementation. It is
  implementation code. It names dti_n and fico_n, defines the perturbation direction,
  and states that the real outcome label is not overwritten.

Draft tables (context only):
- paper/tables/table1_transfer_settings_draft.csv
- paper/tables/table2_primary_performance_draft.csv
- paper/tables/table3_diagnostic_summary_draft.csv

No binary artifacts, parquet files, pickle or joblib files, or large CSV result files
were inspected, and no script or notebook was executed.

## Positive-control feature-choice audit

1. Use of dti_n and fico_n is confirmed. The implementation defines
   `PERTURB_FEATURES = ["dti_n", "fico_n"]` (src/07_positive_control_synthetic_drift.py,
   near line 25), and the analysis protocol states that the perturbation uses dti_n and
   fico_n if present (docs/01_analysis_protocol.md, Stage 7 section, near line 200).

2. The choice of these two features is not explicitly justified as a ranking of
   predictive strength. The code documents a directional, credit-risk-interpretable
   construction, "risk = z(dti_n) - z(fico_n)" with the comment that higher DTI and
   lower FICO imply higher risk (src/07_positive_control_synthetic_drift.py, near line
   42). This supports an interpretability and directional-plausibility rationale, but
   it is not a statement that these are the strongest predictors.

3. The inspected materials do not call dti_n and fico_n the strongest predictors. They
   should not be described that way in the manuscript.

4. The features can reasonably be described as interpretable numeric credit-risk
   covariates, because the implementation treats them as numeric inputs and assigns
   them a credit-risk directional meaning (debt-to-income and a credit-score proxy).

5. Preservation of the observed outcome labels is confirmed in the implementation. The
   module docstring states that the real Default column is never overwritten and that
   the synthetic labels live in a separate column
   (src/07_positive_control_synthetic_drift.py, near line 10), and the main loop keeps
   the feature matrix fixed while holding the synthetic label in a separate column
   (near line 129). The positive control is therefore synthetic and injected, with the
   real labels preserved.

6. Safe Methods wording: the locked materials confirm use of dti_n and fico_n, but do
   not justify them as strongest predictors. The safe Methods wording is to describe
   them as interpretable numeric credit-risk covariates used for a transparent
   positive-control perturbation, with the real outcome labels preserved and the
   synthetic labels held separately, without claiming they are the strongest
   predictors. If a stronger feature-choice rationale is desired, it must be verified
   against the locked positive-control implementation before manuscript integration.

## Oracle-gap capacity caveat

The oracle-gap diagnostic is useful because it asks whether training directly on the
target context recovers ranking performance that is not available to the source-trained
model, when both are evaluated on the same held-out target fold. This makes the oracle
gap a performance-based probe for multivariate relationship change rather than a probe
of any single marginal association.

The diagnostic assumes, however, that the chosen model class can express
target-learnable relationship differences. If both the source-trained and the
target-trained models are capacity-limited, feature-limited, or noise-limited, a small
oracle gap can reflect a shared performance ceiling rather than genuine relationship
stability. Moderate absolute predictive performance, together with proxy labels that
carry noise, should therefore be read as a sensitivity boundary for this layer rather
than as a guarantee that the layer would surface any conditional shift that exists.

Accordingly, small oracle gaps should be interpreted as limited evidence for large
detectable multivariate relationship drift under the chosen models and settings; they
do not prove absence of conditional shift. Suggested Methods wording: "The oracle-gap
diagnostic assumes that the model class can express target-learnable relationship
differences. Moderate absolute predictive performance and noisy proxy labels bound the
sensitivity of this layer; therefore small oracle gaps limit evidence for large
detectable multivariate relationship drift under the chosen models and settings, but do
not prove absence of conditional shift."

## Calibration and oracle-gap complementarity caveat

The calibration diagnostic and the oracle-gap diagnostic answer different questions, but
they are not statistically independent evidence streams. The calibration diagnostic
asks whether probability-scale, prior, or base-rate mismatch explains the observed
probability error, while the oracle-gap diagnostic asks whether target-context training
improves ranking relative to the source-trained model.

Because both layers are sensitive to prior, base-rate, and label-shift structure, a
pattern that is mostly base-rate or label shift can produce calibration changes while
leaving the oracle ranking advantage small. The two readings can therefore move
together for a shared underlying reason, which means a Rule B-style interpretation
should be described as convergent or complementary evidence rather than as independent
confirmation.

The manuscript should avoid describing these layers as independent evidence, or as
statistically independent tests, unless that wording is carefully qualified. Suggested
Methods wording: "The diagnostic layers provide complementary perspectives rather than
statistically independent tests. In particular, calibration diagnostics and oracle-gap
diagnostics can both be affected by base-rate or label-shift structure; their joint
interpretation is therefore framed as a multi-signal synthesis rather than independent
confirmation."

## Method wording recommendations

- Describe dti_n and fico_n only as supported by the locked materials.
- Do not call dti_n and fico_n strongest predictors; the inspected materials do not
  support that wording.
- Where the rationale is not an explicit predictive-strength ranking, use the
  conservative description "interpretable numeric credit-risk covariates," and note the
  directional, credit-risk-interpretable construction.
- State that the observed outcome labels are preserved and that the synthetic labels are
  held separately, as confirmed by the implementation.
- State that the oracle-gap layer is bounded by model capacity, feature information,
  label noise, sample size, metrics, and thresholds.
- State that small oracle gaps do not prove absence of conditional shift.
- State that the calibration and oracle-gap diagnostics are complementary, not
  statistically independent.
- Use "multi-signal synthesis" rather than "independent evidence."
- Keep the positive control descriptive, model- and level-dependent, and not binary.
- Keep the diagnostic recalibration oracle-style and not deployable.
- Preserve Rule F as a bounded interpretation.
- Do not add new claims or new decision rules.

## Implications for Figure 1

Figure 1 can still show the layer-to-role mapping described in the rationale note, but
it should not visually imply statistical independence among the diagnostic layers. It
should use wording such as "complementary evidence layers" or "multi-signal synthesis"
rather than language suggesting independent confirmation. It should not show the oracle
gap as proving absence of multivariate relationship drift, it should not show the
positive control as a binary outcome, and it should not present the diagnostic
recalibration as deployable.

## Recommended next step

- Review this caveat audit.
- Then create or revise the Figure 1 protocol schematic specification using both
  paper/notes/method_protocol_rationale_v1.md and
  paper/notes/method_open_caveats_audit_v1.md.
- Then draft the Methods section using both notes as guardrails.

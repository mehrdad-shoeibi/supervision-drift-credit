# Method Protocol Rationale v1

## Scope note

This is a conceptual method-rationale bridge note. It does not add analysis, and it
does not change results, thresholds, or decision rules. It does not edit the
manuscript, and it does not create tables or figures. It prepares the framing for the
later Methods section, the Introduction, and Figure 1. The empirical scope is one
public LendingClub lending dataset. The protocol focuses on supervision drift and
relationship-relevant shift; it is not designed as a standalone test for exhaustive
testing of pure covariate shift in P(x). Where a rationale below is inferential rather
than directly locked, it is labeled as methodological framing or interpretive
rationale, not as a new empirical result.

## Why this note exists

The five diagnostic layers should not be presented as an arbitrary list of useful
checks. They should be framed as a structured diagnostic protocol that separates
different evidence types relevant to supervision drift: observed transfer performance,
performance-based multivariate relationship-change evidence, prior or base-rate or
probability-scale shift, marginal feature-label association instability, and the
sensitivity boundary of the diagnostic stack under controlled injected shifts.

The goal is not to prove absence of drift. The goal is to expose what the locked
diagnostic stack can and cannot see. A bounded or inconclusive reading, such as the
Rule F reading reached in this case study, is an intended output of the framework
rather than a failure mode. The protocol is not intended to exhaustively test all forms
of distribution shift. In particular, pure covariate shift in P(x) is not treated as a
standalone diagnostic target unless it affects transfer performance, calibration,
oracle-gap behavior, feature-label associations, or positive-control sensitivity. The
framework therefore makes a focused claim about supervision drift and
relationship-relevant change, and it does not claim universal detection or complete
coverage of all possible shifts.

## Mapping diagnostic layers to shift mechanisms

| Diagnostic layer | Primary question | Shift mechanism or interpretive role | What it can support | What it cannot support |
|---|---|---|---|---|
| Primary transfer performance | Does a source-trained model retain predictive performance under the target context? | Observed transfer behavior across ranking and probability-scale metrics. | Evidence about practical transfer degradation or stability under locked thresholds. | It cannot by itself identify the mechanism of shift. |
| Oracle-gap diagnostic | Does a target-trained oracle gain meaningful ranking advantage over the source-trained model? | Primary performance-based probe for multivariate relationship change. | Evidence that target-context training recovers ranking performance not available to the source-trained model. | It cannot prove that no conditional shift exists, especially if effects are small, model-limited, or sample-size-limited. |
| Calibration diagnostic | Is the main issue probability-scale, prior, or base-rate mismatch? | Prior, base-rate, and probability-scale shift. | Evidence for a Rule B-style calibration and base-rate pattern when diagnostic recalibration fixes most calibration error. | It cannot be interpreted as deployable recalibration, because the diagnostic recalibration uses target-context label information. |
| Feature-label stability diagnostic | Do marginal feature-label associations shift beyond noise-baseline variation? | Marginal association shift. | Evidence about univariate feature-label instability and interpretable marginal changes. | It cannot prove full multivariate conditional stability of the conditional label distribution P(y given x). |
| Positive-control sensitivity | Does the diagnostic stack respond to known injected relationship shifts? | Sensitivity boundary of the diagnostic protocol. | Evidence that the diagnostic stack can respond to larger controlled injected shifts in this positive-control setting. | It is not a binary drift detector, not a formal power analysis, and not proof of universal validity. |

This mapping converts the protocol from a list of metrics into a structured diagnostic
decomposition, in which each layer answers a distinct question and carries an explicit
boundary on what it can and cannot support. The decomposition is interpretive and
methodological, not a new empirical result, and it should guide the Methods wording and
the Figure 1 design.

This mapping should not be described as an exhaustive taxonomy of all distribution
shifts; it is not an exhaustive taxonomy. In particular, the protocol is not designed as
a standalone test for pure covariate shift in P(x). Its focus is supervision drift and
relationship-relevant change, meaning shifts that affect transfer performance, oracle
recoverability, calibration, marginal feature-label association, or positive-control
sensitivity. Pure changes in the feature distribution that do not affect these evidence
layers remain outside the main claim of the paper.

## Oracle gap as the multivariate relationship-change probe

The oracle-gap diagnostic is the primary performance-based probe for multivariate
relationship change, whereas the feature-label stability diagnostic is intentionally
marginal and complementary. The intuition is direct: if the relationship between
features and labels changes in a way that is learnable from the target context and
relevant to ranking, then a model trained directly on the target context should gain a
ranking advantage over the source-trained model when both are evaluated on the same
held-out target fold. The oracle gap measures exactly this difference, so it probes
multivariate relationship change through achievable performance rather than through any
single marginal association.

In this case study the temporal oracle gaps are small and the cross-segment oracle gaps
are small or slightly negative, which limits the evidence for large detectable
multivariate relationship drift under the chosen models and contexts. This is a bounded
statement, not a proof of absence of conditional shift. The conclusion is conditioned on
the model class, the available target-context sample, the metrics, and the locked
thresholds, and small effects could remain below what these models and settings can
recover.

Because the oracle gap is performance-based and multivariate, the feature-label
stability diagnostic is positioned as a complement rather than as the main multivariate
test. The two layers answer different questions, and they should be read together rather
than substituted for one another.

## Calibration diagnostic rationale

The calibration diagnostic helps distinguish ranking stability from probability-scale
mismatch. Discrimination and calibration are distinct properties, so a worsening Brier
score in the temporal setting may reflect base-rate or probability-scale differences
between settings and should not be treated as standalone evidence of relationship drift.
The diagnostic recalibration is an oracle-style counterfactual, because it uses
target-context label information to set the recalibration adjustment.

When the diagnostic recalibration fixes most of the calibration error while the oracle
gaps remain small, the combined evidence supports a Rule B-style prior, base-rate, and
probability-scale interpretation rather than the rule for combined base-rate shift and
deeper relationship drift (Rule D), which requires calibration to remain poor after
recalibration together with a large oracle gap. The recalibration is not deployable and
should not be described as production calibration; it is a diagnostic device for
separating probability-scale mismatch from deeper relationship change.

## Feature-label stability rationale

The feature-label stability diagnostic checks marginal feature-label associations
against random-split noise-baseline variation, which provides interpretable evidence
about univariate association changes. It is useful as a complement to the performance
and calibration diagnostics, because marginal association shifts can be inspected
feature by feature and related to domain understanding.

This layer is marginal and univariate, so it cannot prove full conditional stability of
P(y given x); a stable set of marginal associations is consistent with, but does not
establish, multivariate conditional stability. The Spearman-based sensitivity check
should remain a transparently reported caveat rather than the locked band metric, which
is based on univariate AUC strength.

## Positive-control rationale and boundaries

The positive control is designed to test whether the diagnostic stack moves in the
expected direction under known injected relationship shifts of increasing magnitude. It
should be framed as a descriptive sensitivity check, not as a binary pass or fail
detector. The current locked interpretation is model- and level-dependent: stronger
injected shifts show clearer sensitivity, while the weak and medium levels should not be
overinterpreted.

The aggregation unit and the row-alignment rule were not pre-specified as locked binary
decision rules, so the positive control is reported as a model- and level-dependent
sensitivity curve rather than as a single detected or not-detected outcome. It supports
sensitivity to larger injected shifts in this positive-control setting, but it does not
validate the protocol universally and is not a binary detection result.

The positive control uses interpretable numeric credit-risk covariates, such as dti_n
and fico_n, as a transparent design choice for injecting controlled relationship shifts
without overwriting the observed outcome labels. The locked notes do not characterize
these covariates as the strongest predictors, so they should not be described that way;
the feature-choice rationale should be verified against the locked positive-control
implementation before manuscript integration.

## Oracle sample-size transparency caveat

The interpretation of the oracle gap depends partly on the amount of target-context data
available to train the oracle model. In the cross-segment setting, the target segment is
smaller than the source segment, which can limit the oracle model and can make small or
slightly negative oracle gaps difficult to interpret as evidence of no drift.

The draft Table 1 includes train_n and test_n for the transfer settings, because those
columns are present in the locked primary result table, and these sizes should be
reported so that the oracle-gap interpretation is transparent. This note does not claim a
direction of bias and does not claim that the temporal oracle is unbiased; it states
conservatively that sample-size asymmetry is an interpretation caveat for the oracle-gap
layer.

## Framing Rule F as an intended diagnostic output

Rule F should be framed as an honest, bounded interpretation rather than as a weakness of
the study. The framework is useful partly because it can say when the evidence is
insufficient to claim large detectable relationship drift, and reporting that boundary is
part of responsible audit design. A useful audit framework should report both what it
detects and where its sensitivity is bounded.

The framework should not be framed as guaranteeing detection. Smaller or subtler
relationship drift remains possible, and the Rule F reading expresses precisely this
bounded conclusion: the locked diagnostics constrain the size and form of drift that
would have been visible, without certifying that the conditional relationship is
unchanged.

## Implications for Figure 1

Figure 1 should not only show a processing pipeline. It should show the interpretive role
of each diagnostic layer, so that a reader can see why each layer exists rather than only
the order in which the layers run. The figure should visually connect the empirical
scope, the transfer settings, each diagnostic layer, its shift mechanism or interpretive
role, and the rule-based synthesis.

A suggested mapping for Figure 1 is: primary transfer performance -> observed transfer
behavior; oracle gap -> multivariate relationship-change probe; calibration ->
prior/base-rate/probability-scale shift; feature-label stability -> marginal association
shift; positive control -> sensitivity boundary. Figure 1 should not include exact result
values, should not claim universal validation, should not show the positive control as a
binary outcome, should not present recalibration as deployable, and should not present the
protocol as an exhaustive taxonomy of all distribution shifts.

## Implications for the Methods section

- Introduce the protocol as a layered diagnostic design, not a list of unrelated metrics.
- Explain why each layer exists before describing its implementation details.
- Clarify that the framework is focused on supervision drift and relationship-relevant
  shift, not exhaustive testing of pure covariate shift in P(x).
- Report the transfer settings and sample sizes transparently.
- Distinguish source-trained models, target-trained oracle models, and the diagnostic
  recalibration.
- State that the oracle gap probes multivariate relationship change in a performance-based
  way.
- State that the feature-label stability diagnostic is marginal and complementary.
- State that the diagnostic recalibration is oracle-style and non-deployable.
- State that the positive control is descriptive sensitivity, not binary detection.
- Avoid claiming absence of drift.
- Avoid claiming universal validation.
- Avoid claiming that the five diagnostics exhaust all possible shifts.
- Keep all decision rules locked.

## Forbidden manuscript framings

The following framings should be avoided in the manuscript:
- "The diagnostics prove no drift."
- "The dataset has no drift."
- "Positive control passed."
- "Stage 7 detected drift."
- "Stage 7 ruled out drift."
- "Recalibration solves deployment calibration."
- "Feature-label stability proves P(y given x) stability."
- "Oracle gap proves no conditional shift."
- "One dataset validates the protocol."
- "The protocol guarantees detection."
- "The five diagnostics exhaust all possible shifts."
- "The protocol fully tests pure covariate shift."

## Recommended next step

- Review this rationale note.
- Then revise or create the Figure 1 specification so that it includes the
  diagnostic-layer to shift-mechanism mapping.
- After that, draft the Methods section using this rationale as the guide.
- Do not write the Methods section until this rationale is reviewed.

# Stage 6 Feature-Label Stability Band Assignment

**Date:** 2026-06-07
**Type:** Result-only, mechanical band assignment (not scientific interpretation).

This note was created **after the Stage 6 feature–label stability outputs were
locked** in git and **before the Stage 7 positive-control diagnostics were run.**
It is a purely mechanical application of the **pre-locked Stage 6 instability
thresholds** in `docs/03_data_dictionary_and_assumptions.md` §9 to the locked
Stage 6 summary outputs. It introduces no new metric, threshold, or decision rule,
and provides no final interpretation.

## Locked thresholds (verbatim from `docs/03` §9)

Instability is assessed as a **ratio** of a real-comparison stability delta to the
**corresponding noise-baseline** delta:

- **low:** ratio `<= 2.0×` noise baseline
- **moderate / borderline:** ratio `> 2.0×` and `< 3.0×` noise baseline
- **high:** ratio `>= 3.0×` noise baseline

The ratio is `real comparison metric / corresponding noise-baseline metric`, with
baselines paired as:
- `temporal` uses `temporal_noise_baseline`
- `cross_segment` uses `cross_segment_noise_baseline`

## Locked band-assignment metrics (from `docs/03` §9)

`docs/03` §9 names the stability deltas as "**mean `delta_abs_auc_strength`**"
(numeric) and "**weighted mean `delta_abs_risk_difference`**" (categorical). These
map to the locked Stage 6 JSON aggregates:

- **Numeric core metric:** `numeric_mean_delta_abs_auc_strength`
- **Categorical core metric:** `categorical_mean_weighted_risk_diff_change`

Spearman correlation is **not** named as a band metric in the locked docs; it is
descriptive only and is **not** used for band assignment. The `*_max_*` metrics are
not the named "mean"/"weighted mean" metrics and are reported as descriptive /
sensitivity only.

## Numeric band assignment (core metric: `numeric_mean_delta_abs_auc_strength`)

| comparison | baseline | metric | real_value | baseline_value | ratio | band |
|---|---|---|---|---|---|---|
| temporal | temporal_noise_baseline | numeric_mean_delta_abs_auc_strength | 0.006987 | 0.002807 | 2.4895 | moderate / borderline |
| cross_segment | cross_segment_noise_baseline | numeric_mean_delta_abs_auc_strength | 0.006297 | 0.003595 | 1.7518 | low |

## Categorical band assignment (core metric: `categorical_mean_weighted_risk_diff_change`)

A categorical band metric **is** locked, so categorical bands are assigned.

| comparison | baseline | metric | real_value | baseline_value | ratio | band |
|---|---|---|---|---|---|---|
| temporal | temporal_noise_baseline | categorical_mean_weighted_risk_diff_change | 0.015944 | 0.011116 | 1.4343 | low |
| cross_segment | cross_segment_noise_baseline | categorical_mean_weighted_risk_diff_change | 0.015431 | 0.017989 | 0.8578 | low |

## Non-core metric ratios (transparency; NOT used for band assignment)

These are reported for transparency and are **not** hidden, but per `docs/03` §9
they are **not** the locked band-assignment metrics.

| comparison | baseline | metric | real_value | baseline_value | ratio | status |
|---|---|---|---|---|---|---|
| temporal | temporal_noise_baseline | numeric_max_delta_abs_auc_strength | 0.015316 | 0.005401 | 2.8356 | descriptive / sensitivity; not used for band assignment |
| cross_segment | cross_segment_noise_baseline | numeric_max_delta_abs_auc_strength | 0.017457 | 0.008597 | 2.0307 | descriptive / sensitivity; not used for band assignment |
| temporal | temporal_noise_baseline | categorical_max_risk_diff_change | 0.923142 | 1.000000 | 0.9231 | descriptive / sensitivity; not used for band assignment |
| cross_segment | cross_segment_noise_baseline | categorical_max_risk_diff_change | 1.031675 | 1.000025 | 1.0316 | descriptive / sensitivity; not used for band assignment |
| temporal | temporal_noise_baseline | numeric_mean_delta_abs_spearman | 0.021322 | 0.004414 | 4.8307 | descriptive only (Spearman not a locked band metric); not used for band assignment |
| cross_segment | cross_segment_noise_baseline | numeric_mean_delta_abs_spearman | 0.004994 | 0.005761 | 0.8668 | descriptive only (Spearman not a locked band metric); not used for band assignment |

## Data-quality notes (do not affect the locked band metrics)

- **Spearman NaN:** the per-feature Spearman metrics in
  `feature_label_stability_numeric.csv` contain legitimate NaN only for the
  constant feature `experience_c` (zero variance → undefined rank correlation; 4
  rows, one per comparison). Spearman is not used for band assignment. The core
  numeric metric `delta_abs_auc_strength` is finite and NaN-free across all rows
  (and its JSON aggregate is finite for all four comparisons).
- **Category-level detail NaN:** the 3571-row
  `feature_label_stability_categorical_categories.csv` detail table contains
  legitimate NaN for one-sided rare categories (a category present in one context
  and absent in the other). That detail table was **not** used for band assignment;
  these NaNs do not affect the locked summary metric
  (`categorical_mean_weighted_risk_diff_change`), which has no NaN.

## Conceptual limitation

- Stage 6 is a **marginal / univariate** feature–label stability diagnostic (it
  measures per-feature associations: univariate AUC strength, Spearman, and
  per-category risk differences).
- It does **not** prove full **multivariate** stability of `P(y | x)`.
- Low or moderate marginal instability must **not** be overstated as proof of no
  relationship drift.

## Scope and status

- This note **does not** change thresholds, **does not** add decision rules, and
  **does not** introduce new metrics. It distinguishes **mechanical band
  assignment** (done here) from **scientific interpretation** (not done here).
- Low marginal instability does **not** prove no drift; moderate marginal
  instability does **not** prove drift; Stage 6 alone does **not** prove or
  disprove supervision drift.
- **Final interpretation remains pending** until the Stage 7 positive-control
  diagnostics are completed and read together with the Stage 3 primary results and
  the Stage 4–6 diagnostics under the locked multi-signal decision rules.

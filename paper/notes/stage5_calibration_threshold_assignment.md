# Stage 5 Calibration Threshold Assignment

**Date:** 2026-06-07
**Type:** Result-only, mechanical threshold assignment (not scientific interpretation).

This note was created **after the Stage 5 calibration diagnostic outputs were locked**
in git and **before the Stage 6 (feature–label stability) and Stage 7 (positive-control)
diagnostics were run.** It is a purely mechanical application of the **pre-locked
calibration thresholds** recorded in `docs/03_data_dictionary_and_assumptions.md`,
applied to the locked `results/tables/calibration_summary.csv`. It introduces no new
thresholds, no new decision rules, and no final interpretation.

## Locked calibration thresholds (verbatim from `docs/03`)

**Calibration poor** if any of:
- ECE(10-bin) `> 0.05`, or
- |calibration intercept| `> 0.5`, or
- calibration slope outside `[0.8, 1.25]`.

**Recalibration fixes most of it** if:
- ECE(10-bin) is reduced by `>= 50%`, **and**
- recalibrated ECE(10-bin) `<= 0.05`.

Mechanical computation used here (locked CSV values only):
- `calibration_poor = (raw_ece10 > 0.05) OR (|raw_cal_intercept| > 0.5) OR (raw_cal_slope < 0.8 OR raw_cal_slope > 1.25)`
- `ece10_reduction_fraction = ece10_improvement / raw_ece10`
- `recalibration_fixes_most = (ece10_reduction_fraction >= 0.50) AND (recal_ece10 <= 0.05)`

The `calibration_deciles.csv` table was **not** used for this threshold assignment.

## Diagnostic-only / oracle-style recalibration

The Stage 5 recalibration is **diagnostic-only / oracle-style**: it estimates an
intercept/base-rate adjustment using the **observed target/test default rate
(target/test labels)**, which is not available at deployment time. Recalibrated
results are **not** treated as a deployable model and are kept **separate** from the
raw calibration results (distinct `raw_*` and `recal_*` columns). The
`recalibration_fixes_most` flag below is a mechanical property of this diagnostic
adjustment, not a statement about a fielded model.

## Per-row threshold assignment

| context | model | seed | raw_ece10 | raw_cal_intercept | raw_cal_slope | calibration_poor | calibration_poor_triggers | recal_ece10 | ece10_reduction_fraction | recalibration_fixes_most |
|---|---|---|---|---|---|---|---|---|---|---|
| in_domain | logreg | 0 | 0.010535 | -0.276 | 0.826 | False | none | 0.010530 | 0.000 | False |
| in_domain | hgb | 0 | 0.006193 | 0.102 | 1.063 | False | none | 0.006120 | 0.012 | False |
| in_domain | rf | 0 | 0.029959 | -0.615 | 0.582 | True | \|raw_cal_intercept\| > 0.5; raw_cal_slope outside [0.8, 1.25] | 0.029048 | 0.030 | False |
| in_domain | rf | 1 | 0.029575 | -0.621 | 0.580 | True | \|raw_cal_intercept\| > 0.5; raw_cal_slope outside [0.8, 1.25] | 0.027105 | 0.084 | False |
| in_domain | rf | 2 | 0.029374 | -0.611 | 0.585 | True | \|raw_cal_intercept\| > 0.5; raw_cal_slope outside [0.8, 1.25] | 0.026922 | 0.083 | False |
| temporal | logreg | 0 | 0.071088 | 0.298 | 0.886 | True | raw_ece10 > 0.05 | 0.006098 | 0.914 | True |
| temporal | hgb | 0 | 0.075579 | 0.635 | 1.078 | True | raw_ece10 > 0.05; \|raw_cal_intercept\| > 0.5 | 0.005148 | 0.932 | True |
| temporal | rf | 0 | 0.081410 | -0.040 | 0.639 | True | raw_ece10 > 0.05; raw_cal_slope outside [0.8, 1.25] | 0.029177 | 0.642 | True |
| temporal | rf | 1 | 0.080945 | -0.046 | 0.637 | True | raw_ece10 > 0.05; raw_cal_slope outside [0.8, 1.25] | 0.029272 | 0.638 | True |
| temporal | rf | 2 | 0.081373 | -0.046 | 0.636 | True | raw_ece10 > 0.05; raw_cal_slope outside [0.8, 1.25] | 0.029311 | 0.640 | True |
| cross_segment | logreg | 0 | 0.026956 | -0.374 | 0.905 | False | none | 0.005704 | 0.788 | True |
| cross_segment | hgb | 0 | 0.026839 | -0.053 | 1.109 | False | none | 0.004968 | 0.815 | True |
| cross_segment | rf | 0 | 0.029331 | -0.834 | 0.580 | True | \|raw_cal_intercept\| > 0.5; raw_cal_slope outside [0.8, 1.25] | 0.024705 | 0.158 | False |
| cross_segment | rf | 1 | 0.030303 | -0.836 | 0.579 | True | \|raw_cal_intercept\| > 0.5; raw_cal_slope outside [0.8, 1.25] | 0.025614 | 0.155 | False |
| cross_segment | rf | 2 | 0.029959 | -0.842 | 0.577 | True | \|raw_cal_intercept\| > 0.5; raw_cal_slope outside [0.8, 1.25] | 0.025416 | 0.152 | False |

## Summary by context

| context | n rows | calibration_poor | recalibration_fixes_most | poor triggered only by slope/intercept (not ECE) |
|---|---|---|---|---|
| in_domain | 5 | 3 | 0 | 3 |
| temporal | 5 | 5 | 5 | 0 |
| cross_segment | 5 | 3 | 2 | 3 |
| **total** | **15** | **11** | **7** | **6** |

## Rows where `calibration_poor` was triggered only by slope/intercept, not ECE

These rows have `raw_ece10 <= 0.05` but are still `calibration_poor` because the
intercept and/or slope thresholds were crossed. They must **not** be summarized as
"not poor" on the basis of ECE alone:

- `in_domain, rf, seed 0` — raw_ece10=0.029959, intercept=-0.615, slope=0.582
- `in_domain, rf, seed 1` — raw_ece10=0.029575, intercept=-0.621, slope=0.580
- `in_domain, rf, seed 2` — raw_ece10=0.029374, intercept=-0.611, slope=0.585
- `cross_segment, rf, seed 0` — raw_ece10=0.029331, intercept=-0.834, slope=0.580
- `cross_segment, rf, seed 1` — raw_ece10=0.030303, intercept=-0.836, slope=0.579
- `cross_segment, rf, seed 2` — raw_ece10=0.029959, intercept=-0.842, slope=0.577

Note: `cross_segment` is therefore **not** characterized using ECE alone — its `rf`
rows are `calibration_poor` via slope/intercept even though their ECE(10-bin) is
`<= 0.05`.

## Scope and status

- This note **does not change any threshold**, **does not add any decision rule**,
  and **does not provide a final interpretation**. It distinguishes **mechanical
  threshold assignment** (done here) from **scientific interpretation** (not done here).
- `calibration_poor = true` does **not** by itself prove supervision drift.
- `recalibration_fixes_most = true` does **not** prove the absence of drift, and
  does **not** imply any model is deployable after recalibration (the adjustment uses
  target/test labels and is diagnostic-only).
- No final mechanism is claimed here.
- **Final interpretation remains pending** until the Stage 6 feature–label stability
  and Stage 7 positive-control diagnostics are completed and read together with the
  primary results and the oracle-gap results under the locked multi-signal decision
  rules.

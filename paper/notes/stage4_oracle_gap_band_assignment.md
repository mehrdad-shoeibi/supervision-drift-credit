# Stage 4 Oracle-Gap Band Assignment

**Date:** 2026-06-07
**Type:** Result-only, mechanical band assignment (not scientific interpretation).

This note was created **after the Stage 4 oracle-gap diagnostic outputs were locked**
in git and **before the Stage 5 (calibration), Stage 6 (feature–label stability),
and Stage 7 (positive-control) diagnostics were run.** It is a purely mechanical
application of the **pre-locked oracle-gap AUROC thresholds** recorded in
`docs/03_data_dictionary_and_assumptions.md`. It introduces no new thresholds,
no new decision rules, and no final interpretation.

## Locked oracle-gap AUROC bands

Reproduced verbatim from the locked thresholds in `docs/03`:

- **small:** `oracle_gap_auroc < 0.02`
- **moderate / borderline:** `0.02 <= oracle_gap_auroc < 0.05`
- **large:** `oracle_gap_auroc >= 0.05`

Source: `oracle_gap_auroc = oracle_auroc - source_auroc`, both evaluated on the
**same** held-out target test fold (per `results/tables/oracle_gap_summary.csv`).

## Band assignment for every Stage 4 row

| comparison | model | seed | source_auroc | oracle_auroc | oracle_gap_auroc | assigned_band | note |
|---|---|---|---|---|---|---|---|
| temporal | logreg | 0 | 0.655225 | 0.663568 | +0.008343 | small | positive oracle gap; within small band |
| temporal | hgb | 0 | 0.662149 | 0.672586 | +0.010437 | small | positive oracle gap; within small band |
| temporal | rf | 0 | 0.626866 | 0.643265 | +0.016399 | small | positive oracle gap; within small band |
| temporal | rf | 1 | 0.625448 | 0.640678 | +0.015230 | small | positive oracle gap; within small band |
| temporal | rf | 2 | 0.626166 | 0.642454 | +0.016288 | small | positive oracle gap; within small band |
| cross_segment | logreg | 0 | 0.615567 | 0.608299 | -0.007268 | small | small; no positive oracle advantage on this held-out fold |
| cross_segment | hgb | 0 | 0.635927 | 0.642017 | +0.006090 | small | positive oracle gap; within small band |
| cross_segment | rf | 0 | 0.599807 | 0.596721 | -0.003086 | small | small; no positive oracle advantage on this held-out fold |
| cross_segment | rf | 1 | 0.599127 | 0.593889 | -0.005238 | small | small; no positive oracle advantage on this held-out fold |
| cross_segment | rf | 2 | 0.597965 | 0.598331 | +0.000367 | small | positive oracle gap; within small band |

## Summary of band assignment

- **All 10 Stage 4 `oracle_gap_auroc` values fall in the `small` band, because all are `< 0.02`.**
- **No Stage 4 `oracle_gap_auroc` value falls in the `moderate / borderline` band (`0.02 <= gap < 0.05`).**
- **No Stage 4 `oracle_gap_auroc` value falls in the `large` band (`gap >= 0.05`).**

## On negative oracle-gap values

Three rows have a negative `oracle_gap_auroc` (cross_segment: logreg seed 0,
rf seed 0, rf seed 1):

- A negative `oracle_gap_auroc` is mathematically `< 0.02` and therefore falls in
  the locked `small` band for the purpose of this thresholding rule.
- A negative `oracle_gap_auroc` means the target-trained oracle model **did not
  outperform** the source-trained model on that held-out fold.
- This is an **observation about that fold**, not a final stability or no-drift
  conclusion.
- A negative gap is **not, by itself, evidence of stability.**

## Sanity check (consistency only, not a scientific conclusion)

The Stage 4 source models on the temporal held-out fold and the Stage 3 temporal
models on the full 2016 test set are evaluated on **different** evaluation sets,
so their AUROC values are **not expected to be identical**. They are only compared
here as a rough consistency check:

- Stage 3 temporal **HGB** AUROC on the full 2016 test set ≈ **0.6592**.
- Stage 4 temporal **HGB** `source_auroc` on the held-out 2016 fold ≈ **0.6621**.
- Stage 3 temporal **logreg** AUROC on the full 2016 test set ≈ **0.6534**.
- Stage 4 temporal **logreg** `source_auroc` on the held-out 2016 fold ≈ **0.6552**.

These pairs are close but differ because the evaluation sets differ. This is only
a consistency check, not a scientific conclusion.

## Scope and status

- This note **does not change any threshold**, **does not add any decision rule**,
  and **does not provide a final interpretation**.
- It distinguishes **mechanical band assignment** (done here) from **scientific
  interpretation** (not done here).
- **Final interpretation remains pending** until the Stage 5 calibration, Stage 6
  feature–label stability, and Stage 7 positive-control diagnostics are completed
  and read together under the locked multi-signal decision rules.

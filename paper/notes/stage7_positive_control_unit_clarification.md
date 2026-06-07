# Stage 7 Positive-Control Unit and Aggregation Clarification

**Date:** 2026-06-07
**Type:** Protocol-clarification note (not a detection assignment, not a synthesis).

## Timing and scope

- This note was created **after** the Stage 7 raw positive-control outputs were locked.
- This note was created **before** the final multi-signal synthesis.
- This note does **not** rerun any experiment and does **not** run Stage 7 or any model.
- This note does **not** change the Stage 7 raw outputs.
- This note does **not** edit source code, docs, or prior notes.
- This note does **not** introduce a new binary detected/not-detected decision rule.
- This note does **not** create `paper/notes/stage7_positive_control_detection_assignment.md`.

## Locked criterion components

The locked docs (`docs/03_data_dictionary_and_assumptions.md` §9) specify, for the
positive control:

> **Positive control detected** at a perturbation level if that level produces a
> clearly monotone, materially larger oracle gap / stability delta than the real
> temporal result — concretely, `oracle_gap_auroc` at that level exceeds the real
> temporal `oracle_gap_auroc` by `>= 0.05`, with the gap increasing
> weak -> medium -> strong.

So the locked components are:

- **metric:** `oracle_gap_auroc`;
- **comparator:** real temporal `oracle_gap_auroc` (Stage 4 temporal oracle gap);
- **margin:** synthetic level exceeds the real temporal value by `>= 0.05`;
- **monotonicity:** gap increasing weak -> medium -> strong.

These are locked components of the criterion. However, **these components alone are
not sufficient to produce a single binary detected/not-detected assignment**,
because the locked docs do not specify the unit/aggregation or the row-alignment
rule (see next section).

## Ambiguity not resolved in locked docs

The locked docs do **not** specify:

- whether the criterion is evaluated **per model-seed**, **per model**, or as an **aggregate**;
- whether detection requires **any** model, **all** models, a **majority** of models, or an **aggregate** value;
- whether RF seeds (`0, 1, 2`) should be evaluated **separately** or **averaged**;
- whether `logreg`/`hgb` seed 0 should be compared **only** to their own seed-0 real temporal rows;
- how the **Stage 4 temporal** rows and the **Stage 7 synthetic** rows should be **aligned** (the comparator is "real temporal `oracle_gap_auroc`", but Stage 4 temporal has one row per model/seed and Stage 7 has one row per level per model/seed);
- how to handle models with **different numbers of seeds** (RF has 3 seeds; logreg/hgb have 1).

Because each of these choices can change a single detected/not-detected assignment,
**collapsing Stage 7 into one binary flag would require a new post-hoc
aggregation/alignment decision** that the locked protocol does not provide.

## Conservative reporting decision

- **No single binary Stage 7 detected/not-detected flag will be introduced here.**
- Stage 7 will be reported as a **model/seed-level sensitivity curve**.
- Each **model/seed** row and each **perturbation level** remains individually visible.
- The real comparator remains **temporal-only** (Stage 4 temporal oracle gap).
- **Cross-segment** Stage 4 rows are **not** used as the positive-control comparator,
  because the locked criterion names the real **temporal** oracle gap.
- **No seed substitution** is performed.
- **No unstated averaging** across seeds or models is performed.
- Descriptive summaries may be reported **only if clearly labeled descriptive** and
  **not** used as a locked decision rule.

## Descriptive Stage 7 pattern

The following is **descriptive only**, read directly from the locked
`results/tables/positive_control_summary.csv`. The `monotone increasing` column
reports **one** locked component of the criterion (monotonicity); it is **not** a
detection assignment.

| model | seed | weak oracle_gap_auroc | medium oracle_gap_auroc | strong oracle_gap_auroc | monotone increasing (descriptive only) |
|---|---|---|---|---|---|
| hgb | 0 | 0.014703 | 0.029125 | 0.057874 | True |
| logreg | 0 | 0.010526 | 0.018848 | 0.041982 | True |
| rf | 0 | 0.024814 | 0.041956 | 0.081049 | True |
| rf | 1 | 0.022333 | 0.039572 | 0.078997 | True |
| rf | 2 | 0.024759 | 0.041507 | 0.080343 | True |

**Framing of the monotonicity column (explicit):**

- The `monotone increasing` column is **descriptive only**.
- It reports **one** locked component of the Stage 7 criterion (the weak -> medium
  -> strong ordering of `oracle_gap_auroc`), and nothing more.
- It must **not** be interpreted as a positive-control detected/not-detected
  assignment.
- **Even where a model/seed shows monotone-increasing gaps, this note does not say
  the positive control is "detected,"** because the unit/aggregation and
  row-alignment rules were not locked. Monotonicity alone does not constitute
  detection under the locked criterion (which also requires the `>= 0.05` margin
  over the real temporal comparator, under an unlocked aggregation/alignment unit).

No detected/not-detected column, no positive-control pass/fail column, no margin-pass
column, no Rule E/F/G assignment, and no synthesis conclusion are included here, by
design.

## Implication for final synthesis

- Final synthesis should treat Stage 7 as **evidence about diagnostic sensitivity**,
  not as a single binary pass/fail flag.
- The final synthesis may use the monotonicity pattern as **sensitivity evidence**,
  but must **not** convert it into a binary detection claim unless a separate,
  explicitly documented decision rule (specifying the aggregation unit and
  row-alignment) is introduced and justified.
- The final synthesis should report that the positive-control gaps **increase
  monotonically by model/seed** if supported by the locked output.
- The final synthesis should acknowledge that sensitivity is **level- and
  model-dependent**.
- The final synthesis must **not** claim that positive-control detection proves the
  absence of smaller real-world drift.
- The final synthesis must **not** claim that failure at weak or medium levels
  invalidates the diagnostic.
- The final synthesis should preserve the distinction between **raw sensitivity
  evidence** and **final real-data interpretation**.

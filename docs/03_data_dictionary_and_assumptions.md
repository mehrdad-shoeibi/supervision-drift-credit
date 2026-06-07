# 03 — Data Dictionary and Assumptions

**Status: LOCKED before any official experiment.**

This document records the expected schema, processing assumptions, missing-value
policy, segment policy, no-leakage assumptions, the locked interpretive
thresholds referenced by `docs/02_decision_rules.md`, and known limitations.

---

## 1. Expected raw file

- Path: `data/raw/LC_loans_granting_model_dataset.csv`
- Format: CSV with a header row.
- Dataset: LendingClub loan-granting model dataset.

The exact column set of any given LendingClub export varies. The pipeline is
written to be **robust to the presence/absence of optional columns**: required
columns are validated explicitly; optional/leakage-prone columns are dropped if
present.

---

## 2. Target column

- **`Default`** — binary operational/accounting proxy label.
- Interpreted as an **imperfect proxy** for creditworthiness, not ground truth.
- Expected encoding: `{0, 1}`. If encoded as booleans or strings, the loader
  coerces to `{0, 1}` and records the mapping in the log. Rows with a missing or
  uncoercible target are dropped from modeling and the count is recorded.

---

## 3. Date parsing

- **`issue_d`** — loan issue date. LendingClub commonly formats this as
  `"%b-%Y"` (e.g. `Dec-2013`) or `"%b-%y"`. The loader attempts pandas flexible
  parsing and records the parse rate.
- **Issue year** is derived from `issue_d` for **vintage selection only**.
- Issue year is **never** used as a predictive feature.
- Vintages used: **2013** and **2016**.

---

## 4. Dropped columns

Dropped if present (leakage-prone, identifier, or free-text):

- `id`
- `title`
- `desc`

Additional leakage-prone fields are excluded from the predictive feature set per
the no-leakage rules; any such exclusion beyond the three above is logged.

---

## 5. Numeric / categorical handling

- **Feature typing:** columns are classified as numeric vs categorical by dtype
  after load. Object/string and low-cardinality columns are treated as
  categorical; numeric dtypes are treated as numeric.
- **Numeric features:** median imputation (fit on train only) + standardization
  for the linear model; tree models use unscaled numeric features.
- **Categorical features:** most-frequent imputation (fit on train only) +
  one-hot encoding with `handle_unknown="ignore"` (fit on train only).
- The target `Default`, the raw `issue_d`, derived issue year, `purpose` (when
  used as the segment axis), and dropped columns are excluded from the predictive
  feature matrix as appropriate per stage.

---

## 6. Missing-value policy

- Imputation is part of the preprocessing pipeline and is **fit on training data
  only** (no test leakage).
- Rows missing the **target** are dropped from modeling (count logged).
- Rows missing **`issue_d`** (unparseable) are excluded from vintage selection
  (count logged).
- No raw data is ever modified on disk.

---

## 7. Segment policy

- Segment axis: **`purpose`**.
- The **largest** 2013 `purpose` segment is the source segment; the
  **second-largest** is the target segment (locked, by frequency within 2013).
- Ties in segment size are broken by ascending alphabetical category name, and
  the resolution is logged.
- Segment sizes and the resolved source/target are recorded in the Stage 2/3
  manifests.

---

## 8. No-leakage assumptions

- All imputers, encoders, scalers, and predictive calibrators are fit on
  **training data only**.
- Issue year is not a predictive feature.
- IDs and free-text fields are not predictive features.
- Oracle target-trained models (Stage 4, Stage 7) and intercept/base-rate
  recalibration (Stage 5) use target-context labels **only as explicitly
  labeled diagnostics**; these are never reported as deployment-available
  performance.

---

## 9. Locked interpretive thresholds

These operationalize the qualitative terms in `docs/02_decision_rules.md`. They
are reference anchors, interpreted alongside the Stage 6 noise baselines and the
Stage 7 positive control. They are locked before execution.

- **AUROC stable:** the drop in test AUROC from the in-domain reference to a
  transfer context is `< 0.02` (absolute). A drop `>= 0.05` is "degraded";
  `[0.02, 0.05)` is "borderline".
- **Oracle gap small:** `oracle_gap_auroc < 0.02`. "Large" if `>= 0.05`. The
  intermediate band `[0.02, 0.05)` (i.e. `>= 0.02` and `< 0.05`) is
  **"moderate / borderline"**.
- **Feature–label instability low:** the transfer-context stability deltas
  (e.g. mean `delta_abs_auc_strength`, weighted mean `delta_abs_risk_difference`)
  do not exceed the corresponding **noise-baseline** deltas by more than a factor
  of 2. "High" if they exceed the noise baseline by `>= 3x`. The intermediate
  band — **more than 2× but less than 3×** the noise baseline (i.e. `> 2x` and
  `< 3x`) — is **"moderate / borderline"**.
- **Calibration poor:** ECE (10-bin) `> 0.05`, or |calibration intercept| `> 0.5`,
  or calibration slope outside `[0.8, 1.25]`.
- **Recalibration fixes most of it:** intercept/base-rate recalibration reduces
  ECE (10-bin) by `>= 50%` **and** brings the recalibrated ECE `<= 0.05`.
- **Positive control detected** at a perturbation level if that level produces a
  clearly monotone, materially larger oracle gap / stability delta than the real
  temporal result — concretely, `oracle_gap_auroc` at that level exceeds the real
  temporal `oracle_gap_auroc` by `>= 0.05`, with the gap increasing
  weak -> medium -> strong.

These thresholds are diagnostic anchors for transparent reporting; the
multi-signal decision rules in doc 02 govern the final interpretation.

**Reporting of moderate / borderline bands.** A "moderate / borderline" oracle
gap or feature–label instability value is intermediate diagnostic evidence. It
is not, on its own, evidence of strong drift, and it is equally not null
evidence. Such a value is reported transparently as intermediate rather than
forced into the small/large or low/high categories. Where a middle-band result
does not trigger one of the hard decision rules in `docs/02_decision_rules.md`,
it is reported as intermediate diagnostic evidence. Final interpretation weighs
the full pre-specified diagnostic pattern together — primary performance, oracle
gap, calibration, base-rate shift, feature–label stability, and positive-control
sensitivity — preserving scientific caution without collapsing to a rigid binary
reading. This is a reporting clarification only; it does not add, remove, or
alter any decision rule or numeric threshold.

---

## 10. Known limitations

- `Default` is a **proxy label** (operational/accounting), not a validated
  construct of creditworthiness; censoring and loan-maturity effects can bias it
  across vintages.
- Vintage comparison `2013 -> 2016` confounds calendar-time macroeconomic change
  with portfolio/policy change; the design does not attempt to deconfound these.
- Approved-loan datasets reflect **selection by the original underwriting
  policy** (reject inference is out of scope); conclusions concern the
  approved-applicant population only.
- The single locked cross-segment pair is not representative of all segment
  transfers; broader segment analyses would be exploratory.
- Synthetic positive controls validate **sensitivity to injected relationship
  shift of a specific form** (feature-dependent label perturbation); they do not
  exhaustively cover all real drift mechanisms.
- The dataset is a single institution's product; external validity beyond
  LendingClub-style consumer lending is not claimed.

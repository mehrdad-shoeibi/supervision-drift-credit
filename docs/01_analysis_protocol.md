# 01 — Analysis Protocol

**Status: LOCKED before any official experiment.**

This is the complete official analysis plan. It is pre-registered and committed
before any official real-data experiment. Each stage lists its purpose, input
files, output files, leakage controls, and whether it is **primary** or
**diagnostic**.

All stages write a machine-readable log and a manifest (timestamp, command, git
commit, package versions, input file hashes). If any stage fails, it prints the
full traceback and stops.

---

## Stage 0 — Data staging (`src/00_stage_data.py`)

- **Type:** setup.
- **Purpose:** confirm the raw file is present; do not fabricate or download.
- **Input:** `data/raw/LC_loans_granting_model_dataset.csv` (expected).
- **Output:** console instructions only.
- **Leakage controls:** N/A (no modeling).

---

## Stage 1 — Data verification (`src/01_verify_data.py`)

- **Type:** diagnostic / integrity.
- **Purpose:** fingerprint and describe the raw data before any processing.
- **Input:** `data/raw/LC_loans_granting_model_dataset.csv`.
- **Output:**
  - `results/tables/data_verification_summary.json`
  - `results/logs/01_verify_data.log`
  - `results/manifests/01_verify_data_manifest.json`
- **Reports:** file size, SHA256, row/column counts, columns and dtypes,
  `Default` value counts, `issue_d` parse rate, year counts, `purpose` counts.
- **Leakage controls:** read-only; raw data never modified.

---

## Stage 2 — Processed context construction (`src/02_build_processed_contexts.py`)

- **Type:** setup for primary + diagnostic.
- **Purpose:** build the locked analysis contexts.
- **Input:** `data/raw/LC_loans_granting_model_dataset.csv`.
- **Output:**
  - `data/processed/vintage_2013.parquet`
  - `data/processed/vintage_2016.parquet`
  - `data/processed/indomain_2013_train.parquet`
  - `data/processed/indomain_2013_test.parquet`
  - `data/processed/load_report.json`
  - `results/logs/02_build_processed_contexts.log`
  - `results/manifests/02_build_processed_contexts_manifest.json`
- **Procedure:** parse `issue_d`; derive issue year; select vintages 2013 and
  2016; in-domain split is 80/20 within 2013, `random_state=0`, stratified by
  `Default` if feasible.
- **Leakage controls:** drop `id`, `title`, `desc` if present; issue year is
  **not** retained as a predictive feature (used only for vintage selection);
  `purpose` is preserved for segment diagnostics. No preprocessing is fit here —
  only row selection and splitting.

---

## Stage 3 — Primary experiment (`src/03_primary_experiment.py`)

- **Type:** **PRIMARY.**
- **Purpose:** measure discrimination/ranking (and AP/Brier) across the three
  locked contexts.
- **Input:** processed parquet files from Stage 2.
- **Contexts:**
  - **A) In-domain:** train `indomain_2013_train` -> test `indomain_2013_test`.
  - **B) Temporal:** train `vintage_2013` -> test `vintage_2016`.
  - **C) Cross-segment:** train largest 2013 `purpose` -> test second-largest
    2013 `purpose`.
- **Models / seeds:** logreg (seed 0), hgb (seed 0), rf (seeds 0,1,2).
- **Metrics:** AUROC (primary), Average Precision, Brier.
- **Bootstrap:** `--bootstrap` argument, default 2000; bootstrap CIs for AUROC
  on the test set. Cost is documented in the log.
- **Output:**
  - `results/tables/primary_experiment_results.csv`
  - `results/tables/primary_experiment_results.json`
  - `results/logs/03_primary_experiment.log`
  - `results/manifests/03_primary_experiment_manifest.json`
- **Leakage controls:** preprocessing pipeline fit on train fold only; issue
  year excluded; dropped fields excluded.

---

## Stage 4 — Oracle-gap diagnostic (`src/04_oracle_gap_diagnostic.py`)

- **Type:** diagnostic.
- **Purpose:** isolate the achievable performance loss attributable to domain
  shift by comparing a source-trained model to an oracle target-trained model
  **on the same held-out target test fold**.
- **Critical fairness rule:** for each comparison, the source model and the
  oracle model are evaluated on the **exact same** held-out target test fold.
- **Temporal oracle gap:**
  - fixed 80/20 split of `vintage_2016`, `random_state=0`, stratified by
    `Default` if feasible -> `target_train_2016`, `target_test_2016`.
  - source model: train **all** `vintage_2013` -> test `target_test_2016`.
  - oracle model: train `target_train_2016` -> test `target_test_2016`.
- **Cross-segment oracle gap:**
  - source segment = largest 2013 `purpose`; target segment = second-largest
    2013 `purpose`.
  - fixed 80/20 split inside the target segment -> `target_segment_train`,
    `target_segment_test`.
  - source model: train **all** source segment -> test `target_segment_test`.
  - oracle model: train `target_segment_train` -> test `target_segment_test`.
- **Reported quantities:**
  - `source_auroc`, `oracle_auroc`, `oracle_gap_auroc = oracle - source`
  - `source_ap`, `oracle_ap`, `oracle_gap_ap = oracle - source`
  - `source_brier`, `oracle_brier`,
    `oracle_gap_brier = source_brier - oracle_brier`
    (positive means oracle has lower / better Brier).
- **Output:**
  - `results/tables/oracle_gap_summary.csv`
  - `results/tables/oracle_gap_summary.json`
  - `results/logs/04_oracle_gap_diagnostic.log`
  - `results/manifests/04_oracle_gap_manifest.json`
- **Leakage controls:** oracle model trains only on `target_*_train`; both
  models evaluated on the identical held-out fold; preprocessing fit per training
  set only.

---

## Stage 5 — Calibration diagnostic (`src/05_calibration_diagnostic.py`)

- **Type:** diagnostic.
- **Purpose:** characterize raw calibration and the effect of a diagnostic
  intercept / base-rate recalibration.
- **Contexts:** A) in-domain, B) temporal, C) cross-segment (as in Stage 3).
- **For each context / model / seed — raw probabilities:** AUROC, AP, Brier,
  mean predicted probability, observed default rate, calibration intercept,
  calibration slope, ECE (equal-frequency bins 5/10/20), decile calibration
  table (10 bins).
- **Calibration slope/intercept:** clip p to `[1e-6, 1-1e-6]`; compute
  `logit(p)`; fit logistic regression `y ~ logit(p)` with minimal regularization
  (large C); record warnings on failure.
- **Intercept / base-rate recalibration (diagnostic only):**
  - `logit(p_recal) = logit(p_raw_clipped) + delta`
  - choose `delta` so `mean(p_recal)` matches the **observed default rate in the
    test context**.
  - **Not deployment-available** without target labels; reported strictly as a
    diagnostic counterfactual.
  - recompute Brier, calibration intercept/slope, ECE 5/10/20; report
    improvements.
- **Output:**
  - `results/tables/calibration_summary.csv`
  - `results/tables/calibration_deciles.csv`
  - `results/tables/calibration_summary.json`
  - `results/logs/05_calibration_diagnostic.log`
  - `results/manifests/05_calibration_manifest.json`
- **Leakage controls:** predictive model fit on train only; recalibration delta
  uses test labels and is explicitly diagnostic, never reported as deployment
  performance.

---

## Stage 6 — Feature–label stability diagnostic (`src/06_feature_label_stability.py`)

- **Type:** diagnostic.
- **Purpose:** measure instability of feature–label relationships, with a random
  split noise baseline for reference.
- **Comparisons:**
  1. **temporal:** `vintage_2013` vs `vintage_2016`.
  2. **cross_segment:** largest 2013 `purpose` vs second-largest 2013 `purpose`.
  3. **temporal_noise_baseline:** `vintage_2013` split into two random halves.
  4. **cross_segment_noise_baseline:** largest 2013 `purpose` split into two
     random halves.
- **Numeric features:** Spearman correlation with `Default`; univariate AUROC;
  AUROC strength `= max(AUROC, 1-AUROC)`; `delta_abs_spearman`;
  `delta_abs_auc_strength`.
- **Categorical features:** reference categories from **context A only**;
  category prevalence; category count; category default rate; context base
  default rate; risk difference from base rate; `delta_abs_risk_difference`;
  `rare_flag` for `n < 100` in either context; feature-level weighted mean and
  max absolute risk-difference changes.
- **Output:**
  - `results/tables/feature_label_stability_numeric.csv`
  - `results/tables/feature_label_stability_categorical_categories.csv`
  - `results/tables/feature_label_stability_categorical_summary.csv`
  - `results/tables/feature_label_stability_summary.json`
  - `results/logs/06_feature_label_stability.log`
  - `results/manifests/06_feature_label_stability_manifest.json`
- **Leakage controls:** descriptive only (no predictive deployment claim); the
  noise baselines contextualize the magnitude of observed shifts.

---

## Stage 7 — Synthetic positive-control sensitivity curve (`src/07_positive_control_synthetic_drift.py`)

- **Type:** diagnostic (sensitivity validation).
- **Purpose:** verify the diagnostic protocol can detect known, injected
  relationship shift of increasing magnitude.
- **Input:** `vintage_2013` and `vintage_2016`.
- **Procedure:**
  - keep `X` fixed; **do not overwrite the real `Default`**; `seed=0`.
  - create synthetic 2016 labels at three perturbation levels: **weak**,
    **medium**, **strong**, using feature-dependent label perturbation on
    `dti_n` and `fico_n` if present, with increasing relationship shift.
  - record default rate before/after and fraction of labels flipped;
    deterministic.
  - for each level: same 80/20 split logic on synthetic 2016; source model train
    real 2013 -> test synthetic-2016 held-out; oracle model train synthetic-2016
    train -> test synthetic-2016 held-out (**same held-out fold**); compute
    AUROC/AP/Brier oracle gaps; compute lightweight feature–label stability for
    perturbed features.
- **Output:**
  - `results/tables/positive_control_summary.csv`
  - `results/tables/positive_control_feature_stability.csv`
  - `results/tables/positive_control_summary.json`
  - `results/logs/07_positive_control_synthetic_drift.log`
  - `results/manifests/07_positive_control_manifest.json`
- **Leakage controls:** synthetic labels are clearly separated from the real
  target; the real `Default` column is never overwritten; oracle/source share
  the identical held-out fold.

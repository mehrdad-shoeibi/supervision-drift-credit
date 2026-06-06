# 00 — Design Lock

# Supervision-Drift Diagnostics for Proxy-Labeled Credit-Risk Decisions

**Status: LOCKED before any official experiment.**
This document is pre-registered. It must be committed to git before any official
real-data experiment is executed. It is not to be edited to match observed
results.

---

## 1. Venue and framing

- **Target venue:** HICSS-60.
- **Field framing:** Information Systems, AI governance, design-science
  diagnostic.
- **Unit of analysis:** the organizational *deployment decision* in a
  proxy-labeled credit-risk decision system — not only model accuracy.
- **Main contribution:** a transparent diagnostic protocol for distinguishing
  different forms of deployment risk in proxy-labeled decision systems.

This is **not** a paper that claims in advance that temporal AUROC must
collapse. The protocol is designed to *distinguish* multiple deployment risks:

1. discrimination / ranking degradation,
2. base-rate / prior shift,
3. calibration drift,
4. feature–label relationship instability / P(y|x) shift,
5. diagnostic sensitivity, evaluated via synthetic positive controls.

**Stable AUROC is a scientifically valid outcome.** A negative / contrastive
finding (limited evidence of harmful supervision drift) is a legitimate
contribution when paired with a demonstrably sensitive diagnostic.

---

## 2. Dataset

- **Dataset:** LendingClub loan-granting model dataset.
- **Expected raw file:** `data/raw/LC_loans_granting_model_dataset.csv`
- **Target column:** `Default`
- **Target interpretation:** `Default` is treated as an **operational /
  accounting proxy label**, not a perfect ground-truth construct of
  creditworthiness. All conclusions are framed around proxy-label deployment
  risk.
- **Date column:** `issue_d`
- **Segment axis:** `purpose`

---

## 3. Locked primary contexts

**A) In-domain.**
Train/test split **within 2013**, 80/20, `random_state=0`, stratified by
`Default` if feasible.

**B) Primary temporal transfer.**
Train on vintage **2013**, test on vintage **2016**.

**C) Primary cross-segment transfer.**
Within **2013**, train on the **largest** `purpose` segment and test on the
**second-largest** `purpose` segment.

---

## 4. Locked rule

- The primary temporal test **remains `2013 -> 2016`.**
- The primary cross-segment test **remains largest-purpose ->
  second-largest-purpose.**
- Any additional segment-pair or year-pair analyses, if ever added, must be
  **explicitly labeled exploratory sensitivity analyses** and **cannot replace**
  the locked primary tests.
- The locked primary tests are not changed after official execution.
- No search is performed for splits, segments, or vintages that produce a
  desired degradation.

---

## 5. No-leakage rules

- Fit **all** preprocessing (imputers, encoders, scalers) on **training data
  only**.
- Do **not** fit imputers, encoders, scalers, or predictive calibrators on test
  data for predictive evaluation.
- **Retrospective / oracle recalibration** may use test-context labels **only
  when explicitly labeled diagnostic** and not deployment-available. Such
  quantities are never reported as achievable deployment performance.
- Do **not** use issue year as a predictive feature.
- Do **not** use IDs, free-text description fields, or other leakage-prone
  fields as predictive features unless explicitly justified and locked here.

---

## 6. Dropped fields

The following fields are dropped if present (leakage-prone / non-predictive):

- `id`
- `title`
- `desc`

---

## 7. Models

- Logistic regression.
- Random forest.
- Histogram gradient boosting.

Seeds (locked in the analysis protocol):

- Logistic regression: run once with `seed=0`.
- Histogram gradient boosting: run once with `seed=0` unless implementation uses
  randomness.
- Random forest: run with seeds `0, 1, 2`.

---

## 8. Metrics

**Primary metric:**

- **AUROC** for discrimination / ranking.

**Secondary / diagnostic metrics:**

- Average Precision (AP).
- Brier score.
- Calibration metrics: calibration intercept, calibration slope, ECE
  (equal-frequency bins 5/10/20), decile calibration tables.
- Oracle-gap metrics (AUROC / AP / Brier).
- Feature–label stability metrics (Spearman, univariate AUROC strength,
  category risk-difference shifts), with a random-split noise baseline.
- Synthetic positive-control sensitivity curve.

---

## 9. Explicit non-assumption

The study **does not assume** temporal AUROC degradation must occur. Stable
AUROC across contexts is a valid outcome and will be reported as such. The
diagnostic protocol — and the demonstrated sensitivity of that protocol via
synthetic positive controls — is the contribution.

# Supervision-Drift Diagnostics for Proxy-Labeled Credit-Risk Decisions

A pre-specified, transparent diagnostic study of **supervision-drift risk** in
proxy-labeled credit-risk decision systems. Target venue: **HICSS-60**
(Information Systems / AI governance / design-science diagnostic).

## Project goal

This project does **not** claim in advance that temporal AUROC must collapse.
Instead it builds a *governance diagnostic protocol* that distinguishes several
distinct forms of deployment risk in proxy-labeled organizational decision
systems:

1. discrimination / ranking degradation,
2. base-rate / prior shift,
3. calibration drift,
4. feature–label relationship instability (P(y|x) shift),
5. diagnostic sensitivity, validated with synthetic positive controls.

The unit of analysis is the **organizational deployment decision**, not only
model accuracy. **Stable AUROC is a valid and expected possible outcome.**

## Scientific integrity / pre-registration

The design and analysis protocol are **locked and committed before any official
experiment is run** (see `docs/`). After official execution:

- the locked primary temporal test (`2013 -> 2016`) is not changed,
- the locked primary cross-segment test (largest -> second-largest `purpose`)
  is not changed,
- the design is not tuned after seeing results,
- no search is performed for splits that produce desired degradation,
- raw data is never modified,
- numbers are never fabricated.

## How to place the raw data

The pipeline expects the LendingClub loan-granting model dataset at:

```
data/raw/LC_loans_granting_model_dataset.csv
```

This file is **not** tracked in git. Copy it into `data/raw/` manually. Then run
`python src/00_stage_data.py` to confirm it is in place.

Required columns include the target `Default`, the date column `issue_d`, and
the segment column `purpose`. See `docs/03_data_dictionary_and_assumptions.md`.

## Official run order

> **WARNING:** Run official experiments **only after the design documents in
> `docs/` are committed and reviewed.** The protocol is pre-registered; running
> experiments before committing the design violates the integrity rules above.

```
python src/00_stage_data.py                      # confirm raw file is present
python src/01_verify_data.py                     # verify + fingerprint raw data
python src/02_build_processed_contexts.py        # build vintage/in-domain contexts
python src/03_primary_experiment.py              # PRIMARY: AUROC/AP/Brier
python src/04_oracle_gap_diagnostic.py           # diagnostic: oracle gap
python src/05_calibration_diagnostic.py          # diagnostic: calibration
python src/06_feature_label_stability.py         # diagnostic: feature-label stability
python src/07_positive_control_synthetic_drift.py# diagnostic: synthetic positive control
```

## Environment

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Repository layout

```
docs/      locked design & analysis protocol (committed before experiments)
src/       reproducible pipeline (numbered stages) + utils
data/      raw/ and processed/ (git-ignored, never committed)
results/   tables/ logs/ manifests/ (git-ignored outputs)
paper/     manuscript notes
```

Every script writes machine-readable outputs plus a manifest recording the
timestamp, command, git commit, package versions, and input file hashes for
reproducibility.

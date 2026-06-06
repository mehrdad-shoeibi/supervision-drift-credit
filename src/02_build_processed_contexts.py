"""
Stage 2 — Processed context construction.

Builds the locked analysis contexts as parquet files. Only row selection,
target coercion, column dropping, and the in-domain split happen here. No
predictive preprocessing is fit at this stage (that happens train-only inside
each modeling stage).
"""

from __future__ import annotations

import os

import pandas as pd

import utils as u


def parse_issue_dates(s: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(s, errors="coerce", format="mixed")
    if parsed.isna().mean() > 0.5:
        for fmt in ("%b-%Y", "%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
            trial = pd.to_datetime(s, errors="coerce", format=fmt)
            if trial.notna().mean() > parsed.notna().mean():
                parsed = trial
    return parsed


def main() -> None:
    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "02_build_processed_contexts.log"))
    fp = u.raw_csv_path()

    log.log("=" * 70)
    log.log("Stage 2 — Processed context construction")
    log.log("=" * 70)

    if not os.path.exists(fp):
        raise FileNotFoundError(f"Raw file not found: {fp}\nRun src/00_stage_data.py")

    df = u.load_csv(fp)
    log.log(f"loaded raw: {df.shape[0]:,} rows x {df.shape[1]} cols")

    report = {"raw_rows": int(df.shape[0]), "raw_cols": int(df.shape[1])}

    # Required columns
    for col in (u.TARGET_COL, u.DATE_COL):
        if col not in df.columns:
            raise KeyError(f"Required column missing: {col}")

    # Coerce target, drop rows with missing target
    df[u.TARGET_COL] = u.coerce_target(df[u.TARGET_COL], log)
    n_before = len(df)
    df = df[df[u.TARGET_COL].notna()].copy()
    df[u.TARGET_COL] = df[u.TARGET_COL].astype(int)
    log.log(f"dropped {n_before - len(df)} rows with missing/uncoercible target")
    report["rows_after_target_filter"] = int(len(df))

    # Parse dates, derive year (NOT a feature)
    dates = parse_issue_dates(df[u.DATE_COL])
    parse_rate = float(dates.notna().mean())
    log.log(f"issue_d parse rate: {parse_rate:.4f}")
    df[u.YEAR_COL] = dates.dt.year
    n_before = len(df)
    df = df[df[u.YEAR_COL].notna()].copy()
    df[u.YEAR_COL] = df[u.YEAR_COL].astype(int)
    log.log(f"dropped {n_before - len(df)} rows with unparseable issue_d")
    report["date_parse_rate"] = parse_rate
    report["rows_after_date_filter"] = int(len(df))

    # Drop leakage-prone columns if present
    present_drop = [c for c in u.DROP_COLS if c in df.columns]
    df = df.drop(columns=present_drop)
    log.log(f"dropped leakage-prone columns: {present_drop}")
    report["dropped_columns"] = present_drop

    # Vintage selection
    v2013 = df[df[u.YEAR_COL] == u.VINTAGE_TRAIN_YEAR].reset_index(drop=True)
    v2016 = df[df[u.YEAR_COL] == u.VINTAGE_TEST_YEAR].reset_index(drop=True)
    log.log(f"vintage {u.VINTAGE_TRAIN_YEAR}: {len(v2013):,} rows")
    log.log(f"vintage {u.VINTAGE_TEST_YEAR}: {len(v2016):,} rows")
    report["vintage_2013_rows"] = int(len(v2013))
    report["vintage_2016_rows"] = int(len(v2016))
    report["vintage_2013_default_rate"] = float(v2013[u.TARGET_COL].mean()) if len(v2013) else None
    report["vintage_2016_default_rate"] = float(v2016[u.TARGET_COL].mean()) if len(v2016) else None

    if len(v2013) == 0:
        raise ValueError("No rows in vintage 2013; cannot build in-domain contexts.")

    # In-domain 80/20 split within 2013
    train_2013, test_2013 = u.stratified_split(
        v2013, test_size=0.2, random_state=u.RANDOM_STATE, logger=log
    )
    log.log(f"in-domain 2013 train: {len(train_2013):,}  test: {len(test_2013):,}")
    report["indomain_2013_train_rows"] = int(len(train_2013))
    report["indomain_2013_test_rows"] = int(len(test_2013))

    # Segment summary (within 2013) for transparency
    if u.SEGMENT_COL in v2013.columns:
        seg_counts = v2013[u.SEGMENT_COL].value_counts(dropna=False)
        report["segment_2013_counts"] = {str(k): int(v) for k, v in seg_counts.items()}
        # locked: largest -> second-largest, ties broken alphabetically
        ordered = sorted(seg_counts.items(), key=lambda kv: (-kv[1], str(kv[0])))
        if len(ordered) >= 2:
            report["source_segment"] = str(ordered[0][0])
            report["target_segment"] = str(ordered[1][0])
            log.log(f"source segment (largest 2013 purpose): {ordered[0][0]} (n={ordered[0][1]})")
            log.log(f"target segment (second-largest 2013 purpose): {ordered[1][0]} (n={ordered[1][1]})")
        else:
            log.log("WARNING: fewer than 2 purpose segments in 2013; cross-segment test infeasible.")
    else:
        log.log(f"WARNING: segment column '{u.SEGMENT_COL}' absent; cross-segment test infeasible.")

    # Write parquet
    out = {
        "vintage_2013.parquet": v2013,
        "vintage_2016.parquet": v2016,
        "indomain_2013_train.parquet": train_2013,
        "indomain_2013_test.parquet": test_2013,
    }
    for fname, frame in out.items():
        opath = u.path("data", "processed", fname)
        frame.to_parquet(opath, index=False)
        log.log(f"wrote: {opath}  ({len(frame):,} rows)")

    u.write_json(report, u.path("data", "processed", "load_report.json"))
    log.log("wrote: data/processed/load_report.json")

    u.write_manifest(
        u.path("results", "manifests", "02_build_processed_contexts_manifest.json"),
        stage="02_build_processed_contexts",
        input_files=[fp],
        extra=report,
    )
    log.log("wrote: results/manifests/02_build_processed_contexts_manifest.json")
    log.log("\nStage 2 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("02_build_processed_contexts", main)

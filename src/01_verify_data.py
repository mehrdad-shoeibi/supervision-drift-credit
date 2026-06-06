"""
Stage 1 — Data verification.

Read-only fingerprint + description of the raw data. Never modifies raw data.
"""

from __future__ import annotations

import pandas as pd

import utils as u


def main() -> None:
    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "01_verify_data.log"))
    fp = u.raw_csv_path()

    log.log("=" * 70)
    log.log("Stage 1 — Data verification")
    log.log("=" * 70)

    if not __import__("os").path.exists(fp):
        raise FileNotFoundError(
            f"Raw file not found: {fp}\nRun: python src/00_stage_data.py"
        )

    size = u.file_size_bytes(fp)
    sha = u.sha256_file(fp)
    log.log(f"file: {fp}")
    log.log(f"size_bytes: {size:,}")
    log.log(f"sha256: {sha}")

    df = u.load_csv(fp)
    n_rows, n_cols = df.shape
    log.log(f"rows: {n_rows:,}")
    log.log(f"cols: {n_cols}")

    # columns and dtypes
    dtypes = {c: str(df[c].dtype) for c in df.columns}
    log.log("\ncolumns and dtypes:")
    for c, dt in dtypes.items():
        log.log(f"  {c}: {dt}")

    summary = {
        "file": fp,
        "size_bytes": size,
        "sha256": sha,
        "n_rows": int(n_rows),
        "n_cols": int(n_cols),
        "columns": list(df.columns),
        "dtypes": dtypes,
    }

    # target value counts
    log.log("\ntarget value counts:")
    if u.TARGET_COL in df.columns:
        raw_vc = df[u.TARGET_COL].value_counts(dropna=False).to_dict()
        coerced = u.coerce_target(df[u.TARGET_COL], log)
        coerced_vc = coerced.value_counts(dropna=False).to_dict()
        n_missing_target = int(coerced.isna().sum())
        log.log(f"  raw: {raw_vc}")
        log.log(f"  coerced_to_{{0,1}}: {coerced_vc}")
        log.log(f"  uncoercible/missing target rows: {n_missing_target}")
        summary["target"] = {
            "present": True,
            "raw_value_counts": {str(k): int(v) for k, v in raw_vc.items()},
            "coerced_value_counts": {str(k): int(v) for k, v in coerced_vc.items()},
            "missing_or_uncoercible": n_missing_target,
        }
    else:
        log.log(f"  WARNING: target column '{u.TARGET_COL}' NOT present!")
        summary["target"] = {"present": False}

    # date parse rate
    log.log("\ndate parsing (issue_d):")
    if u.DATE_COL in df.columns:
        parsed = pd.to_datetime(df[u.DATE_COL], errors="coerce", format="mixed")
        if parsed.isna().mean() > 0.5:
            # retry with common LendingClub formats
            for fmt in ("%b-%Y", "%b-%y", "%Y-%m-%d", "%m/%d/%Y"):
                trial = pd.to_datetime(df[u.DATE_COL], errors="coerce", format=fmt)
                if trial.notna().mean() > parsed.notna().mean():
                    parsed = trial
        parse_rate = float(parsed.notna().mean())
        years = parsed.dt.year
        year_counts = years.value_counts(dropna=True).sort_index().to_dict()
        log.log(f"  parse_rate: {parse_rate:.4f}")
        log.log(f"  year_counts: {year_counts}")
        summary["issue_d"] = {
            "present": True,
            "parse_rate": parse_rate,
            "year_counts": {int(k): int(v) for k, v in year_counts.items()},
        }
        for yr in (u.VINTAGE_TRAIN_YEAR, u.VINTAGE_TEST_YEAR):
            log.log(f"  rows in {yr}: {int((years == yr).sum())}")
    else:
        log.log(f"  WARNING: date column '{u.DATE_COL}' NOT present!")
        summary["issue_d"] = {"present": False}

    # purpose counts
    log.log("\nsegment (purpose) counts:")
    if u.SEGMENT_COL in df.columns:
        pc = df[u.SEGMENT_COL].value_counts(dropna=False).to_dict()
        for k, v in pc.items():
            log.log(f"  {k}: {v}")
        summary["purpose"] = {
            "present": True,
            "value_counts": {str(k): int(v) for k, v in pc.items()},
        }
    else:
        log.log(f"  WARNING: segment column '{u.SEGMENT_COL}' NOT present!")
        summary["purpose"] = {"present": False}

    # dropped-field presence
    present_drop = [c for c in u.DROP_COLS if c in df.columns]
    log.log(f"\nleakage-prone columns present (will be dropped downstream): {present_drop}")
    summary["drop_cols_present"] = present_drop

    out_json = u.path("results", "tables", "data_verification_summary.json")
    u.write_json(summary, out_json)
    log.log(f"\nwrote: {out_json}")

    u.write_manifest(
        u.path("results", "manifests", "01_verify_data_manifest.json"),
        stage="01_verify_data",
        input_files=[fp],
        extra={"n_rows": int(n_rows), "n_cols": int(n_cols)},
    )
    log.log("wrote: results/manifests/01_verify_data_manifest.json")
    log.log("\nStage 1 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("01_verify_data", main)

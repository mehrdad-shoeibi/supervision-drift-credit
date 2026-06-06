"""
Stage 5 — Calibration diagnostic.

For each locked context / model / seed: characterize RAW probability
calibration, then a DIAGNOSTIC intercept/base-rate recalibration that uses the
observed test-context default rate (not deployment-available).

Contexts: A) in-domain, B) temporal, C) cross-segment.
"""

from __future__ import annotations

import utils as u


def calib_block(prefix: str, y_true, p) -> dict:
    """Compute the calibration metric block for one probability vector."""
    import numpy as np
    cs = u.calibration_intercept_slope(y_true, p)
    out = {
        f"{prefix}_auroc": u.auroc(y_true, p),
        f"{prefix}_ap": u.average_precision(y_true, p),
        f"{prefix}_brier": u.brier(y_true, p),
        f"{prefix}_mean_pred": float(np.mean(p)),
        f"{prefix}_observed_rate": float(np.mean(y_true)),
        f"{prefix}_cal_intercept": cs["intercept"],
        f"{prefix}_cal_slope": cs["slope"],
        f"{prefix}_cal_warning": cs["warning"],
        f"{prefix}_ece5": u.ece_equal_frequency(y_true, p, 5),
        f"{prefix}_ece10": u.ece_equal_frequency(y_true, p, 10),
        f"{prefix}_ece20": u.ece_equal_frequency(y_true, p, 20),
    }
    return out


def evaluate(context, train_df, test_df, *, include_segment, log, decile_rows):
    numeric, categorical = u.common_features(train_df, test_df, include_segment=include_segment)
    y_test = test_df[u.TARGET_COL].astype(int).values
    obs_rate = float(y_test.mean())
    rows = []
    for model_name, seeds in u.model_specs():
        for seed in seeds:
            pipe = u.build_pipeline(model_name, numeric, categorical, seed=seed)
            p_raw = u.fit_predict_proba(pipe, train_df, test_df, numeric, categorical)

            # diagnostic recalibration to match observed test default rate
            p_recal, delta = u.base_rate_recalibrate(p_raw, obs_rate)

            row = {"context": context, "model": model_name, "seed": seed,
                   "test_n": int(len(test_df)), "recal_delta": float(delta)}
            row.update(calib_block("raw", y_test, p_raw))
            row.update(calib_block("recal", y_test, p_recal))
            # improvement summaries
            row["ece10_improvement"] = row["raw_ece10"] - row["recal_ece10"]
            row["brier_improvement"] = row["raw_brier"] - row["recal_brier"]
            rows.append(row)
            log.log(f"    {model_name} seed={seed}: raw ECE10={row['raw_ece10']:.4f} "
                    f"intercept={row['raw_cal_intercept']:.3f} slope={row['raw_cal_slope']:.3f} "
                    f"-> recal ECE10={row['recal_ece10']:.4f} (delta={delta:+.3f})")

            # decile tables (raw and recal)
            for kind, p in (("raw", p_raw), ("recal", p_recal)):
                for d in u.decile_calibration_table(y_test, p, 10):
                    decile_rows.append({"context": context, "model": model_name,
                                        "seed": seed, "prob_kind": kind, **d})
    return rows


def main() -> None:
    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "05_calibration_diagnostic.log"))
    log.log("=" * 70)
    log.log("Stage 5 — Calibration diagnostic")
    log.log("=" * 70)

    ctx = u.load_processed()
    import pandas as pd
    all_rows, decile_rows = [], []

    log.log("\nContext A — in-domain:")
    all_rows += evaluate("in_domain", ctx["indomain_2013_train"], ctx["indomain_2013_test"],
                         include_segment=True, log=log, decile_rows=decile_rows)

    log.log("\nContext B — temporal:")
    all_rows += evaluate("temporal", ctx["vintage_2013"], ctx["vintage_2016"],
                         include_segment=True, log=log, decile_rows=decile_rows)

    log.log("\nContext C — cross-segment:")
    source_seg, target_seg = u.resolve_segments(ctx["vintage_2013"], log)
    src_df = u.segment_frame(ctx["vintage_2013"], source_seg)
    tgt_df = u.segment_frame(ctx["vintage_2013"], target_seg)
    cs_rows = evaluate("cross_segment", src_df, tgt_df,
                       include_segment=False, log=log, decile_rows=decile_rows)
    for r in cs_rows:
        r["source_segment"] = source_seg
        r["target_segment"] = target_seg
    all_rows += cs_rows

    u.write_csv(pd.DataFrame(all_rows), u.path("results", "tables", "calibration_summary.csv"))
    u.write_csv(pd.DataFrame(decile_rows), u.path("results", "tables", "calibration_deciles.csv"))
    u.write_json({"results": all_rows,
                  "cross_segment": {"source": source_seg, "target": target_seg}},
                 u.path("results", "tables", "calibration_summary.json"))
    log.log("\nwrote: results/tables/calibration_summary.csv / calibration_deciles.csv / .json")

    u.write_manifest(
        u.path("results", "manifests", "05_calibration_manifest.json"),
        stage="05_calibration_diagnostic",
        input_files=[u.path("data", "processed", f) for f in
                     ("vintage_2013.parquet", "vintage_2016.parquet",
                      "indomain_2013_train.parquet", "indomain_2013_test.parquet")],
        extra={"source_segment": source_seg, "target_segment": target_seg,
               "n_result_rows": len(all_rows)},
    )
    log.log("wrote: results/manifests/05_calibration_manifest.json")
    log.log("\nStage 5 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("05_calibration_diagnostic", main)

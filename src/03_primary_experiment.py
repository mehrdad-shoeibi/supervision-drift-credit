"""
Stage 3 — Primary experiment (PRIMARY).

Measures discrimination/ranking (AUROC, primary) plus Average Precision and
Brier across the three locked contexts:
  A) in-domain   : indomain_2013_train -> indomain_2013_test
  B) temporal    : vintage_2013 -> vintage_2016
  C) cross-seg   : largest 2013 purpose -> second-largest 2013 purpose

Models/seeds (locked): logreg[0], hgb[0], rf[0,1,2].
Bootstrap AUROC CIs on the test set (default 2000).
"""

from __future__ import annotations

import argparse

import utils as u


def evaluate(context: str, train_df, test_df, *, include_segment: bool, n_boot: int, log):
    numeric, categorical = u.common_features(train_df, test_df, include_segment=include_segment)
    log.log(f"  [{context}] features: {len(numeric)} numeric, {len(categorical)} categorical")
    log.log(f"  [{context}] train n={len(train_df):,} (default rate {train_df[u.TARGET_COL].mean():.4f}); "
            f"test n={len(test_df):,} (default rate {test_df[u.TARGET_COL].mean():.4f})")
    rows = []
    y_test = test_df[u.TARGET_COL].astype(int).values
    for model_name, seeds in u.model_specs():
        for seed in seeds:
            pipe = u.build_pipeline(model_name, numeric, categorical, seed=seed)
            p = u.fit_predict_proba(pipe, train_df, test_df, numeric, categorical)
            m = u.core_metrics(y_test, p)
            ci = u.bootstrap_auroc_ci(y_test, p, n_boot=n_boot, random_state=u.RANDOM_STATE)
            row = {
                "context": context,
                "model": model_name,
                "seed": seed,
                "train_n": int(len(train_df)),
                "test_n": int(len(test_df)),
                "train_default_rate": float(train_df[u.TARGET_COL].mean()),
                "test_default_rate": float(test_df[u.TARGET_COL].mean()),
                "auroc": m["auroc"],
                "auroc_ci_lo": ci["ci_lo"],
                "auroc_ci_hi": ci["ci_hi"],
                "auroc_n_boot": ci["n_boot"],
                "average_precision": m["average_precision"],
                "brier": m["brier"],
            }
            rows.append(row)
            log.log(f"    {model_name} seed={seed}: AUROC={m['auroc']:.4f} "
                    f"[{ci['ci_lo']:.4f},{ci['ci_hi']:.4f}] "
                    f"AP={m['average_precision']:.4f} Brier={m['brier']:.4f}")
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap", type=int, default=2000,
                    help="Bootstrap resamples for AUROC CI (default 2000).")
    args = ap.parse_args()

    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "03_primary_experiment.log"))
    log.log("=" * 70)
    log.log("Stage 3 — Primary experiment")
    log.log("=" * 70)
    log.log(f"bootstrap resamples: {args.bootstrap}")
    if args.bootstrap >= 2000:
        log.log("NOTE: bootstrap CIs at this setting may be computationally expensive "
                "across all model/seed/context combinations.")

    ctx = u.load_processed()
    import pandas as pd

    all_rows = []

    log.log("\nContext A — in-domain (2013 train -> 2013 test):")
    all_rows += evaluate("in_domain", ctx["indomain_2013_train"], ctx["indomain_2013_test"],
                         include_segment=True, n_boot=args.bootstrap, log=log)

    log.log("\nContext B — temporal (vintage 2013 -> vintage 2016):")
    all_rows += evaluate("temporal", ctx["vintage_2013"], ctx["vintage_2016"],
                         include_segment=True, n_boot=args.bootstrap, log=log)

    log.log("\nContext C — cross-segment (largest 2013 purpose -> second-largest):")
    source_seg, target_seg = u.resolve_segments(ctx["vintage_2013"], log)
    src_df = u.segment_frame(ctx["vintage_2013"], source_seg)
    tgt_df = u.segment_frame(ctx["vintage_2013"], target_seg)
    # purpose is constant within each segment -> exclude as feature here
    cs_rows = evaluate("cross_segment", src_df, tgt_df,
                       include_segment=False, n_boot=args.bootstrap, log=log)
    for r in cs_rows:
        r["source_segment"] = source_seg
        r["target_segment"] = target_seg
    all_rows += cs_rows

    df = pd.DataFrame(all_rows)
    u.write_csv(df, u.path("results", "tables", "primary_experiment_results.csv"))
    u.write_json({"results": all_rows,
                  "cross_segment": {"source": source_seg, "target": target_seg}},
                 u.path("results", "tables", "primary_experiment_results.json"))
    log.log("\nwrote: results/tables/primary_experiment_results.csv / .json")

    u.write_manifest(
        u.path("results", "manifests", "03_primary_experiment_manifest.json"),
        stage="03_primary_experiment",
        input_files=[u.path("data", "processed", f) for f in
                     ("vintage_2013.parquet", "vintage_2016.parquet",
                      "indomain_2013_train.parquet", "indomain_2013_test.parquet")],
        extra={"bootstrap": args.bootstrap, "source_segment": source_seg,
               "target_segment": target_seg, "n_result_rows": len(all_rows)},
    )
    log.log("wrote: results/manifests/03_primary_experiment_manifest.json")
    log.log("\nStage 3 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("03_primary_experiment", main)

"""
Stage 4 — Oracle-gap diagnostic.

Isolates achievable performance loss from domain shift by comparing a
source-trained model against an oracle target-trained model, BOTH evaluated on
the EXACT SAME held-out target test fold.

Temporal:     source = all vintage_2013 ; oracle = target_train_2016
              both tested on target_test_2016 (fixed 80/20 of vintage_2016).
Cross-segment:source = all source segment ; oracle = target_segment_train
              both tested on target_segment_test (fixed 80/20 of target seg).
"""

from __future__ import annotations

import utils as u


def oracle_pair(comparison, source_train, target_train, target_test, *, include_segment, log):
    """Train source and oracle; evaluate both on the SAME target_test."""
    y_test = target_test[u.TARGET_COL].astype(int).values
    rows = []
    for model_name, seeds in u.model_specs():
        for seed in seeds:
            # source model: source_train -> target_test
            num_s, cat_s = u.common_features(source_train, target_test, include_segment=include_segment)
            pipe_s = u.build_pipeline(model_name, num_s, cat_s, seed=seed)
            p_src = u.fit_predict_proba(pipe_s, source_train, target_test, num_s, cat_s)
            m_src = u.core_metrics(y_test, p_src)

            # oracle model: target_train -> SAME target_test
            num_o, cat_o = u.common_features(target_train, target_test, include_segment=include_segment)
            pipe_o = u.build_pipeline(model_name, num_o, cat_o, seed=seed)
            p_orc = u.fit_predict_proba(pipe_o, target_train, target_test, num_o, cat_o)
            m_orc = u.core_metrics(y_test, p_orc)

            row = {
                "comparison": comparison,
                "model": model_name,
                "seed": seed,
                "target_test_n": int(len(target_test)),
                "target_test_default_rate": float(target_test[u.TARGET_COL].mean()),
                "source_train_n": int(len(source_train)),
                "oracle_train_n": int(len(target_train)),
                "source_auroc": m_src["auroc"],
                "oracle_auroc": m_orc["auroc"],
                "oracle_gap_auroc": m_orc["auroc"] - m_src["auroc"],
                "source_ap": m_src["average_precision"],
                "oracle_ap": m_orc["average_precision"],
                "oracle_gap_ap": m_orc["average_precision"] - m_src["average_precision"],
                "source_brier": m_src["brier"],
                "oracle_brier": m_orc["brier"],
                "oracle_gap_brier": m_src["brier"] - m_orc["brier"],
            }
            rows.append(row)
            log.log(f"    {model_name} seed={seed}: "
                    f"AUROC src={m_src['auroc']:.4f} orc={m_orc['auroc']:.4f} "
                    f"gap={row['oracle_gap_auroc']:+.4f} | "
                    f"Brier gap={row['oracle_gap_brier']:+.4f}")
    return rows


def main() -> None:
    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "04_oracle_gap_diagnostic.log"))
    log.log("=" * 70)
    log.log("Stage 4 — Oracle-gap diagnostic")
    log.log("=" * 70)

    ctx = u.load_processed()
    import pandas as pd
    all_rows = []

    # ---- Temporal oracle gap ----
    log.log("\nTemporal oracle gap (source=all 2013, oracle=2016 train, test=2016 held-out):")
    v2016 = ctx["vintage_2016"]
    if len(v2016) == 0:
        raise ValueError("vintage_2016 is empty; temporal oracle gap infeasible.")
    tgt_train_2016, tgt_test_2016 = u.stratified_split(
        v2016, test_size=0.2, random_state=u.RANDOM_STATE, logger=log
    )
    log.log(f"  target_test_2016 n={len(tgt_test_2016):,}")
    all_rows += oracle_pair(
        "temporal",
        source_train=ctx["vintage_2013"],
        target_train=tgt_train_2016,
        target_test=tgt_test_2016,
        include_segment=True,
        log=log,
    )

    # ---- Cross-segment oracle gap ----
    log.log("\nCross-segment oracle gap (source=all source seg, oracle=target seg train, "
            "test=target seg held-out):")
    source_seg, target_seg = u.resolve_segments(ctx["vintage_2013"], log)
    src_df = u.segment_frame(ctx["vintage_2013"], source_seg)
    tgt_df = u.segment_frame(ctx["vintage_2013"], target_seg)
    tgt_seg_train, tgt_seg_test = u.stratified_split(
        tgt_df, test_size=0.2, random_state=u.RANDOM_STATE, logger=log
    )
    log.log(f"  target_segment_test n={len(tgt_seg_test):,}")
    cs_rows = oracle_pair(
        "cross_segment",
        source_train=src_df,
        target_train=tgt_seg_train,
        target_test=tgt_seg_test,
        include_segment=False,
        log=log,
    )
    for r in cs_rows:
        r["source_segment"] = source_seg
        r["target_segment"] = target_seg
    all_rows += cs_rows

    df = pd.DataFrame(all_rows)
    u.write_csv(df, u.path("results", "tables", "oracle_gap_summary.csv"))
    u.write_json({"results": all_rows,
                  "cross_segment": {"source": source_seg, "target": target_seg}},
                 u.path("results", "tables", "oracle_gap_summary.json"))
    log.log("\nwrote: results/tables/oracle_gap_summary.csv / .json")

    u.write_manifest(
        u.path("results", "manifests", "04_oracle_gap_manifest.json"),
        stage="04_oracle_gap_diagnostic",
        input_files=[u.path("data", "processed", f) for f in
                     ("vintage_2013.parquet", "vintage_2016.parquet")],
        extra={"source_segment": source_seg, "target_segment": target_seg,
               "n_result_rows": len(all_rows)},
    )
    log.log("wrote: results/manifests/04_oracle_gap_manifest.json")
    log.log("\nStage 4 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("04_oracle_gap_diagnostic", main)

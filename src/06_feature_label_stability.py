"""
Stage 6 — Feature-label stability diagnostic.

Descriptive (non-predictive) measurement of feature-label relationship
instability between two contexts (A vs B), with random-split noise baselines for
reference scale.

Comparisons:
  1. temporal                    : vintage_2013 (A) vs vintage_2016 (B)
  2. cross_segment               : largest 2013 purpose (A) vs 2nd-largest (B)
  3. temporal_noise_baseline     : vintage_2013 split into two random halves
  4. cross_segment_noise_baseline: largest 2013 purpose split into two halves
"""

from __future__ import annotations

import numpy as np

import utils as u


def numeric_stability(comparison, A, B, numeric, log):
    rows = []
    yA = A[u.TARGET_COL].astype(int).values
    yB = B[u.TARGET_COL].astype(int).values
    for col in numeric:
        sp_A = u.spearman_with_target(A[col].values, yA)
        sp_B = u.spearman_with_target(B[col].values, yB)
        auc_A = u.univariate_auc_strength(A[col].values, yA)
        auc_B = u.univariate_auc_strength(B[col].values, yB)
        rows.append({
            "comparison": comparison, "feature": col,
            "spearman_A": sp_A, "spearman_B": sp_B,
            "delta_abs_spearman": abs(sp_A - sp_B) if not (np.isnan(sp_A) or np.isnan(sp_B)) else np.nan,
            "auc_strength_A": auc_A, "auc_strength_B": auc_B,
            "delta_abs_auc_strength": abs(auc_A - auc_B) if not (np.isnan(auc_A) or np.isnan(auc_B)) else np.nan,
        })
    log.log(f"  [{comparison}] numeric features assessed: {len(rows)}")
    return rows


def categorical_stability(comparison, A, B, categorical, log):
    """Reference categories from context A only."""
    cat_rows, summ_rows = [], []
    yA = A[u.TARGET_COL].astype(int)
    yB = B[u.TARGET_COL].astype(int)
    base_A = float(yA.mean())
    base_B = float(yB.mean())
    nA, nB = len(A), len(B)
    for col in categorical:
        ref_cats = A[col].astype("string").fillna("__NA__").unique().tolist()
        a_vals = A[col].astype("string").fillna("__NA__")
        b_vals = B[col].astype("string").fillna("__NA__")
        weighted_num, weight_den, max_delta = 0.0, 0.0, 0.0
        for cat in ref_cats:
            mA = a_vals == cat
            mB = b_vals == cat
            cntA, cntB = int(mA.sum()), int(mB.sum())
            prevA = cntA / nA if nA else np.nan
            prevB = cntB / nB if nB else np.nan
            rateA = float(yA[mA.values].mean()) if cntA > 0 else np.nan
            rateB = float(yB[mB.values].mean()) if cntB > 0 else np.nan
            rdA = rateA - base_A if not np.isnan(rateA) else np.nan
            rdB = rateB - base_B if not np.isnan(rateB) else np.nan
            if not (np.isnan(rdA) or np.isnan(rdB)):
                delta_rd = abs(rdA - rdB)
            else:
                delta_rd = np.nan
            rare = (cntA < 100) or (cntB < 100)
            cat_rows.append({
                "comparison": comparison, "feature": col, "category": cat,
                "count_A": cntA, "count_B": cntB,
                "prevalence_A": prevA, "prevalence_B": prevB,
                "default_rate_A": rateA, "default_rate_B": rateB,
                "base_rate_A": base_A, "base_rate_B": base_B,
                "risk_diff_A": rdA, "risk_diff_B": rdB,
                "delta_abs_risk_difference": delta_rd,
                "rare_flag": bool(rare),
            })
            if not np.isnan(delta_rd):
                weighted_num += (prevA if not np.isnan(prevA) else 0.0) * delta_rd
                weight_den += (prevA if not np.isnan(prevA) else 0.0)
                max_delta = max(max_delta, delta_rd)
        summ_rows.append({
            "comparison": comparison, "feature": col,
            "n_reference_categories": len(ref_cats),
            "weighted_mean_abs_risk_diff_change": (weighted_num / weight_den) if weight_den > 0 else np.nan,
            "max_abs_risk_diff_change": max_delta if weight_den > 0 else np.nan,
        })
    log.log(f"  [{comparison}] categorical features assessed: {len(summ_rows)}")
    return cat_rows, summ_rows


def run_comparison(comparison, A, B, log):
    numeric, categorical = u.common_features(A, B, include_segment=True)
    # Drop a categorical feature only when it is the comparison axis itself and
    # is constant on a side (e.g. `purpose` in the cross-segment comparison).
    def keep(c):
        if c == u.SEGMENT_COL and (A[c].nunique() <= 1 or B[c].nunique() <= 1):
            return False
        return True
    cat = [c for c in categorical if keep(c)]
    num_rows = numeric_stability(comparison, A, B, numeric, log)
    cat_rows, summ_rows = categorical_stability(comparison, A, B, cat, log)
    return num_rows, cat_rows, summ_rows


def main() -> None:
    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "06_feature_label_stability.log"))
    log.log("=" * 70)
    log.log("Stage 6 — Feature-label stability diagnostic")
    log.log("=" * 70)

    ctx = u.load_processed()
    import pandas as pd
    num_all, cat_all, summ_all = [], [], []

    # 1. temporal
    log.log("\n[1] temporal: vintage_2013 vs vintage_2016")
    n, c, s = run_comparison("temporal", ctx["vintage_2013"], ctx["vintage_2016"], log)
    num_all += n; cat_all += c; summ_all += s

    # 2. cross_segment
    log.log("\n[2] cross_segment: largest vs second-largest 2013 purpose")
    source_seg, target_seg = u.resolve_segments(ctx["vintage_2013"], log)
    src_df = u.segment_frame(ctx["vintage_2013"], source_seg)
    tgt_df = u.segment_frame(ctx["vintage_2013"], target_seg)
    n, c, s = run_comparison("cross_segment", src_df, tgt_df, log)
    num_all += n; cat_all += c; summ_all += s

    # 3. temporal_noise_baseline: split vintage_2013 into two random halves
    log.log("\n[3] temporal_noise_baseline: vintage_2013 random halves")
    h1, h2 = u.stratified_split(ctx["vintage_2013"], test_size=0.5,
                                random_state=u.RANDOM_STATE, logger=log)
    n, c, s = run_comparison("temporal_noise_baseline", h1, h2, log)
    num_all += n; cat_all += c; summ_all += s

    # 4. cross_segment_noise_baseline: split largest 2013 purpose into halves
    log.log("\n[4] cross_segment_noise_baseline: largest 2013 purpose random halves")
    h1s, h2s = u.stratified_split(src_df, test_size=0.5,
                                  random_state=u.RANDOM_STATE, logger=log)
    n, c, s = run_comparison("cross_segment_noise_baseline", h1s, h2s, log)
    num_all += n; cat_all += c; summ_all += s

    u.write_csv(pd.DataFrame(num_all),
                u.path("results", "tables", "feature_label_stability_numeric.csv"))
    u.write_csv(pd.DataFrame(cat_all),
                u.path("results", "tables", "feature_label_stability_categorical_categories.csv"))
    u.write_csv(pd.DataFrame(summ_all),
                u.path("results", "tables", "feature_label_stability_categorical_summary.csv"))

    # JSON summary: per-comparison aggregate deltas (for decision-rule reference)
    def agg(comparison):
        nd = pd.DataFrame(num_all)
        sd = pd.DataFrame(summ_all)
        nd = nd[nd["comparison"] == comparison] if len(nd) else nd
        sd = sd[sd["comparison"] == comparison] if len(sd) else sd
        return {
            "numeric_mean_delta_abs_spearman": float(np.nanmean(nd["delta_abs_spearman"])) if len(nd) else None,
            "numeric_mean_delta_abs_auc_strength": float(np.nanmean(nd["delta_abs_auc_strength"])) if len(nd) else None,
            "numeric_max_delta_abs_auc_strength": float(np.nanmax(nd["delta_abs_auc_strength"])) if len(nd) else None,
            "categorical_mean_weighted_risk_diff_change": float(np.nanmean(sd["weighted_mean_abs_risk_diff_change"])) if len(sd) else None,
            "categorical_max_risk_diff_change": float(np.nanmax(sd["max_abs_risk_diff_change"])) if len(sd) else None,
        }

    comparisons = ["temporal", "cross_segment",
                   "temporal_noise_baseline", "cross_segment_noise_baseline"]
    summary_json = {"by_comparison": {c: agg(c) for c in comparisons},
                    "cross_segment": {"source": source_seg, "target": target_seg}}
    u.write_json(summary_json,
                 u.path("results", "tables", "feature_label_stability_summary.json"))
    log.log("\nwrote: feature_label_stability_numeric.csv / "
            "categorical_categories.csv / categorical_summary.csv / summary.json")

    u.write_manifest(
        u.path("results", "manifests", "06_feature_label_stability_manifest.json"),
        stage="06_feature_label_stability",
        input_files=[u.path("data", "processed", f) for f in
                     ("vintage_2013.parquet", "vintage_2016.parquet")],
        extra={"source_segment": source_seg, "target_segment": target_seg},
    )
    log.log("wrote: results/manifests/06_feature_label_stability_manifest.json")
    log.log("\nStage 6 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("06_feature_label_stability", main)

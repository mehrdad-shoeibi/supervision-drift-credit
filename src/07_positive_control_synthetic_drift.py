"""
Stage 7 — Synthetic positive-control sensitivity curve.

Validates diagnostic SENSITIVITY by injecting a known feature-dependent
relationship shift of increasing magnitude into synthetic 2016 labels, then
checking that the oracle-gap / stability diagnostics respond monotonically.

Rules:
  - X is kept fixed (real 2016 features).
  - The real `Default` column is NEVER overwritten; synthetic labels live in a
    separate column.
  - Deterministic (seed=0).
  - Perturbation is feature-dependent, using dti_n and fico_n if present.
"""

from __future__ import annotations

import numpy as np

import utils as u

# Locked perturbation levels: fraction of labels redefined by the synthetic
# feature-driven relationship. Increasing weak -> medium -> strong.
LEVELS = {"weak": 0.05, "medium": 0.15, "strong": 0.30}
PERTURB_FEATURES = ["dti_n", "fico_n"]


def zscore(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    mu = np.nanmean(x)
    sd = np.nanstd(x)
    if not np.isfinite(sd) or sd == 0:
        return np.zeros_like(x)
    z = (x - mu) / sd
    return np.nan_to_num(z, nan=0.0)


def synthetic_labels(df, perturb_feats, frac, base_rate, log):
    """
    Deterministic feature-dependent synthetic labels.

    risk = z(dti_n) - z(fico_n)  (higher DTI / lower FICO -> higher risk)
    y_feat = 1 for the highest-risk rows, matching the real base rate.
    A deterministic fraction `frac` of rows have their label REPLACED by y_feat;
    the rest keep the real label. Larger frac -> stronger relationship shift.
    """
    n = len(df)
    risk = np.zeros(n, dtype=float)
    for f in perturb_feats:
        if f == "fico_n":
            risk -= zscore(df[f].values)
        else:
            risk += zscore(df[f].values)

    # threshold so y_feat base rate ~ real base rate
    k = int(round(base_rate * n))
    k = min(max(k, 0), n)
    order = np.argsort(-risk)  # descending risk
    y_feat = np.zeros(n, dtype=int)
    if k > 0:
        y_feat[order[:k]] = 1

    y_real = df[u.TARGET_COL].astype(int).values
    # deterministic selection of which rows are overwritten
    rng = np.random.default_rng(u.RANDOM_STATE)
    perm = rng.permutation(n)
    n_overwrite = int(round(frac * n))
    overwrite_idx = perm[:n_overwrite]
    y_syn = y_real.copy()
    y_syn[overwrite_idx] = y_feat[overwrite_idx]

    frac_flipped = float(np.mean(y_syn != y_real))
    log.log(f"    base_rate real={y_real.mean():.4f} syn={y_syn.mean():.4f} "
            f"overwrite_frac={frac:.2f} actual_flipped={frac_flipped:.4f}")
    return y_syn, frac_flipped


def lightweight_stability(df_2013, df_2016_syn_label, perturb_feats):
    """Spearman + AUC strength of perturbed features vs real-2013 vs synthetic-2016."""
    rows = []
    y13 = df_2013[u.TARGET_COL].astype(int).values
    y16 = df_2016_syn_label["_y_syn"].astype(int).values
    for f in perturb_feats:
        sp13 = u.spearman_with_target(df_2013[f].values, y13)
        sp16 = u.spearman_with_target(df_2016_syn_label[f].values, y16)
        a13 = u.univariate_auc_strength(df_2013[f].values, y13)
        a16 = u.univariate_auc_strength(df_2016_syn_label[f].values, y16)
        rows.append({
            "feature": f,
            "spearman_real2013": sp13, "spearman_syn2016": sp16,
            "delta_abs_spearman": abs(sp13 - sp16),
            "auc_strength_real2013": a13, "auc_strength_syn2016": a16,
            "delta_abs_auc_strength": abs(a13 - a16),
        })
    return rows


def main() -> None:
    u.ensure_dirs()
    log = u.Logger(u.path("results", "logs", "07_positive_control_synthetic_drift.log"))
    log.log("=" * 70)
    log.log("Stage 7 — Synthetic positive-control sensitivity curve")
    log.log("=" * 70)

    ctx = u.load_processed()
    import pandas as pd
    v2013 = ctx["vintage_2013"]
    v2016 = ctx["vintage_2016"]
    if len(v2016) == 0:
        raise ValueError("vintage_2016 is empty; positive control infeasible.")

    perturb_feats = [f for f in PERTURB_FEATURES if f in v2016.columns and f in v2013.columns]
    if not perturb_feats:
        raise KeyError(
            f"None of the perturbation features {PERTURB_FEATURES} are present in both "
            "vintages; the locked positive-control design requires dti_n and/or fico_n."
        )
    log.log(f"perturbation features used: {perturb_feats}")

    base_rate = float(v2016[u.TARGET_COL].mean())
    numeric, categorical = u.common_features(v2013, v2016, include_segment=True)

    summary_rows, stab_rows = [], []

    for level, frac in LEVELS.items():
        log.log(f"\n--- level={level} (overwrite fraction {frac}) ---")
        y_syn, frac_flipped = synthetic_labels(v2016, perturb_feats, frac, base_rate, log)

        # synthetic-labeled 2016 frame: X fixed, separate synthetic label column
        syn = v2016.copy()
        syn["_y_syn"] = y_syn

        # 80/20 split of synthetic 2016, stratified on synthetic label
        syn_for_split = syn.copy()
        # temporarily expose synthetic label as TARGET_COL for the shared splitter,
        # without ever touching the real Default on disk
        syn_split = syn_for_split.rename(columns={u.TARGET_COL: "_default_real"})
        syn_split = syn_split.rename(columns={"_y_syn": u.TARGET_COL})
        syn_train, syn_test = u.stratified_split(
            syn_split, test_size=0.2, random_state=u.RANDOM_STATE, logger=log
        )
        log.log(f"    syn_train n={len(syn_train):,} syn_test n={len(syn_test):,}")

        y_test = syn_test[u.TARGET_COL].astype(int).values

        for model_name, seeds in u.model_specs():
            for seed in seeds:
                # source: real 2013 (real labels) -> synthetic-2016 held-out
                num_s, cat_s = u.common_features(v2013, syn_test, include_segment=True)
                pipe_s = u.build_pipeline(model_name, num_s, cat_s, seed=seed)
                p_src = u.fit_predict_proba(pipe_s, v2013, syn_test, num_s, cat_s)
                m_src = u.core_metrics(y_test, p_src)

                # oracle: synthetic-2016 train -> SAME synthetic-2016 held-out
                num_o, cat_o = u.common_features(syn_train, syn_test, include_segment=True)
                pipe_o = u.build_pipeline(model_name, num_o, cat_o, seed=seed)
                p_orc = u.fit_predict_proba(pipe_o, syn_train, syn_test, num_o, cat_o)
                m_orc = u.core_metrics(y_test, p_orc)

                row = {
                    "level": level, "overwrite_fraction": frac,
                    "fraction_flipped": frac_flipped,
                    "syn_base_rate": float(y_syn.mean()),
                    "real_base_rate": base_rate,
                    "model": model_name, "seed": seed,
                    "target_test_n": int(len(syn_test)),
                    "source_auroc": m_src["auroc"], "oracle_auroc": m_orc["auroc"],
                    "oracle_gap_auroc": m_orc["auroc"] - m_src["auroc"],
                    "source_ap": m_src["average_precision"], "oracle_ap": m_orc["average_precision"],
                    "oracle_gap_ap": m_orc["average_precision"] - m_src["average_precision"],
                    "source_brier": m_src["brier"], "oracle_brier": m_orc["brier"],
                    "oracle_gap_brier": m_src["brier"] - m_orc["brier"],
                }
                summary_rows.append(row)
                log.log(f"    {model_name} seed={seed}: "
                        f"AUROC src={m_src['auroc']:.4f} orc={m_orc['auroc']:.4f} "
                        f"gap={row['oracle_gap_auroc']:+.4f}")

        # lightweight stability for perturbed features at this level
        for s in lightweight_stability(v2013, syn, perturb_feats):
            stab_rows.append({"level": level, **s})

    u.write_csv(pd.DataFrame(summary_rows),
                u.path("results", "tables", "positive_control_summary.csv"))
    u.write_csv(pd.DataFrame(stab_rows),
                u.path("results", "tables", "positive_control_feature_stability.csv"))
    u.write_json({"levels": LEVELS, "perturbation_features": perturb_feats,
                  "results": summary_rows, "feature_stability": stab_rows},
                 u.path("results", "tables", "positive_control_summary.json"))
    log.log("\nwrote: positive_control_summary.csv / feature_stability.csv / summary.json")

    u.write_manifest(
        u.path("results", "manifests", "07_positive_control_manifest.json"),
        stage="07_positive_control_synthetic_drift",
        input_files=[u.path("data", "processed", f) for f in
                     ("vintage_2013.parquet", "vintage_2016.parquet")],
        extra={"levels": LEVELS, "perturbation_features": perturb_feats},
    )
    log.log("wrote: results/manifests/07_positive_control_manifest.json")
    log.log("\nStage 7 complete.")
    log.close()


if __name__ == "__main__":
    u.run_main("07_positive_control_synthetic_drift", main)

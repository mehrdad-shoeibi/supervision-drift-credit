"""
Shared utilities for the supervision-drift-credit pipeline.

All modeling helpers enforce train-only preprocessing fit. Reproducibility
helpers (hashing, manifests) record enough to reconstruct any official run.

If something fails, callers are expected to let the traceback propagate and
stop (see run_main in each stage script).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import warnings
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# ----------------------------------------------------------------------------
# Locked constants (mirror docs/00_design_lock.md and docs/03_*).
# ----------------------------------------------------------------------------
RAW_FILENAME = "LC_loans_granting_model_dataset.csv"
TARGET_COL = "Default"
DATE_COL = "issue_d"
SEGMENT_COL = "purpose"
YEAR_COL = "_issue_year"          # derived, never a predictive feature
DROP_COLS = ["id", "title", "desc"]
VINTAGE_TRAIN_YEAR = 2013
VINTAGE_TEST_YEAR = 2016
RANDOM_STATE = 0
CLIP_LO, CLIP_HI = 1e-6, 1.0 - 1e-6

# Columns that are never predictive features.
NON_FEATURE_COLS = set(DROP_COLS) | {TARGET_COL, DATE_COL, YEAR_COL}


# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
def project_root() -> str:
    """Repo root = parent of the directory containing this file (src/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def path(*parts: str) -> str:
    return os.path.join(project_root(), *parts)


def raw_csv_path() -> str:
    return path("data", "raw", RAW_FILENAME)


def ensure_dirs() -> None:
    for d in [
        path("data", "processed"),
        path("results", "tables"),
        path("results", "logs"),
        path("results", "manifests"),
    ]:
        os.makedirs(d, exist_ok=True)


# ----------------------------------------------------------------------------
# Logging (writes to a file AND echoes to stdout)
# ----------------------------------------------------------------------------
class Logger:
    def __init__(self, log_path: str):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        # truncate at start of each run
        self._fh = open(log_path, "w", encoding="utf-8")

    def log(self, msg: str = "") -> None:
        line = str(msg)
        print(line)
        self._fh.write(line + "\n")
        self._fh.flush()

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# Hashing / IO
# ----------------------------------------------------------------------------
def sha256_file(fp: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(fp, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def file_size_bytes(fp: str) -> int:
    return os.path.getsize(fp)


def load_csv(fp: str, **kwargs) -> pd.DataFrame:
    if not os.path.exists(fp):
        raise FileNotFoundError(f"Expected CSV not found: {fp}")
    return pd.read_csv(fp, low_memory=False, **kwargs)


def load_parquet(fp: str) -> pd.DataFrame:
    if not os.path.exists(fp):
        raise FileNotFoundError(f"Expected parquet not found: {fp}")
    return pd.read_parquet(fp)


def write_json(obj, fp: str) -> None:
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_json_default)


def write_csv(df: pd.DataFrame, fp: str) -> None:
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    df.to_csv(fp, index=False)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    return str(o)


# ----------------------------------------------------------------------------
# Reproducibility manifest
# ----------------------------------------------------------------------------
def git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root(),
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() or "UNKNOWN"
    except Exception:
        return "UNKNOWN"


def package_versions() -> dict:
    vers = {"python": sys.version.split()[0]}
    for mod in ["numpy", "pandas", "sklearn", "scipy", "pyarrow"]:
        try:
            m = __import__(mod)
            vers[mod] = getattr(m, "__version__", "UNKNOWN")
        except Exception:
            vers[mod] = "NOT_INSTALLED"
    return vers


def input_hashes(files: list[str]) -> dict:
    out = {}
    for fp in files:
        if os.path.exists(fp):
            out[fp] = {"sha256": sha256_file(fp), "bytes": file_size_bytes(fp)}
        else:
            out[fp] = {"sha256": None, "bytes": None}
    return out


def write_manifest(fp: str, *, stage: str, input_files: list[str], extra: dict | None = None) -> None:
    manifest = {
        "stage": stage,
        "timestamp_utc": now_iso(),
        "command": " ".join(sys.argv),
        "git_commit": git_commit(),
        "package_versions": package_versions(),
        "input_file_hashes": input_hashes(input_files),
    }
    if extra:
        manifest["extra"] = extra
    write_json(manifest, fp)


# ----------------------------------------------------------------------------
# Target coercion
# ----------------------------------------------------------------------------
def coerce_target(s: pd.Series, logger: Logger | None = None) -> pd.Series:
    """Coerce target to {0,1}. Records mapping. NaN where uncoercible."""
    if pd.api.types.is_numeric_dtype(s):
        out = s.astype("float")
        out = out.where(out.isin([0.0, 1.0]), other=np.nan)
        return out
    # boolean / string
    mapping = {
        "1": 1, "0": 0, "true": 1, "false": 0, "yes": 1, "no": 0,
        "default": 1, "charged off": 1, "charged_off": 1,
        "fully paid": 0, "fully_paid": 0, "paid": 0, "non-default": 0,
        "t": 1, "f": 0,
    }
    norm = s.astype("string").str.strip().str.lower()
    out = norm.map(mapping)
    if logger is not None:
        logger.log(f"  target coercion mapping applied: {mapping}")
    return out.astype("float")


# ----------------------------------------------------------------------------
# Feature identification
# ----------------------------------------------------------------------------
def identify_features(
    df: pd.DataFrame,
    *,
    exclude: set[str] | None = None,
    include_segment: bool = True,
) -> tuple[list[str], list[str]]:
    """
    Return (numeric_features, categorical_features) for the predictive matrix.

    Excludes target, date, derived year, and dropped leakage columns. The
    segment column `purpose` is included as a feature unless include_segment is
    False (it is preserved in the frame regardless for diagnostics).
    """
    excl = set(NON_FEATURE_COLS)
    if exclude:
        excl |= set(exclude)
    if not include_segment:
        excl.add(SEGMENT_COL)

    numeric, categorical = [], []
    for col in df.columns:
        if col in excl:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric.append(col)
        else:
            categorical.append(col)
    return numeric, categorical


# ----------------------------------------------------------------------------
# Splitting
# ----------------------------------------------------------------------------
def stratified_split(df: pd.DataFrame, *, test_size: float = 0.2, random_state: int = RANDOM_STATE,
                     logger: Logger | None = None):
    """80/20 split stratified by Default if feasible, else random."""
    from sklearn.model_selection import train_test_split

    y = df[TARGET_COL]
    stratify = None
    if y.nunique(dropna=True) >= 2 and y.value_counts(dropna=True).min() >= 2:
        stratify = y
    else:
        if logger:
            logger.log("  WARNING: stratification not feasible; using random split.")
    train_df, test_df = train_test_split(
        df, test_size=test_size, random_state=random_state, stratify=stratify
    )
    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


# ----------------------------------------------------------------------------
# Preprocessing + models
# ----------------------------------------------------------------------------
def build_preprocessor(numeric: list[str], categorical: list[str], *, scale: bool):
    """ColumnTransformer; fit on training data only by the caller."""
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler

    num_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        num_steps.append(("scale", StandardScaler()))
    num_pipe = Pipeline(num_steps)

    cat_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore")),
    ])

    transformers = []
    if numeric:
        transformers.append(("num", num_pipe, numeric))
    if categorical:
        transformers.append(("cat", cat_pipe, categorical))
    return ColumnTransformer(transformers, remainder="drop", sparse_threshold=0.3)


def build_model(name: str, *, seed: int):
    """Return an estimator. `name` in {logreg, rf, hgb}."""
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.linear_model import LogisticRegression

    if name == "logreg":
        return LogisticRegression(max_iter=2000, random_state=seed)
    if name == "rf":
        return RandomForestClassifier(n_estimators=300, n_jobs=-1, random_state=seed)
    if name == "hgb":
        return HistGradientBoostingClassifier(random_state=seed)
    raise ValueError(f"Unknown model name: {name}")


def model_specs() -> list[tuple[str, list[int]]]:
    """Locked (model, seeds) plan."""
    return [("logreg", [0]), ("hgb", [0]), ("rf", [0, 1, 2])]


def build_pipeline(model_name: str, numeric: list[str], categorical: list[str], *, seed: int):
    """Full sklearn Pipeline: preprocessing + classifier. Fit on train only."""
    from sklearn.pipeline import Pipeline

    scale = model_name == "logreg"
    pre = build_preprocessor(numeric, categorical, scale=scale)
    clf = build_model(model_name, seed=seed)
    return Pipeline([("pre", pre), ("clf", clf)])


def fit_predict_proba(pipe, train_df: pd.DataFrame, test_df: pd.DataFrame,
                      numeric: list[str], categorical: list[str]):
    """Fit on train, return positive-class probabilities on test."""
    feats = numeric + categorical
    X_train = train_df[feats]
    y_train = train_df[TARGET_COL].astype(int)
    X_test = test_df[feats]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe.fit(X_train, y_train)
        proba = pipe.predict_proba(X_test)[:, 1]
    return proba


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def auroc(y_true, p) -> float:
    from sklearn.metrics import roc_auc_score
    y_true = np.asarray(y_true)
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(roc_auc_score(y_true, p))


def average_precision(y_true, p) -> float:
    from sklearn.metrics import average_precision_score
    y_true = np.asarray(y_true)
    if len(np.unique(y_true)) < 2:
        return float("nan")
    return float(average_precision_score(y_true, p))


def brier(y_true, p) -> float:
    from sklearn.metrics import brier_score_loss
    return float(brier_score_loss(np.asarray(y_true), np.asarray(p)))


def core_metrics(y_true, p) -> dict:
    return {
        "auroc": auroc(y_true, p),
        "average_precision": average_precision(y_true, p),
        "brier": brier(y_true, p),
    }


def bootstrap_auroc_ci(y_true, p, *, n_boot: int = 2000, random_state: int = RANDOM_STATE,
                       alpha: float = 0.05) -> dict:
    """Percentile bootstrap CI for AUROC. Returns dict with lo/hi/n_boot."""
    from sklearn.metrics import roc_auc_score
    y_true = np.asarray(y_true)
    p = np.asarray(p)
    n = len(y_true)
    if len(np.unique(y_true)) < 2 or n == 0:
        return {"ci_lo": float("nan"), "ci_hi": float("nan"), "n_boot": 0}
    rng = np.random.default_rng(random_state)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        yb = y_true[idx]
        if len(np.unique(yb)) < 2:
            continue
        stats.append(roc_auc_score(yb, p[idx]))
    if not stats:
        return {"ci_lo": float("nan"), "ci_hi": float("nan"), "n_boot": 0}
    lo = float(np.percentile(stats, 100 * alpha / 2))
    hi = float(np.percentile(stats, 100 * (1 - alpha / 2)))
    return {"ci_lo": lo, "ci_hi": hi, "n_boot": len(stats)}


# ----------------------------------------------------------------------------
# Calibration
# ----------------------------------------------------------------------------
def clip_p(p) -> np.ndarray:
    return np.clip(np.asarray(p, dtype=float), CLIP_LO, CLIP_HI)


def logit(p) -> np.ndarray:
    pc = clip_p(p)
    return np.log(pc / (1.0 - pc))


def sigmoid(z) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.asarray(z, dtype=float)))


def ece_equal_frequency(y_true, p, n_bins: int = 10) -> float:
    """Expected Calibration Error with equal-frequency (quantile) bins."""
    y_true = np.asarray(y_true, dtype=float)
    p = np.asarray(p, dtype=float)
    n = len(p)
    if n == 0:
        return float("nan")
    order = np.argsort(p)
    p_sorted = p[order]
    y_sorted = y_true[order]
    # equal-frequency bin edges by rank
    bins = np.array_split(np.arange(n), n_bins)
    ece = 0.0
    for b in bins:
        if len(b) == 0:
            continue
        conf = p_sorted[b].mean()
        acc = y_sorted[b].mean()
        ece += (len(b) / n) * abs(acc - conf)
    return float(ece)


def calibration_intercept_slope(y_true, p, logger: Logger | None = None) -> dict:
    """
    Fit y ~ logit(p) via logistic regression with minimal regularization.
    Returns {'intercept', 'slope', 'ok', 'warning'}.
    """
    from sklearn.linear_model import LogisticRegression

    y_true = np.asarray(y_true, dtype=int)
    z = logit(p).reshape(-1, 1)
    result = {"intercept": float("nan"), "slope": float("nan"), "ok": False, "warning": ""}
    if len(np.unique(y_true)) < 2:
        result["warning"] = "single-class target; cannot fit calibration model"
        if logger:
            logger.log(f"  WARNING: {result['warning']}")
        return result
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            lr = LogisticRegression(C=1e6, max_iter=5000, solver="lbfgs")
            lr.fit(z, y_true)
        result["intercept"] = float(lr.intercept_[0])
        result["slope"] = float(lr.coef_[0][0])
        result["ok"] = True
    except Exception as e:  # noqa: BLE001
        result["warning"] = f"calibration fit failed: {e}"
        if logger:
            logger.log(f"  WARNING: {result['warning']}")
    return result


def base_rate_recalibrate(p, target_rate: float, *, tol: float = 1e-9, max_iter: int = 200) -> tuple[np.ndarray, float]:
    """
    Intercept/base-rate recalibration:
      logit(p_recal) = logit(p_clipped) + delta
    choosing delta so mean(p_recal) == target_rate (observed default rate).

    Diagnostic only (uses test base rate). Returns (p_recal, delta).
    Solved by monotone bisection on delta (mean is increasing in delta).
    """
    z = logit(p)
    target = float(np.clip(target_rate, CLIP_LO, CLIP_HI))

    def mean_for(delta: float) -> float:
        return float(sigmoid(z + delta).mean())

    lo, hi = -50.0, 50.0
    if mean_for(lo) > target:
        return sigmoid(z + lo), lo
    if mean_for(hi) < target:
        return sigmoid(z + hi), hi
    delta = 0.0
    for _ in range(max_iter):
        delta = 0.5 * (lo + hi)
        m = mean_for(delta)
        if abs(m - target) < tol:
            break
        if m < target:
            lo = delta
        else:
            hi = delta
    return sigmoid(z + delta), float(delta)


def decile_calibration_table(y_true, p, n_bins: int = 10) -> list[dict]:
    """Equal-frequency decile table: bin, n, mean_pred, observed_rate."""
    y_true = np.asarray(y_true, dtype=float)
    p = np.asarray(p, dtype=float)
    n = len(p)
    rows = []
    if n == 0:
        return rows
    order = np.argsort(p)
    p_sorted = p[order]
    y_sorted = y_true[order]
    for i, b in enumerate(np.array_split(np.arange(n), n_bins)):
        if len(b) == 0:
            continue
        rows.append({
            "bin": i + 1,
            "n": int(len(b)),
            "mean_pred": float(p_sorted[b].mean()),
            "observed_rate": float(y_sorted[b].mean()),
            "p_min": float(p_sorted[b].min()),
            "p_max": float(p_sorted[b].max()),
        })
    return rows


# ----------------------------------------------------------------------------
# Univariate feature-label diagnostics
# ----------------------------------------------------------------------------
def spearman_with_target(x, y) -> float:
    from scipy.stats import spearmanr
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~np.isnan(x)
    if mask.sum() < 3 or len(np.unique(y[mask])) < 2:
        return float("nan")
    rho, _ = spearmanr(x[mask], y[mask])
    return float(rho)


def univariate_auc_strength(x, y) -> float:
    """max(AUROC, 1-AUROC) of single feature vs target, NaN-safe."""
    from sklearn.metrics import roc_auc_score
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = ~np.isnan(x)
    if mask.sum() < 3 or len(np.unique(y[mask])) < 2:
        return float("nan")
    a = roc_auc_score(y[mask], x[mask])
    return float(max(a, 1.0 - a))


# ----------------------------------------------------------------------------
# Processed-context loading / segment resolution (shared by stages 3-7)
# ----------------------------------------------------------------------------
def load_processed():
    """Load the four locked processed contexts. Returns a dict of DataFrames."""
    return {
        "vintage_2013": load_parquet(path("data", "processed", "vintage_2013.parquet")),
        "vintage_2016": load_parquet(path("data", "processed", "vintage_2016.parquet")),
        "indomain_2013_train": load_parquet(path("data", "processed", "indomain_2013_train.parquet")),
        "indomain_2013_test": load_parquet(path("data", "processed", "indomain_2013_test.parquet")),
    }


def resolve_segments(v2013: pd.DataFrame, logger: Logger | None = None) -> tuple[str, str]:
    """
    Locked rule: source = largest 2013 purpose, target = second-largest.
    Ties broken by ascending alphabetical category name.
    """
    if SEGMENT_COL not in v2013.columns:
        raise KeyError(f"Segment column '{SEGMENT_COL}' absent; cannot resolve segments.")
    vc = v2013[SEGMENT_COL].value_counts(dropna=False)
    ordered = sorted(vc.items(), key=lambda kv: (-kv[1], str(kv[0])))
    if len(ordered) < 2:
        raise ValueError("Fewer than two purpose segments in 2013; cross-segment infeasible.")
    source, target = str(ordered[0][0]), str(ordered[1][0])
    if logger:
        logger.log(f"  source segment: {source} (n={ordered[0][1]})")
        logger.log(f"  target segment: {target} (n={ordered[1][1]})")
    return source, target


def segment_frame(df: pd.DataFrame, seg_value: str) -> pd.DataFrame:
    return df[df[SEGMENT_COL].astype(str) == str(seg_value)].reset_index(drop=True)


def common_features(train_df: pd.DataFrame, test_df: pd.DataFrame, *, include_segment: bool):
    """Identify features present in BOTH frames (defensive against schema drift)."""
    num_tr, cat_tr = identify_features(train_df, include_segment=include_segment)
    num_te, cat_te = identify_features(test_df, include_segment=include_segment)
    numeric = [c for c in num_tr if c in set(num_te)]
    categorical = [c for c in cat_tr if c in set(cat_te)]
    return numeric, categorical


# ----------------------------------------------------------------------------
# Stage runner: guarantees full traceback + stop on failure
# ----------------------------------------------------------------------------
def run_main(stage_name: str, fn) -> None:
    """
    Execute fn(). On any exception, print the full traceback and exit non-zero.
    Per integrity rules: if anything fails, report and stop.
    """
    import traceback
    try:
        fn()
    except Exception:  # noqa: BLE001
        sys.stderr.write(f"\n[{stage_name}] FAILED — full traceback follows:\n")
        traceback.print_exc()
        sys.exit(1)

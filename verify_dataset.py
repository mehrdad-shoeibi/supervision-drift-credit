#!/usr/bin/env python3
"""
verify_dataset.py — READ-ONLY dataset provenance audit.

Purpose
-------
Verify whether a local raw LendingClub file is consistent with the dataset cited
in the manuscript:

    Ariza-Garzon et al. 2024, "Lending Club loan dataset for granting models",
    Zenodo Version 0.1, DOI: 10.5281/zenodo.11295916
    (concept DOI 10.5281/zenodo.11295915 belongs to the same record family).

This is a *fingerprint and consistency* tool. It never resolves the DOI online,
never needs internet access, and never modifies the dataset.

HARD SAFETY CONSTRAINTS (enforced by construction)
--------------------------------------------------
* Strictly READ-ONLY: data files are opened in read mode only ("rb" for hashing,
  pandas read_* for loading). Nothing is modified, deleted, moved, or renamed.
* NO raw rows are ever printed or written. No df.head(), df.sample(), no
  per-record output. Only aggregates: counts, rates, column names, distributions,
  warnings, and verdicts.
* No internet access.
* Works for CSV and Parquet input.
* Exit code 0 on a successful run regardless of the verdict; nonzero only for
  runtime errors (missing file, unreadable format, etc.).

Dependencies: pandas + Python standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import pandas as pd

# ----------------------------------------------------------------------------
# Reference knowledge (no network needed)
# ----------------------------------------------------------------------------

# Post-origination / outcome columns that should NOT exist in an application-time
# "granting model" dataset. Their presence indicates a raw / non-granting dump.
LEAKAGE_COLS = [
    "total_pymnt",
    "total_rec_prncp",
    "recoveries",
    "last_pymnt_d",
    "last_pymnt_amnt",
    "out_prncp",
    "total_pymnt_inv",
    "collection_recovery_fee",
    "next_pymnt_d",
]

# Candidate identifier / key columns (presence check only; values never printed).
KEY_CANDIDATES = ["id", "member_id", "loan_id", "loanid", "index", "Unnamed: 0"]

# Auto-detection candidate names (case-insensitive match).
YEAR_CANDIDATES = ["_issue_year", "issue_year", "year", "vintage"]
PURPOSE_CANDIDATES = ["purpose", "loan_purpose"]
LABEL_CANDIDATES = [
    "Default", "default", "default_flag", "is_default",
    "target", "y", "label", "loan_status",
]
DATE_CANDIDATES = ["issue_d", "issue_date", "issued", "date"]

# Manuscript Table 1 expected quantities (locked).
TABLE1_EXPECTED = {
    "in_domain_total_2013": {"n": 134804, "rate": 0.1560, "note": "2013 total = train(107843)+test(26961)"},
    "temporal_train_2013": {"n": 134804, "rate": 0.1560, "note": "2013 vintage"},
    "temporal_test_2016": {"n": 293057, "rate": 0.2328, "note": "2016 vintage"},
    "cross_segment_train_2013_debt_consolidation": {"n": 80634, "rate": 0.1636, "note": "2013 debt_consolidation"},
    "cross_segment_test_2013_credit_card": {"n": 32804, "rate": 0.1320, "note": "2013 credit_card"},
}

# Verdict labels.
V_SAME = "1) LIKELY SAME DATASET AND FILTERING"
V_FAMILY = "2) POSSIBLY SAME SOURCE FAMILY BUT DIFFERENT FILTERING/PREPROCESSING OR RAW VERSION"
V_DIFFERENT = "3) LIKELY DIFFERENT DATASET OR DIFFERENT LABEL CONSTRUCTION"
V_INSUFFICIENT = "4) INSUFFICIENT INFORMATION"


# ----------------------------------------------------------------------------
# Small reporting helper: print + accumulate text, never touches raw rows.
# ----------------------------------------------------------------------------
class Report:
    """Collects printed lines so the same text can be saved to a .txt file."""

    def __init__(self):
        self.lines: list[str] = []

    def __call__(self, line: str = "") -> None:
        print(line)
        self.lines.append(line)

    def text(self) -> str:
        return "\n".join(self.lines) + "\n"


# ----------------------------------------------------------------------------
# Read-only utilities
# ----------------------------------------------------------------------------
def sha256_file(path: str, chunk_size: int = 1 << 20) -> str:
    """Stream the file in binary read mode and return its SHA-256 hex digest."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:  # read-only
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def load_dataset(path: str) -> pd.DataFrame:
    """
    Load a CSV or Parquet file in read mode only. Raises on unreadable format so
    the caller can exit nonzero. Never writes anything.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".parquet", ".pq"):
        return pd.read_parquet(path)  # read-only
    if ext in (".csv", ".gz", ".txt", ".tsv"):
        sep = "\t" if ext == ".tsv" else ","
        # low_memory=False avoids mixed-dtype chunk warnings; still read-only.
        return pd.read_csv(path, sep=sep, low_memory=False)
    # Fall back: try CSV, then Parquet, before giving up.
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.read_parquet(path)


def find_column(df: pd.DataFrame, explicit: str | None, candidates: list[str]) -> str | None:
    """Return an explicit column if valid, else the first candidate present (case-insensitive)."""
    if explicit:
        if explicit in df.columns:
            return explicit
        # case-insensitive fallback for an explicitly requested name
        lower = {c.lower(): c for c in df.columns}
        return lower.get(explicit.lower())
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in df.columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    return None


def normalize_purpose(value) -> str:
    """lowercase, strip, and map spaces/hyphens to underscores so that
    'Debt consolidation', 'debt-consolidation', 'debt_consolidation' all match."""
    s = str(value).strip().lower()
    for ch in (" ", "-", "/"):
        s = s.replace(ch, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s


def parse_years_from_dates(series: pd.Series):
    """
    Parse a date-like column into integer years. Handles formats such as
    'Dec-2013', '2013-12-01', 'Dec-13', '12/01/2013', '2013-12'.
    Returns (years_series_or_None, parse_rate).
    """
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    best_rate = float(parsed.notna().mean())
    if best_rate < 0.5:
        for fmt in ("%b-%Y", "%b-%y", "%Y-%m-%d", "%m/%d/%Y", "%Y-%m", "%Y/%m/%d"):
            trial = pd.to_datetime(series, errors="coerce", format=fmt)
            rate = float(trial.notna().mean())
            if rate > best_rate:
                parsed, best_rate = trial, rate
    if best_rate == 0.0:
        return None, 0.0
    return parsed.dt.year, best_rate


def detect_years(df: pd.DataFrame, year_col: str | None, date_col: str | None, rep: Report):
    """
    Determine an integer-year series and how it was obtained.
    Returns (years_series_or_None, source_description, parse_rate_or_None).
    """
    if year_col and year_col in df.columns:
        years = pd.to_numeric(df[year_col], errors="coerce")
        # tolerate float years like 2013.0
        years = years.round().astype("Int64")
        return years, f"year column '{year_col}'", None
    if date_col and date_col in df.columns:
        years, rate = parse_years_from_dates(df[date_col])
        if years is not None:
            return years.astype("Int64"), f"parsed from date column '{date_col}'", rate
        rep("  WARNING: date column present but could not be parsed into years.")
        return None, f"unparseable date column '{date_col}'", rate
    return None, "no year or date column found", None


def build_label_config(df: pd.DataFrame, label_col: str | None, positive_values):
    """
    Decide how to compute the default rate.

    Returns a dict:
      {'mode': 'positive_values' | 'numeric_binary' | 'unmapped' | 'missing',
       'positive_values_norm': set[str],
       'n_unique': int | None,
       'unique_preview': list[str]  # category labels only, never rows
       'is_loan_status': bool}
    """
    cfg = {
        "mode": "missing",
        "positive_values_norm": set(),
        "n_unique": None,
        "unique_preview": [],
        "is_loan_status": False,
    }
    if not label_col or label_col not in df.columns:
        return cfg

    s = df[label_col]
    nonnull = s.dropna()
    uniq = pd.Index(nonnull.unique())
    cfg["n_unique"] = int(len(uniq))
    cfg["is_loan_status"] = label_col.lower() == "loan_status"
    # Category labels (not borrower rows). Cap the preview length defensively.
    cfg["unique_preview"] = [str(v) for v in list(uniq)[:25]]

    if positive_values:
        cfg["mode"] = "positive_values"
        cfg["positive_values_norm"] = {str(v).strip().lower() for v in positive_values}
        return cfg

    # numeric binary {0,1}?
    numeric = pd.to_numeric(nonnull, errors="coerce")
    if numeric.notna().all():
        vals = set(numeric.unique().tolist())
        if vals.issubset({0, 1, 0.0, 1.0}):
            cfg["mode"] = "numeric_binary"
            return cfg

    cfg["mode"] = "unmapped"
    return cfg


def default_rate(sub: pd.DataFrame, label_col: str, cfg: dict):
    """
    Compute an aggregate default rate (a single float) for a subframe.
    Returns None when the label is unmapped. Never returns row-level data.
    """
    if label_col is None or label_col not in sub.columns or len(sub) == 0:
        return None
    s = sub[label_col]
    if cfg["mode"] == "positive_values":
        norm = s.astype(str).str.strip().str.lower()
        return float(norm.isin(cfg["positive_values_norm"]).mean())
    if cfg["mode"] == "numeric_binary":
        return float(pd.to_numeric(s, errors="coerce").mean())
    return None  # unmapped / missing


# ----------------------------------------------------------------------------
# Main audit
# ----------------------------------------------------------------------------
def run_audit(args) -> dict:
    rep = Report()
    results: dict = {}

    path = args.path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset file not found: {path}")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Not a regular file: {path}")

    rep("=" * 78)
    rep("READ-ONLY DATASET PROVENANCE AUDIT")
    rep("Reference: Ariza-Garzon et al. 2024, Zenodo 10.5281/zenodo.11295916")
    rep("(concept DOI 10.5281/zenodo.11295915, same record family; not resolved online)")
    rep("=" * 78)

    # ---- 1-4. File fingerprint -------------------------------------------------
    abspath = os.path.abspath(path)
    fname = os.path.basename(path)
    size_bytes = os.path.getsize(path)
    size_mb = size_bytes / (1024 * 1024)
    sha = sha256_file(path)

    rep("\n[FILE FINGERPRINT]")
    rep(f"  absolute_path : {abspath}")
    rep(f"  file_name     : {fname}")
    rep(f"  size_bytes    : {size_bytes:,}")
    rep(f"  size_mb       : {size_mb:.2f}")
    rep(f"  sha256        : {sha}")

    results.update({
        "path": abspath,
        "file_name": fname,
        "size_bytes": int(size_bytes),
        "size_mb": round(size_mb, 4),
        "sha256": sha,
    })

    # ---- Load (read-only) ------------------------------------------------------
    df = load_dataset(path)
    n_rows, n_cols = int(df.shape[0]), int(df.shape[1])

    # ---- 5-6. Shape and ordered columns ---------------------------------------
    rep("\n[SHAPE]")
    rep(f"  n_rows : {n_rows:,}")
    rep(f"  n_cols : {n_cols}")
    rep("\n[COLUMNS] (ordered)")
    rep("  " + ", ".join(map(str, df.columns)))
    results.update({
        "n_rows": n_rows,
        "n_cols": n_cols,
        "columns": [str(c) for c in df.columns],
    })

    # ---- 7. Candidate key-column presence -------------------------------------
    lower_cols = {c.lower(): c for c in df.columns}
    keys_present = [lower_cols[k.lower()] for k in KEY_CANDIDATES if k.lower() in lower_cols]
    rep("\n[CANDIDATE KEY COLUMNS]")
    rep(f"  present: {keys_present if keys_present else 'none'}")
    results["candidate_key_columns_present"] = keys_present

    # ---- Column auto-detection -------------------------------------------------
    year_col = find_column(df, args.year_col, YEAR_CANDIDATES)
    purpose_col = find_column(df, args.purpose_col, PURPOSE_CANDIDATES)
    label_col = find_column(df, args.label_col, LABEL_CANDIDATES)
    date_col = find_column(df, args.issue_date_col, DATE_CANDIDATES)

    rep("\n[DETECTED COLUMNS]")
    rep(f"  year_col    : {year_col}")
    rep(f"  purpose_col : {purpose_col}")
    rep(f"  label_col   : {label_col}")
    rep(f"  date_col    : {date_col}")
    results["detected_columns"] = {
        "year_col": year_col, "purpose_col": purpose_col,
        "label_col": label_col, "date_col": date_col,
    }

    positive_values = None
    if args.positive_label_values:
        positive_values = [v.strip() for v in args.positive_label_values.split(",") if v.strip()]

    label_cfg = build_label_config(df, label_col, positive_values)

    # ---- 8. Label / default-rate summary --------------------------------------
    rep("\n[LABEL / DEFAULT-RATE SUMMARY]")
    if label_col is None:
        rep("  WARNING: no label column detected; default-rate computation skipped.")
    else:
        rep(f"  label_col          : {label_col}")
        rep(f"  n_unique_values    : {label_cfg['n_unique']}")
        rep(f"  unique_values      : {label_cfg['unique_preview']}  (category labels only)")
        rep(f"  rate_mode          : {label_cfg['mode']}")
        overall = default_rate(df, label_col, label_cfg)
        if overall is None:
            rep("  overall_default_rate: label mapping not specified (rate skipped)")
        else:
            rep(f"  overall_default_rate: {overall:.4f}")
    results["label"] = {
        "label_col": label_col,
        "n_unique_values": label_cfg["n_unique"],
        "unique_values": label_cfg["unique_preview"],
        "rate_mode": label_cfg["mode"],
        "positive_label_values": positive_values,
    }

    # ---- 9. Year / vintage distribution ---------------------------------------
    years, year_source, parse_rate = detect_years(df, year_col, date_col, rep)
    rep("\n[YEAR / VINTAGE DISTRIBUTION]")
    rep(f"  source: {year_source}")
    if parse_rate is not None:
        rep(f"  date_parse_rate: {parse_rate:.4f}")
    year_counts: dict = {}
    if years is not None:
        vc = years.dropna().astype(int).value_counts().sort_index()
        year_counts = {int(k): int(v) for k, v in vc.items()}
        for k, v in year_counts.items():
            rep(f"  {k}: {v:,}")
    else:
        rep("  WARNING: year distribution unavailable.")
    results["year_distribution"] = year_counts
    results["year_source"] = year_source

    # ---- 10. Purpose distribution ---------------------------------------------
    rep("\n[PURPOSE DISTRIBUTION] (normalized)")
    purpose_norm = None
    purpose_counts: dict = {}
    if purpose_col is not None:
        purpose_norm = df[purpose_col].map(normalize_purpose)
        vc = purpose_norm.value_counts(dropna=False)
        purpose_counts = {str(k): int(v) for k, v in vc.items()}
        for k, v in purpose_counts.items():
            rep(f"  {k}: {v:,}")
    else:
        rep("  WARNING: purpose column not found.")
    results["purpose_distribution"] = purpose_counts

    # ---- ARIZA-GARZON GRANTING-VERSION CONSISTENCY CHECK ----------------------
    rep("\n" + "=" * 78)
    rep("ARIZA-GARZON GRANTING-VERSION CONSISTENCY CHECK")
    rep("=" * 78)
    granting = {"warnings": []}

    if label_col is not None:
        rep(f"  label '{label_col}' unique-value count: {label_cfg['n_unique']}")
        if label_cfg["is_loan_status"] and (label_cfg["n_unique"] or 0) > 2 and not positive_values:
            msg = ("WARNING: label is 'loan_status' with >2 classes "
                   f"({label_cfg['unique_preview']}). This looks like the RAW LendingClub "
                   "dataset, not the filtered binary granting version. Not collapsing "
                   "automatically; supply --positive-label-values to map a default class.")
            rep("  " + msg)
            granting["warnings"].append(msg)
        granting["label_n_unique"] = label_cfg["n_unique"]
        granting["label_is_loan_status_multiclass"] = bool(
            label_cfg["is_loan_status"] and (label_cfg["n_unique"] or 0) > 2
        )
    else:
        granting["label_n_unique"] = None
        granting["label_is_loan_status_multiclass"] = False

    leakage_present = [lower_cols[c.lower()] for c in LEAKAGE_COLS if c.lower() in lower_cols]
    rep(f"\n  post-origination / leakage columns present: "
        f"{leakage_present if leakage_present else 'none'}")
    if leakage_present:
        msg = ("WARNING: post-origination/leakage columns are present "
               f"({leakage_present}). Their presence suggests a raw or non-granting "
               "version, since an application-time granting dataset should not contain them.")
        rep("  " + msg)
        granting["warnings"].append(msg)
    granting["leakage_columns_present"] = leakage_present
    binary_label = label_cfg["mode"] in ("numeric_binary", "positive_values")
    granting["binary_label"] = bool(binary_label)
    granting["granting_signs_present"] = bool(binary_label and not leakage_present)
    rep(f"  granting-version signs present (binary label & no leakage cols): "
        f"{granting['granting_signs_present']}")
    results["granting_version_check"] = granting

    # ---- MANUSCRIPT TABLE 1 REPRODUCTION CHECK --------------------------------
    rep("\n" + "=" * 78)
    rep("MANUSCRIPT TABLE 1 REPRODUCTION CHECK")
    rep("=" * 78)
    rep("Assumptions:")
    rep("  * in_domain cannot be reproduced exactly (held-out random fold unknown);")
    rep("    only the identity 107843 + 26961 = 134804 = total 2013 vintage is checked,")
    rep("    and the 2013 overall default rate is compared to 0.1560 as a proxy.")
    rep("  * temporal train n = total 2013 rows; temporal test n = total 2016 rows.")
    rep("  * cross_segment counts are within 2013, filtered by normalized purpose.")
    rep(f"  * n match: {'within 1% (allow-n-diff)' if args.allow_n_diff else 'EXACT required'}; "
        f"default-rate tolerance = {args.default_rate_tol}")

    def n_in_year(yr: int):
        if years is None:
            return None
        return int((years == yr).sum())

    def n_in_year_purpose(yr: int, purpose_value: str):
        if years is None or purpose_norm is None:
            return None
        mask = (years == yr) & (purpose_norm == purpose_value)
        return int(mask.sum())

    def subframe_year(yr: int):
        if years is None:
            return None
        return df[years == yr]

    def subframe_year_purpose(yr: int, purpose_value: str):
        if years is None or purpose_norm is None:
            return None
        return df[(years == yr) & (purpose_norm == purpose_value)]

    def status_for(expected_n, observed_n, expected_rate, observed_rate):
        # n status
        if observed_n is None:
            n_status = "SKIPPED"
        elif observed_n == expected_n:
            n_status = "PASS"
        elif args.allow_n_diff and expected_n > 0 and abs(observed_n - expected_n) / expected_n <= 0.01:
            n_status = "PASS"
        else:
            n_status = "FAIL"
        # rate status
        if observed_rate is None:
            r_status = "SKIPPED"
        elif abs(observed_rate - expected_rate) <= args.default_rate_tol:
            r_status = "PASS"
        else:
            r_status = "FAIL"
        # overall
        sub = [s for s in (n_status, r_status)]
        if "FAIL" in sub:
            overall = "FAIL"
        elif all(s == "SKIPPED" for s in sub):
            overall = "SKIPPED"
        else:
            overall = "PASS"
        return n_status, r_status, overall

    repro: list[dict] = []

    def emit_entry(name, expected_n, observed_n, expected_rate, observed_rate, extra_note=""):
        n_status, r_status, overall = status_for(expected_n, observed_n, expected_rate, observed_rate)
        rep(f"\n  [{name}] {extra_note}")
        rep(f"    expected_n            : {expected_n}")
        rep(f"    observed_n            : {observed_n if observed_n is not None else 'SKIPPED'}")
        if observed_n is not None:
            rep(f"    abs_diff_n            : {abs(observed_n - expected_n)}")
        rep(f"    expected_default_rate : {expected_rate:.4f}")
        if observed_rate is None:
            rep("    observed_default_rate : SKIPPED (label mapping not specified)")
        else:
            rep(f"    observed_default_rate : {observed_rate:.4f}")
            rep(f"    abs_diff_rate         : {abs(observed_rate - expected_rate):.4f}")
        rep(f"    n_status / rate_status: {n_status} / {r_status}")
        rep(f"    STATUS                : {overall}")
        repro.append({
            "name": name,
            "expected_n": expected_n,
            "observed_n": observed_n,
            "abs_diff_n": (abs(observed_n - expected_n) if observed_n is not None else None),
            "expected_default_rate": expected_rate,
            "observed_default_rate": (round(observed_rate, 6) if observed_rate is not None else None),
            "abs_diff_rate": (round(abs(observed_rate - expected_rate), 6) if observed_rate is not None else None),
            "n_status": n_status,
            "rate_status": r_status,
            "status": overall,
        })

    # in_domain: identity check on the 2013 total + proxy 2013 overall rate
    n2013 = n_in_year(2013)
    n2016 = n_in_year(2016)
    rate2013 = default_rate(subframe_year(2013), label_col, label_cfg) if n2013 is not None else None
    rate2016 = default_rate(subframe_year(2016), label_col, label_cfg) if n2016 is not None else None

    rep("\n  [in_domain] 107843 + 26961 = 134804 identity vs total 2013 count")
    if n2013 is None:
        rep("    observed_total_2013   : SKIPPED (year unavailable)")
    else:
        rep(f"    expected_total_2013   : 134804")
        rep(f"    observed_total_2013   : {n2013}")
        rep(f"    identity_holds        : {n2013 == (107843 + 26961)}")
    emit_entry("in_domain_total_2013_and_rate", 134804, n2013, 0.1560, rate2013,
               extra_note="(2013 total + proxy overall rate)")

    emit_entry("temporal_train_2013", 134804, n2013, 0.1560, rate2013)
    emit_entry("temporal_test_2016", 293057, n2016, 0.2328, rate2016)

    dc_n = n_in_year_purpose(2013, "debt_consolidation")
    cc_n = n_in_year_purpose(2013, "credit_card")
    dc_rate = default_rate(subframe_year_purpose(2013, "debt_consolidation"), label_col, label_cfg) if dc_n is not None else None
    cc_rate = default_rate(subframe_year_purpose(2013, "credit_card"), label_col, label_cfg) if cc_n is not None else None
    emit_entry("cross_segment_train_2013_debt_consolidation", 80634, dc_n, 0.1636, dc_rate)
    emit_entry("cross_segment_test_2013_credit_card", 32804, cc_n, 0.1320, cc_rate)

    results["table1_reproduction"] = repro

    # ---- FINAL VERDICT ---------------------------------------------------------
    evidence: list[str] = []

    # Helpers over computed checks.
    computed_counts = [(e["expected_n"], e["observed_n"]) for e in repro if e["observed_n"] is not None]
    any_count_fail = any(e["n_status"] == "FAIL" for e in repro)
    all_counts_pass = (len(computed_counts) > 0) and all(
        e["n_status"] == "PASS" for e in repro if e["observed_n"] is not None
    )
    any_rate_fail = any(e["rate_status"] == "FAIL" for e in repro)
    all_rates_pass_or_skipped = not any_rate_fail
    rates_all_skipped = all(e["rate_status"] == "SKIPPED" for e in repro)
    any_rate_skipped = any(e["rate_status"] == "SKIPPED" for e in repro)
    # Strict: every Table 1 default-rate check actually PASSed (none skipped, none failed).
    all_rates_pass = (len(repro) > 0) and all(e["rate_status"] == "PASS" for e in repro)

    def grossly_off(expected_n, observed_n) -> bool:
        return expected_n > 0 and abs(observed_n - expected_n) / expected_n > 0.10

    any_gross = any(grossly_off(en, on) for en, on in computed_counts)
    required_years_present = (years is not None) and (2013 in year_counts) and (2016 in year_counts)
    required_purposes_present = (
        purpose_norm is not None
        and dc_n is not None and dc_n > 0
        and cc_n is not None and cc_n > 0
    )
    structural_ok = (years is not None) and (purpose_col is not None) and (label_col is not None)
    loan_status_multiclass = granting["label_is_loan_status_multiclass"] and not positive_values

    # Decision (first matching rule wins). Precedence is documented in comments.
    if loan_status_multiclass:
        # Raw multiclass loan_status with no binary mapping -> different label construction.
        verdict = V_DIFFERENT
        evidence.append(f"label '{label_col}' has {label_cfg['n_unique']} classes with no binary mapping (raw-looking).")
        if leakage_present:
            evidence.append(f"post-origination/leakage columns present: {leakage_present}.")
    elif (years is None) or (purpose_col is None) or (label_col is None) or (label_cfg["mode"] in ("unmapped", "missing")):
        # Missing structural columns OR an unmapped label -> cannot confirm construction.
        verdict = V_INSUFFICIENT
        if years is None:
            evidence.append("year/vintage could not be determined.")
        if purpose_col is None:
            evidence.append("purpose column not found.")
        if label_col is None:
            evidence.append("label column not found.")
        elif label_cfg["mode"] in ("unmapped", "missing"):
            evidence.append("label present but not mapped to a binary default class (provide --positive-label-values).")
        # Still report whatever count evidence we have.
        if all_counts_pass:
            evidence.append("Row counts match the manuscript, but label/default-rate "
                            "construction was not verified because default-rate checks were skipped.")
        elif any_count_fail:
            evidence.append("note: some available row-count checks did not match.")
    elif (not required_years_present) or (not required_purposes_present) or any_gross:
        # Required vintages/purposes absent, or counts grossly different.
        verdict = V_DIFFERENT
        if not required_years_present:
            evidence.append("required vintages 2013 and/or 2016 are absent.")
        if not required_purposes_present:
            evidence.append("required 2013 purposes debt_consolidation and/or credit_card are absent.")
        if any_gross:
            evidence.append("at least one row count differs from the manuscript by more than 10%.")
    elif (all_counts_pass and all_rates_pass and not any_rate_skipped
          and granting["granting_signs_present"] and not leakage_present
          and not loan_status_multiclass):
        # LIKELY SAME requires counts AND default rates to be verified. Manuscript
        # Table 1 reports both row counts and default rates, so row-count agreement
        # alone is insufficient; any SKIPPED default-rate check excludes this verdict.
        verdict = V_SAME
        evidence.append("all reproducible row counts match the manuscript exactly.")
        evidence.append("all Table 1 default-rate checks match within tolerance (none skipped).")
        evidence.append("binary label and no post-origination/leakage columns (granting-version signs).")
    else:
        # Close but not exact, leakage columns present, or minor rate mismatch.
        verdict = V_FAMILY
        if leakage_present:
            evidence.append(f"post-origination/leakage columns present: {leakage_present} (raw/non-granting sign).")
        if not all_counts_pass and not any_gross:
            evidence.append("row counts are close to the manuscript but not exact.")
        if any_rate_fail:
            evidence.append("at least one default rate is outside the tolerance.")
        if all_counts_pass and not granting["granting_signs_present"]:
            evidence.append("counts match but the file does not fully look like the filtered granting version.")
        if all_counts_pass and any_rate_skipped:
            evidence.append("Row counts match the manuscript, but label/default-rate "
                            "construction was not verified because default-rate checks were skipped.")
        if not evidence:
            evidence.append("evidence is mixed; counts/rates partially match.")

    rep("\n" + "=" * 78)
    rep("FINAL VERDICT")
    rep("=" * 78)
    rep(f"  {verdict}")
    rep("\n  Evidence:")
    for b in evidence:
        rep(f"    - {b}")

    results["verdict"] = verdict
    results["evidence"] = evidence

    return {"report": rep, "results": results}


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="READ-ONLY provenance audit for the LendingClub granting dataset.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("path", help="Path to the dataset file (CSV or Parquet). Opened read-only.")
    p.add_argument("--year-col", default=None, help="Year/vintage column name (auto-detected if omitted).")
    p.add_argument("--purpose-col", default=None, help="Purpose column name (auto-detected if omitted).")
    p.add_argument("--label-col", default=None, help="Label/target column name (auto-detected if omitted).")
    p.add_argument("--issue-date-col", default=None, help="Issue-date column name (auto-detected if omitted).")
    p.add_argument("--positive-label-values", default=None,
                   help='Comma-separated default/positive class values, e.g. "Default,Charged Off".')
    p.add_argument("--default-rate-tol", type=float, default=0.001,
                   help="Absolute tolerance for default-rate comparisons.")
    p.add_argument("--allow-n-diff", action="store_true",
                   help="Allow small (<=1%%) row-count differences; otherwise counts must match exactly.")
    p.add_argument("--outdir", default=".", help="Directory for the saved .txt and .json reports.")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    out = run_audit(args)
    rep: Report = out["report"]
    results: dict = out["results"]

    # ---- Save summaries only (never raw rows) ---------------------------------
    os.makedirs(args.outdir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_path = os.path.join(args.outdir, f"dataset_fingerprint_{stamp}.txt")
    json_path = os.path.join(args.outdir, f"dataset_fingerprint_{stamp}.json")

    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(rep.text())
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, default=str)

    print(f"\nSaved report : {os.path.abspath(txt_path)}")
    print(f"Saved JSON   : {os.path.abspath(json_path)}")
    return 0


if __name__ == "__main__":
    # Exit 0 on a successful run regardless of verdict; nonzero only on runtime errors.
    try:
        sys.exit(main())
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(2)
    except ImportError as exc:
        print(f"ERROR: missing dependency for this file format: {exc}", file=sys.stderr)
        sys.exit(3)

"""
Stage 0 — Data staging.

Confirms that the raw LendingClub file is present. Does NOT fabricate or
download data. If the file is missing, prints clear placement instructions.
"""

from __future__ import annotations

import os

import utils as u


def main() -> None:
    fp = u.raw_csv_path()
    print("=" * 70)
    print("Stage 0 — Data staging")
    print("=" * 70)
    print(f"Expected raw file:\n  {fp}\n")

    if os.path.exists(fp):
        size = u.file_size_bytes(fp)
        print("STATUS: raw file FOUND.")
        print(f"  size: {size:,} bytes")
        print("  Computing SHA256 (may take a moment for large files)...")
        print(f"  sha256: {u.sha256_file(fp)}")
        print("\nNext: python src/01_verify_data.py")
    else:
        print("STATUS: raw file NOT FOUND.")
        print("\nACTION REQUIRED — place the raw dataset manually:")
        print(f"  1. Obtain the LendingClub loan-granting model dataset CSV.")
        print(f"  2. Copy it to exactly this path:")
        print(f"       {fp}")
        print(f"  3. Re-run: python src/00_stage_data.py")
        print("\nThis script will NOT download or fabricate data.")


if __name__ == "__main__":
    u.run_main("00_stage_data", main)

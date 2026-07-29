#!/usr/bin/env python3
"""
One-time (or rare) script to pull many historical seasons.
Run this locally when you want to backfill.
Example:
  python build_historical.py --start 1991 --end 2025
"""

import argparse
import time
import subprocess
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1991, help="First season end year")
    parser.add_argument("--end", type=int, default=2025, help="Last season end year (exclusive of current)")
    args = parser.parse_args()

    script = Path(__file__).parent / "fetch_season_bref.py"
    out_dir = Path(__file__).resolve().parents[1] / "data" / "historical"
    out_dir.mkdir(parents=True, exist_ok=True)

    for year in range(args.start, args.end + 1):
        print(f"\n===== {year} =====")
        cmd = [
            "python", str(script),
            "--year", str(year),
            "--outdir", str(out_dir)
        ]
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed for {year}: {e}")
        time.sleep(5)  # be respectful to BRef

    print("\nHistorical backfill complete.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Fetch NBA player salaries from Basketball-Reference contracts page.
Outputs a clean Parquet for joining with the stats we already loaded.
"""

import argparse
from pathlib import Path
import pandas as pd
import requests
from io import StringIO

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.basketball-reference.com/",
}


def fetch_contracts() -> pd.DataFrame:
    url = "https://www.basketball-reference.com/contracts/players.html"
    print(f"Fetching {url}")

    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    df = tables[0]

    # BRef puts a multi-level header on this table – flatten it
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [" ".join(col).strip() for col in df.columns.values]

    # Standard cleaning
    df = df[df.iloc[:, 0] != "Rk"].copy()          # remove repeated header rows
    df = df.rename(columns={df.columns[1]: "PLAYER_NAME", df.columns[2]: "Team"})

    # Keep useful columns (the exact names can shift slightly by season)
    # We look for the 2025-26 salary column
    salary_col = None
    for col in df.columns:
        if "2025-26" in str(col) or "2025/26" in str(col):
            salary_col = col
            break

    if salary_col is None:
        # fallback – take the first salary-like column after Team
        for col in df.columns[3:]:
            if df[col].dtype == object or "Salary" in str(col) or "$" in str(col):
                salary_col = col
                break

    print(f"Using salary column: {salary_col}")

    keep = ["PLAYER_NAME", "Team", salary_col]
    # also keep Guaranteed if it exists
    for col in df.columns:
        if "Guaranteed" in str(col):
            keep.append(col)
            break

    df = df[keep].copy()
    df = df.rename(columns={salary_col: "base_salary"})

    # Clean salary values (remove $ and commas)
    df["base_salary"] = (
        df["base_salary"]
        .astype(str)
        .str.replace(r"[\$,]", "", regex=True)
        .replace(["", "nan", "None"], None)
    )
    df["base_salary"] = pd.to_numeric(df["base_salary"], errors="coerce")

    if "Guaranteed" in df.columns:
        df["Guaranteed"] = (
            df["Guaranteed"]
            .astype(str)
            .str.replace(r"[\$,]", "", regex=True)
            .replace(["", "nan", "None"], None)
        )
        df["Guaranteed"] = pd.to_numeric(df["Guaranteed"], errors="coerce")

    df["SEASON"] = "2025-26"
    df = df.dropna(subset=["PLAYER_NAME", "base_salary"])

    return df


def main():
    df = fetch_contracts()
    out_path = RAW_DIR / "player_salaries_bref_2026.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSuccess! Wrote {len(df)} rows → {out_path}")
    print(df.head(10).to_string())
    print(f"\nColumns: {list(df.columns)}")


if __name__ == "__main__":
    main()
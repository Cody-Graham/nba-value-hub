#!/usr/bin/env python3
from pathlib import Path
import pandas as pd
import requests
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.basketball-reference.com/",
}

def fetch_current_salaries() -> pd.DataFrame:
    url = "https://www.basketball-reference.com/contracts/players.html"
    print(f"Fetching {url}")

    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))
    df = tables[0]

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join(str(c) for c in col).strip() for col in df.columns.values]

    first_col = df.columns[0]
    df = df[df[first_col] != "Rk"].copy()

    df = df.rename(columns={
        df.columns[1]: "PLAYER_NAME",
        df.columns[2]: "Team"
    })

    salary_col = None
    for col in df.columns:
        col_str = str(col)
        if "2025-26" in col_str or "2026-27" in col_str or "2024-25" in col_str:
            salary_col = col
            break
    if salary_col is None:
        for col in df.columns[3:8]:
            salary_col = col
            break

    print(f"Using salary column: {salary_col}")

    keep = ["PLAYER_NAME", "Team", salary_col]
    for col in df.columns:
        if "Guaranteed" in str(col):
            keep.append(col)
            break

    df = df[keep].copy()
    df = df.rename(columns={salary_col: "base_salary"})

    for col in ["base_salary", "Guaranteed"]:
        if col in df.columns:
            df[col] = (
                df[col].astype(str)
                .str.replace(r"[\$,]", "", regex=True)
                .replace(["", "nan", "None", "–", "-"], None)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["SEASON"] = "2025-26"
    df = df.dropna(subset=["PLAYER_NAME", "base_salary"])
    return df

def main():
    df = fetch_current_salaries()
    out_dir = Path(__file__).resolve().parents[1] / "data" / "current"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "player_salaries_current.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows → {out_path}")

if __name__ == "__main__":
    main()
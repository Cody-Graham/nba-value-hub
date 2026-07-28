#!/usr/bin/env python3
"""
Fetch NBA player season stats from Basketball-Reference.
Much more reliable than the live stats.nba.com endpoint.
Outputs Parquet ready for the value / Contribution Rating pipeline.
"""

import argparse
import time
from pathlib import Path
import pandas as pd
import requests
from io import StringIO

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.basketball-reference.com/",
    "Connection": "keep-alive",
}


def get_table(url: str) -> pd.DataFrame:
    """Download a Basketball-Reference stats table and clean it."""
    print(f"  Fetching {url}")
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()

    # pandas.read_html is the most reliable way to parse BRef tables
    tables = pd.read_html(StringIO(response.text), header=0)
    df = tables[0]

    # Remove the repeating header rows that BRef inserts
    df = df[df["Rk"] != "Rk"].copy()

    # Drop the rank column – we don’t need it
    if "Rk" in df.columns:
        df = df.drop(columns=["Rk"])

    return df


def fetch_season(season_end_year: int = 2026) -> pd.DataFrame:
    """
    season_end_year = 2026 means the 2025-26 season.
    """
    print(f"Fetching Basketball-Reference stats for {season_end_year-1}-{str(season_end_year)[-2:]}...")

    per_game_url = f"https://www.basketball-reference.com/leagues/NBA_{season_end_year}_per_game.html"
    advanced_url = f"https://www.basketball-reference.com/leagues/NBA_{season_end_year}_advanced.html"

    df_per = get_table(per_game_url)
    time.sleep(3)  # be polite
    df_adv = get_table(advanced_url)

    # Standardize player name column
    df_per = df_per.rename(columns={"Player": "PLAYER_NAME"})
    df_adv = df_adv.rename(columns={"Player": "PLAYER_NAME"})

    # Keep only the columns we actually need for Contribution Rating + value analysis
    per_cols = [
        "PLAYER_NAME", "Age", "Team", "Pos", "G", "GS", "MP",
        "FG", "FGA", "FG%", "3P", "3PA", "3P%", "2P", "2PA", "2P%",
        "eFG%", "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST",
        "STL", "BLK", "TOV", "PF", "PTS"
    ]
    adv_cols = [
        "PLAYER_NAME", "Team", "PER", "TS%", "3PAr", "FTr",
        "ORB%", "DRB%", "TRB%", "AST%", "STL%", "BLK%", "TOV%", "USG%",
        "OWS", "DWS", "WS", "WS/48", "OBPM", "DBPM", "BPM", "VORP"
    ]

    # Some columns may be missing in older seasons – take intersection
    per_cols = [c for c in per_cols if c in df_per.columns]
    adv_cols = [c for c in adv_cols if c in df_adv.columns]

    df_per = df_per[per_cols]
    df_adv = df_adv[adv_cols]

    # Merge on player + team (handles players who were traded)
    df = df_per.merge(df_adv, on=["PLAYER_NAME", "Team"], how="left", suffixes=("", "_adv"))

    # Add season identifier
    df["SEASON"] = f"{season_end_year-1}-{str(season_end_year)[-2:]}"
    df["SEASON_END_YEAR"] = season_end_year

    # Clean numeric columns
    for col in df.columns:
        if col not in ["PLAYER_NAME", "Team", "Pos", "SEASON"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2026,
                        help="Season end year (2026 = 2025-26 season)")
    args = parser.parse_args()

    df = fetch_season(args.year)

    out_path = RAW_DIR / f"player_stats_bref_{args.year}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"\nSuccess! Wrote {len(df)} rows → {out_path}")
    print(f"Columns available: {list(df.columns)}")


if __name__ == "__main__":
    main()
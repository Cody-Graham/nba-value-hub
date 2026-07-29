#!/usr/bin/env python3
import argparse
import time
from pathlib import Path
import pandas as pd
import requests
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.basketball-reference.com/",
}

def get_table(url: str) -> pd.DataFrame:
    response = requests.get(url, headers=HEADERS, timeout=60)
    response.raise_for_status()
    tables = pd.read_html(StringIO(response.text), header=0)
    df = tables[0]
    df = df[df["Rk"] != "Rk"].copy()
    if "Rk" in df.columns:
        df = df.drop(columns=["Rk"])
    return df

def fetch_season(season_end_year: int) -> pd.DataFrame:
    season_str = f"{season_end_year-1}-{str(season_end_year)[-2:]}"
    print(f"Fetching {season_str} ...")

    per_game_url = f"https://www.basketball-reference.com/leagues/NBA_{season_end_year}_per_game.html"
    advanced_url = f"https://www.basketball-reference.com/leagues/NBA_{season_end_year}_advanced.html"

    df_per = get_table(per_game_url)
    time.sleep(3)
    df_adv = get_table(advanced_url)

    df_per = df_per.rename(columns={"Player": "PLAYER_NAME"})
    df_adv = df_adv.rename(columns={"Player": "PLAYER_NAME"})

    per_keep = [c for c in [
        "PLAYER_NAME", "Age", "Team", "Pos", "G", "GS", "MP",
        "FG", "FGA", "FG%", "3P", "3PA", "3P%", "2P", "2PA", "2P%",
        "eFG%", "FT", "FTA", "FT%", "ORB", "DRB", "TRB", "AST",
        "STL", "BLK", "TOV", "PF", "PTS"
    ] if c in df_per.columns]

    adv_keep = [c for c in [
        "PLAYER_NAME", "Team", "PER", "TS%", "3PAr", "FTr",
        "ORB%", "DRB%", "TRB%", "AST%", "STL%", "BLK%", "TOV%", "USG%",
        "OWS", "DWS", "WS", "WS/48", "OBPM", "DBPM", "BPM", "VORP"
    ] if c in df_adv.columns]

    df_per = df_per[per_keep]
    df_adv = df_adv[adv_keep]

    df = df_per.merge(df_adv, on=["PLAYER_NAME", "Team"], how="left")
    df["SEASON"] = season_str
    df["SEASON_END_YEAR"] = season_end_year

    for col in df.columns:
        if col not in ["PLAYER_NAME", "Team", "Pos", "SEASON"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.sort_values(["PLAYER_NAME", "SEASON", "Team"])
    df = df.drop_duplicates(subset=["PLAYER_NAME", "SEASON"], keep="first")
    return df

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--outdir", type=str, default=None)
    args = parser.parse_args()

    df = fetch_season(args.year)

    if args.outdir:
        out_dir = Path(args.outdir)
    else:
        out_dir = Path(__file__).resolve().parents[1] / "data" / "current"

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"player_stats_{args.year}.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Wrote {len(df)} rows → {out_path}")

if __name__ == "__main__":
    main()
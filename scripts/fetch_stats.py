#!/usr/bin/env python3
"""
Fetch NBA player season stats + advanced metrics via nba_api.
Hardened version – works with current nba_api releases.
"""

import argparse
import time
from pathlib import Path
import pandas as pd

try:
    from nba_api.stats.endpoints import leaguedashplayerstats
    from nba_api.stats.static import players
except ImportError:
    raise SystemExit("Install nba_api: pip install nba_api pandas pyarrow")

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

CUSTOM_HEADERS = {
    "Host": "stats.nba.com",
    "Connection": "keep-alive",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}


def fetch_with_retry(endpoint_class, max_retries=4, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Attempt {attempt}/{max_retries}...")
            obj = endpoint_class(
                headers=CUSTOM_HEADERS,
                timeout=120,
                **kwargs
            )
            return obj.get_data_frames()[0]
        except Exception as e:
            print(f"  Failed: {type(e).__name__}: {e}")
            if attempt == max_retries:
                raise
            wait = 8 * attempt
            print(f"  Waiting {wait}s before retry...")
            time.sleep(wait)


def fetch_season_stats(season: str = "2025-26", season_type: str = "Regular Season") -> pd.DataFrame:
    print(f"Fetching league dash player stats for {season} ({season_type})...")

    df_base = fetch_with_retry(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        season_type_all_star=season_type,
        measure_type_detailed_defense="Base",
        per_mode_detailed="PerGame",
    )
    time.sleep(3)

    df_adv = fetch_with_retry(
        leaguedashplayerstats.LeagueDashPlayerStats,
        season=season,
        season_type_all_star=season_type,
        measure_type_detailed_defense="Advanced",
        per_mode_detailed="PerGame",
    )

    keep_adv = [c for c in df_adv.columns if c not in df_base.columns or c == "PLAYER_ID"]
    df = df_base.merge(df_adv[keep_adv], on="PLAYER_ID", how="left")
    df["SEASON"] = season
    return df


def fetch_player_index() -> pd.DataFrame:
    return pd.DataFrame(players.get_players())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2025-26")
    args = parser.parse_args()

    stats = fetch_season_stats(args.season)
    out_path = RAW_DIR / f"player_stats_{args.season.replace('-', '_')}.parquet"
    stats.to_parquet(out_path, index=False)
    print(f"Wrote {len(stats)} rows → {out_path}")

    idx = fetch_player_index()
    idx_path = RAW_DIR / "nba_player_index.parquet"
    idx.to_parquet(idx_path, index=False)
    print(f"Wrote player index ({len(idx)} players) → {idx_path}")


if __name__ == "__main__":
    main()
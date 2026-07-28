#!/usr/bin/env python3
"""
Join stats + salaries on crosswalk and compute value rankings.
Primary metric: salary / VORP (or BPM fallback).
Outputs data/processed/value_leaderboard.parquet + .csv
"""

from pathlib import Path
import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)


def compute_value(stats: pd.DataFrame, salaries: pd.DataFrame, crosswalk: pd.DataFrame) -> pd.DataFrame:
    """
    Expects:
      stats: PLAYER_ID, PLAYER_NAME, GP, MIN, VORP (or BPM), ...
      salaries: Player, Team, salary_current, Guaranteed, bref_id (or name)
      crosswalk: nba_id, bref_id, full_name
    """
    # Normalize join keys
    s = stats.rename(columns={"PLAYER_ID": "nba_id"})
    c = crosswalk.copy()
    sal = salaries.copy()

    # Prefer bref_id join if available, else cleaned name
    if "bref_id" in sal.columns and "bref_id" in c.columns:
        joined = s.merge(c, on="nba_id", how="inner").merge(sal, on="bref_id", how="left")
    else:
        sal["clean_name"] = sal["Player"].str.lower().str.replace(r"[^a-z\s]", "", regex=True)
        joined = s.merge(c, on="nba_id", how="inner").merge(sal, on="clean_name", how="left")

    # Value metric – protect against zero / missing impact
    impact_col = "VORP" if "VORP" in joined.columns else "BPM"
    if impact_col not in joined.columns:
        # fallback demo: use PTS as proxy (replace in production)
        impact_col = "PTS"
    joined["impact"] = joined[impact_col].fillna(0).clip(lower=0.01)
    joined["salary"] = pd.to_numeric(joined.get("2026-27", joined.get("salary_current", 0)), errors="coerce").fillna(0)
    joined["dollars_per_impact"] = joined["salary"] / joined["impact"]
    joined["value_rank"] = joined["dollars_per_impact"].rank(method="min")

    cols = [
        "nba_id", "full_name", "PLAYER_NAME", "Tm", "Team",
        "salary", "Guaranteed", impact_col, "dollars_per_impact", "value_rank",
        "GP", "MIN"
    ]
    cols = [c for c in cols if c in joined.columns]
    return joined[cols].sort_values("value_rank")


def main():
    print("Value computation script ready.")
    print("After you have stats + salaries + crosswalk, run this to produce the leaderboard.")
    # Demo with the sample salary we already extracted
    sample_sal = pd.read_csv(Path(__file__).resolve().parents[1] / "data" / "raw" / "bref_contracts_2026_27_sample.csv")
    print(f"Sample salaries loaded: {len(sample_sal)} top contracts")
    out = PROCESSED / "value_leaderboard_sample.csv"
    sample_sal.to_csv(out, index=False)  # placeholder until full join
    print(f"Placeholder leaderboard → {out}")


if __name__ == "__main__":
    main()

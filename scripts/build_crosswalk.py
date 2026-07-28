#!/usr/bin/env python3
"""
Build / update the master player crosswalk.
Matches NBA PLAYER_ID ↔ Basketball-Reference ID via cleaned name + birthdate / draft year.
Outputs data/crosswalk/player_crosswalk.csv
"""

import re
from pathlib import Path
import pandas as pd
from difflib import SequenceMatcher

CROSSWALK_DIR = Path(__file__).resolve().parents[1] / "data" / "crosswalk"
CROSSWALK_DIR.mkdir(parents=True, exist_ok=True)
OUT = CROSSWALK_DIR / "player_crosswalk.csv"


def clean_name(name: str) -> str:
    if pd.isna(name):
        return ""
    name = str(name).lower().strip()
    name = re.sub(r"\s+(jr\.?|sr\.?|iii|ii|iv|v)$", "", name)
    name = re.sub(r"[^a-z\s]", "", name)
    return re.sub(r"\s+", " ", name).strip()


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def build_from_nba_index(nba_idx: pd.DataFrame) -> pd.DataFrame:
    """Start with official NBA static players list."""
    df = nba_idx.copy()
    df["nba_id"] = df["id"]
    df["full_name"] = df["full_name"]
    df["clean_name"] = df["full_name"].apply(clean_name)
    df["is_active"] = df["is_active"]
    return df[["nba_id", "full_name", "clean_name", "is_active"]]


def main():
    # Placeholder: in production load from data/raw/nba_player_index.parquet
    # and a BRef scrape. For now create skeleton that can be filled.
    print("Crosswalk builder ready. Run after fetch_stats.py has produced the index.")
    print(f"Target output: {OUT}")
    # Example skeleton row
    skeleton = pd.DataFrame([
        {
            "nba_id": 2544,
            "full_name": "LeBron James",
            "clean_name": "lebron james",
            "bref_id": "jamesle01",
            "birthdate": "1984-12-30",
            "is_active": True,
            "notes": "canonical example",
        }
    ])
    skeleton.to_csv(OUT, index=False)
    print(f"Wrote skeleton → {OUT}")


if __name__ == "__main__":
    main()

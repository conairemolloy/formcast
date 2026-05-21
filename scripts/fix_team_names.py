import os
import pandas as pd

RESULTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "processed", "results.csv")
)

TEAM_NAME_MAP = {
    "FC Bayern München": "Bayern Munich",
    "Paris Saint-Germain FC": "Paris SG",
    "Club Atlético de Madrid": "Ath Madrid",
    "FC Internazionale Milano": "Inter",
    "Manchester City FC": "Man City",
    "Manchester United FC": "Man United",
    "Arsenal FC": "Arsenal",
    "Chelsea FC": "Chelsea",
    "Liverpool FC": "Liverpool",
    "Tottenham Hotspur FC": "Tottenham",
    "Aston Villa FC": "Aston Villa",
    "Newcastle United FC": "Newcastle",
    "Real Madrid CF": "Real Madrid",
    "FC Barcelona": "Barcelona",
    "Villarreal CF": "Villarreal",
    "Sevilla FC": "Sevilla",
    "AS Monaco FC": "Monaco",
    "Juventus FC": "Juventus",
    "Bologna FC 1909": "Bologna",
    "Celtic FC": "Celtic",
    "AFC Ajax": "Ajax",
    "1. FC Union Berlin": "Union Berlin",
    "FC Koln": "FC Koln",
    "FC Utrecht": "FC Utrecht",
    "FC Groningen": "Groningen",
    "FC Twente '65": "Twente",
    "FC Volendam": "Volendam",
    "Girona FC": "Girona",
    "FC København": "Copenhagen",
    "FC Porto": "Porto",
    "FC Red Bull Salzburg": "RB Salzburg",
    "Almere City FC": "Almere",
    "Royal Antwerp FC": "Antwerp",
    "Paphos FC": "Paphos",
}


def main() -> None:
    print(f"Loading {RESULTS_PATH}...")
    df = pd.read_csv(RESULTS_PATH, low_memory=False)
    print(f"  {len(df):,} rows loaded")

    counts = {official: 0 for official in TEAM_NAME_MAP}

    for col in ("home_team", "away_team"):
        for official, short in TEAM_NAME_MAP.items():
            mask = df[col] == official
            n = mask.sum()
            if n:
                df.loc[mask, col] = short
                counts[official] += n

    replaced = {k: v for k, v in counts.items() if v > 0}

    if not replaced:
        print("No replacements needed.")
        return

    print("\n--- Replacements ---")
    for official, n in sorted(replaced.items(), key=lambda x: -x[1]):
        print(f"  {official:<40} → {TEAM_NAME_MAP[official]:<20} ({n} rows)")
    print(f"\n  Total cells changed: {sum(replaced.values())}")

    df.to_csv(RESULTS_PATH, index=False)
    print(f"\nSaved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()

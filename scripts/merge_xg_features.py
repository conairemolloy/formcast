import pandas as pd

TEAM_NAME_MAP = {
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Newcastle United": "Newcastle",
    "Tottenham": "Tottenham",
    "Nottingham Forest": "Nott'm Forest",
    "Sheffield United": "Sheffield United",
    "West Bromwich Albion": "West Brom",
    "Wolverhampton Wanderers": "Wolves",
    "Leicester City": "Leicester",
    "Leeds United": "Leeds",
    "Aston Villa": "Aston Villa",
    "Brighton": "Brighton",
    "Atletico Madrid": "Ath Madrid",
    "Athletic Club": "Ath Bilbao",
    "Real Betis": "Betis",
    "Rayo Vallecano": "Vallecano",
    "Celta Vigo": "Celta",
    "Deportivo Alaves": "Alaves",
    "Cadiz": "Cadiz",
    "Getafe": "Getafe",
    "Bayern Munich": "Bayern Munich",
    "Borussia Dortmund": "Dortmund",
    "RB Leipzig": "RB Leipzig",
    "Bayer Leverkusen": "Leverkusen",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "Borussia Monchengladbach": "M'gladbach",
    "Werder Bremen": "Werder Bremen",
    "VfB Stuttgart": "Stuttgart",
    "SC Freiburg": "Freiburg",
    "FC Augsburg": "Augsburg",
    "FC Cologne": "FC Koln",
    "FC Union Berlin": "Union Berlin",
    "VfL Wolfsburg": "Wolfsburg",
    "VfL Bochum": "Bochum",
    "TSG Hoffenheim": "Hoffenheim",
    "FSV Mainz 05": "Mainz",
    "Paris Saint-Germain": "Paris SG",
    "Olympique Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "AS Monaco": "Monaco",
    "RC Lens": "Lens",
    "OGC Nice": "Nice",
    "Stade Rennais": "Rennes",
    "Lille": "Lille",
    "Stade Brestois": "Brest",
    "RC Strasbourg": "Strasbourg",
    "Toulouse": "Toulouse",
    "Nantes": "Nantes",
    "Montpellier": "Montpellier",
    "Reims": "Reims",
    "Angers": "Angers",
    "Le Havre": "Le Havre",
    "Saint-Etienne": "St Etienne",
    "Auxerre": "Auxerre",
    "AC Milan": "Milan",
    "Inter": "Inter",
    "Juventus": "Juventus",
    "AS Roma": "Roma",
    "Lazio": "Lazio",
    "Atalanta": "Atalanta",
    "Fiorentina": "Fiorentina",
    "Napoli": "Napoli",
    "Bologna": "Bologna",
    "Torino": "Torino",
    "Udinese": "Udinese",
    "Sassuolo": "Sassuolo",
    "Genoa": "Genoa",
    "Verona": "Verona",
    "Cagliari": "Cagliari",
    "Empoli": "Empoli",
    "Lecce": "Lecce",
    "Monza": "Monza",
    "Frosinone": "Frosinone",
    "Salernitana": "Salernitana",
    "Spezia": "Spezia",
    "Cremonese": "Cremonese",
}

results = pd.read_csv("data/processed/results.csv")
xg = pd.read_csv("data/processed/xg_data.csv")

xg = xg.copy()
xg["home_team"] = xg["home_team"].replace(TEAM_NAME_MAP)
xg["away_team"] = xg["away_team"].replace(TEAM_NAME_MAP)

results["match_date"] = pd.to_datetime(results["match_date"]).dt.date.astype(str)
xg["match_date"] = pd.to_datetime(xg["match_date"]).dt.date.astype(str)

results["league"] = results["league"].str.strip()
xg["league"] = xg["league"].str.strip()

print("results.csv leagues:", sorted(results["league"].unique()))
print("xg_data.csv leagues:", sorted(xg["league"].unique()))

real_madrid = results[(results["home_team"] == "Real Madrid") | (results["away_team"] == "Real Madrid")]
print("Real Madrid in results:", len(real_madrid), "matches, sample date:", real_madrid["match_date"].iloc[0] if len(real_madrid) else "none")
xg_rm = xg[(xg["home_team"] == "Real Madrid") | (xg["away_team"] == "Real Madrid")]
print("Real Madrid in xg after mapping:", len(xg_rm), "matches, sample date:", xg_rm["match_date"].iloc[0] if len(xg_rm) else "none")

xg_deduped = xg.drop_duplicates(subset=["match_date", "home_team", "away_team", "league"])

merged = results.merge(
    xg_deduped[["match_date", "home_team", "away_team", "league", "home_xg", "away_xg", "xg_diff"]],
    on=["match_date", "home_team", "away_team", "league"],
    how="left",
)

n_results = len(results)
n_xg = len(xg)
n_joined = merged["home_xg"].notna().sum()
join_rate = n_joined / n_results * 100

print(f"Total matches in results.csv:   {n_results:,}")
print(f"Total matches in xg_data.csv:   {n_xg:,}")
print(f"Total matches successfully joined: {n_joined:,}")
print(f"Join rate: {join_rate:.1f}%")

unmatched_mask = merged["home_xg"].isna()
if unmatched_mask.any():
    unmatched = merged.loc[unmatched_mask, ["match_date", "home_team", "away_team", "league"]].copy()

    print("\nSample of 5 unmatched rows (from results):")
    print(unmatched.head(5).to_string(index=False))

    xg_sample_teams = unmatched["home_team"].iloc[:5].tolist()
    xg_candidates = xg_deduped[xg_deduped["home_team"].isin(xg_sample_teams)]
    if not xg_candidates.empty:
        print("\nCorresponding rows in xg_data for those home teams:")
        print(xg_candidates[["match_date", "home_team", "away_team", "league"]].head(5).to_string(index=False))

    team_counts = pd.concat([
        unmatched["home_team"].rename("team"),
        unmatched["away_team"].rename("team"),
    ]).value_counts()
    print("\nUnmatched teams (top 20 by frequency):")
    print(team_counts.head(20).to_string())
else:
    print("\nAll matches joined successfully — no unmatched teams.")

merged.to_csv("data/processed/results_with_xg.csv", index=False)
print(f"\nSaved {len(merged):,} rows to data/processed/results_with_xg.csv")

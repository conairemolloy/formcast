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
    "Rangers FC": "Rangers",
    "AFC Ajax": "Ajax",
    "Borussia Dortmund": "Dortmund",
    "Bayer 04 Leverkusen": "Leverkusen",
    "SS Lazio": "Lazio",
    "AC Milan": "Milan",
    "Olympique de Marseille": "Marseille",
    "Olympique Lyonnais": "Lyon",
    "Atletico Madrid": "Ath Madrid",
    "Real Sociedad de Futbol": "Sociedad",
    "Athletic Club": "Ath Bilbao",
    "Eintracht Frankfurt": "Ein Frankfurt",
    "Borussia Monchengladbach": "M'gladbach",
    "VfB Stuttgart": "Stuttgart",
    "Sport Lisboa e Benfica": "Benfica",
    "Sporting Clube de Portugal": "Sporting",
    "FC Nantes": "Nantes",
    "Stade Rennais FC": "Rennes",
    "LOSC Lille": "Lille",
    "RC Lens": "Lens",
    "OGC Nice": "Nice",
    "RC Strasbourg Alsace": "Strasbourg",
    "Stade de Reims": "Reims",
    "Paris FC": "Paris FC",
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

    # ── football-data.org names seen in 2026-27 upcoming fixtures ──────────
    # predict_upcoming.py checks this map first, so every entry here must
    # point at a name that exists in results.csv / elo_ratings.csv.
    # England
    "Nottingham Forest FC": "Nott'm Forest",
    "Wolverhampton Wanderers FC": "Wolves",
    "Brighton & Hove Albion FC": "Brighton",
    "West Ham United FC": "West Ham",
    "Leeds United FC": "Leeds",
    "Leicester City FC": "Leicester",
    "Ipswich Town FC": "Ipswich",
    "Coventry City FC": "Coventry",
    "Sunderland AFC": "Sunderland",
    "AFC Bournemouth": "Bournemouth",
    "Hull City AFC": "Hull",
    "Swansea City AFC": "Swansea",
    "Bristol City FC": "Bristol City",
    "Norwich City FC": "Norwich",
    "Stoke City FC": "Stoke",
    "Birmingham City FC": "Birmingham",
    "Cardiff City FC": "Cardiff",
    "Sheffield United FC": "Sheffield United",
    "Sheffield Wednesday FC": "Sheffield Weds",
    "Queens Park Rangers FC": "QPR",
    "West Bromwich Albion FC": "West Brom",
    "Preston North End FC": "Preston",
    "Blackburn Rovers FC": "Blackburn",
    "Charlton Athletic FC": "Charlton",
    "Derby County FC": "Derby",
    "Oxford United FC": "Oxford",
    "Wrexham AFC": "Wrexham",
    "Lincoln City FC": "Lincoln",  # promoted 2026-27; canonical exists once 2026-27 is ingested
    # Suffix-less forms (prediction_log stores these). Pinned so they never hit
    # fuzzy matching — "Queens Park Rangers" otherwise matches Scottish "Rangers".
    "Queens Park Rangers": "QPR",
    "Manchester City": "Man City",
    "Manchester United": "Man United",
    "Nottingham Forest": "Nott'm Forest",
    "Wolverhampton Wanderers": "Wolves",
    "Sheffield Wednesday": "Sheffield Weds",
    "Brighton & Hove Albion": "Brighton",
    "Tottenham Hotspur": "Tottenham",
    "Lincoln City": "Lincoln",
    # More suffix-less forms found in prediction_log.csv (each checked by hand).
    # Deliberately NOT mapped — ambiguous, settled only via opponent anchoring:
    # "Manchester", "Sheffield", "Paris".
    "Paris Saint-Germain": "Paris SG",
    "Birmingham City": "Birmingham",
    "Blackburn Rovers": "Blackburn",
    "Bolton Wanderers": "Bolton",
    "Cardiff City": "Cardiff",
    "Charlton Athletic": "Charlton",
    "Derby County": "Derby",
    "Norwich City": "Norwich",
    "Preston North End": "Preston",
    "Stoke City": "Stoke",
    "Swansea City": "Swansea",
    "West Bromwich Albion": "West Brom",
    "Coventry City": "Coventry",
    "Hull City": "Hull",
    "Ipswich Town": "Ipswich",
    "FC Augsburg": "Augsburg",
    "FC Schalke 04": "Schalke 04",
    "SC Freiburg": "Freiburg",
    "AS Monaco": "Monaco",
    "ES Troyes AC": "Troyes",
    "Lille OSC": "Lille",
    "Racing Club de Lens": "Lens",
    "Stade Brestois 29": "Brest",
    "CA Osasuna": "Osasuna",
    "Real Racing Club de Santander": "Santander",
    "AC Monza": "Monza",
    "ACF Fiorentina": "Fiorentina",
    "AS Roma": "Roma",
    "Cagliari Calcio": "Cagliari",
    "Frosinone Calcio": "Frosinone",
    "Genoa CFC": "Genoa",
    "Parma Calcio 1913": "Parma",
    "SSC Napoli": "Napoli",
    "US Lecce": "Lecce",
    "Udinese Calcio": "Udinese",
    # Spain
    "Deportivo Alavés": "Alaves",
    "Málaga CF": "Malaga",
    "Málaga": "Malaga",
    "RC Deportivo La Coruña": "La Coruna",
    "RCD Espanyol de Barcelona": "Espanol",
    "Real Sociedad de Fútbol": "Sociedad",
    "Real Betis Balompié": "Betis",
    "Rayo Vallecano de Madrid": "Vallecano",
    "RC Celta de Vigo": "Celta",
    "Real Oviedo": "Oviedo",
    "Levante UD": "Levante",
    "Elche CF": "Elche",
    "Racing Santander": "Santander",
    # Germany
    "1. FC Köln": "FC Koln",
    "Borussia Mönchengladbach": "M'gladbach",
    "Hamburger SV": "Hamburg",
    "SV Werder Bremen": "Werder Bremen",
    "TSG 1899 Hoffenheim": "Hoffenheim",
    "1. FSV Mainz 05": "Mainz",
    "VfL Wolfsburg": "Wolfsburg",
    "1. FC Heidenheim 1846": "Heidenheim",
    "FC St. Pauli 1910": "St Pauli",
    "SC Paderborn 07": "Paderborn",
    "SV 07 Elversberg": "Elversberg",
    # Italy
    "Como 1907": "Como",
    "US Sassuolo Calcio": "Sassuolo",
    "US Cremonese": "Cremonese",
    "AC Pisa 1909": "Pisa",
    # France
    "Stade Rennais FC 1901": "Rennes",
    "Le Havre AC": "Le Havre",
    "FC Lorient": "Lorient",
    "FC Metz": "Metz",
    "AJ Auxerre": "Auxerre",
    "Angers SCO": "Angers",
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

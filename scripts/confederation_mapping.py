"""
Enrich data/processed/international_elo_ratings.csv with a 'confederation' column.
FIFA member nations map to their confederation; all others get "Other / Non-FIFA".
"""

import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Confederation mapping — FIFA member nations only (current status, ~211 teams)
# ---------------------------------------------------------------------------

UEFA = "UEFA"
CONMEBOL = "CONMEBOL"
CONCACAF = "CONCACAF"
CAF = "CAF"
AFC = "AFC"
OFC = "OFC"
OTHER = "Other / Non-FIFA"

CONFEDERATION_MAP = {
    # ── UEFA (Europe) ── 55 members ──────────────────────────────────────────
    "Albania": UEFA,
    "Andorra": UEFA,
    "Armenia": UEFA,
    "Austria": UEFA,
    "Azerbaijan": UEFA,
    "Belarus": UEFA,
    "Belgium": UEFA,
    "Bosnia and Herzegovina": UEFA,
    "Bulgaria": UEFA,
    "Croatia": UEFA,
    "Cyprus": UEFA,
    "Czech Republic": UEFA,
    "Denmark": UEFA,
    "England": UEFA,
    "Estonia": UEFA,
    "Faroe Islands": UEFA,
    "Finland": UEFA,
    "France": UEFA,
    "Georgia": UEFA,
    "Germany": UEFA,
    "Gibraltar": UEFA,          # FIFA member since 2016
    "Greece": UEFA,
    "Hungary": UEFA,
    "Iceland": UEFA,
    "Israel": UEFA,             # Geographically Asia; UEFA member since 1994
    "Italy": UEFA,
    "Kazakhstan": UEFA,         # Moved from AFC to UEFA in 2002
    "Kosovo": UEFA,             # FIFA member since 2016
    "Latvia": UEFA,
    "Liechtenstein": UEFA,
    "Lithuania": UEFA,
    "Luxembourg": UEFA,
    "Malta": UEFA,
    "Moldova": UEFA,
    "Monaco": UEFA,
    "Montenegro": UEFA,
    "Netherlands": UEFA,
    "North Macedonia": UEFA,
    "Northern Ireland": UEFA,
    "Norway": UEFA,
    "Poland": UEFA,
    "Portugal": UEFA,
    "Republic of Ireland": UEFA,
    "Romania": UEFA,
    "Russia": UEFA,             # Suspended but historical UEFA member; rated as UEFA
    "San Marino": UEFA,
    "Scotland": UEFA,
    "Serbia": UEFA,
    "Slovakia": UEFA,
    "Slovenia": UEFA,
    "Spain": UEFA,
    "Sweden": UEFA,
    "Switzerland": UEFA,
    "Turkey": UEFA,
    "Ukraine": UEFA,
    "Wales": UEFA,

    # ── CONMEBOL (South America) ── 10 members ───────────────────────────────
    "Argentina": CONMEBOL,
    "Bolivia": CONMEBOL,
    "Brazil": CONMEBOL,
    "Chile": CONMEBOL,
    "Colombia": CONMEBOL,
    "Ecuador": CONMEBOL,
    "Paraguay": CONMEBOL,
    "Peru": CONMEBOL,
    "Uruguay": CONMEBOL,
    "Venezuela": CONMEBOL,

    # ── CONCACAF (North/Central America & Caribbean) ── 41 members ───────────
    "Anguilla": CONCACAF,
    "Antigua and Barbuda": CONCACAF,
    "Aruba": CONCACAF,
    "Bahamas": CONCACAF,
    "Barbados": CONCACAF,
    "Belize": CONCACAF,
    "Bermuda": CONCACAF,
    "British Virgin Islands": CONCACAF,
    "Canada": CONCACAF,
    "Cayman Islands": CONCACAF,
    "Costa Rica": CONCACAF,
    "Cuba": CONCACAF,
    "Curaçao": CONCACAF,
    "Dominica": CONCACAF,
    "Dominican Republic": CONCACAF,
    "El Salvador": CONCACAF,
    "Grenada": CONCACAF,
    "Guatemala": CONCACAF,
    "Guyana": CONCACAF,         # Geographically South America; CONCACAF member
    "Haiti": CONCACAF,
    "Honduras": CONCACAF,
    "Jamaica": CONCACAF,
    "Mexico": CONCACAF,
    "Montserrat": CONCACAF,
    "Nicaragua": CONCACAF,
    "Panama": CONCACAF,
    "Puerto Rico": CONCACAF,
    "Saint Kitts and Nevis": CONCACAF,
    "Saint Lucia": CONCACAF,
    "Saint Vincent and the Grenadines": CONCACAF,
    "Sint Maarten": CONCACAF,
    "Suriname": CONCACAF,
    "Trinidad and Tobago": CONCACAF,
    "Turks and Caicos Islands": CONCACAF,
    "United States": CONCACAF,
    "United States Virgin Islands": CONCACAF,

    # ── CAF (Africa) ── 54 members ───────────────────────────────────────────
    "Algeria": CAF,
    "Angola": CAF,
    "Benin": CAF,
    "Botswana": CAF,
    "Burkina Faso": CAF,
    "Burundi": CAF,
    "Cameroon": CAF,
    "Cape Verde": CAF,
    "Central African Republic": CAF,
    "Chad": CAF,
    "Comoros": CAF,
    "Congo": CAF,
    "DR Congo": CAF,
    "Djibouti": CAF,
    "Egypt": CAF,
    "Equatorial Guinea": CAF,
    "Eritrea": CAF,
    "Eswatini": CAF,
    "Ethiopia": CAF,
    "Gabon": CAF,
    "Gambia": CAF,
    "Ghana": CAF,
    "Guinea": CAF,
    "Guinea-Bissau": CAF,
    "Ivory Coast": CAF,
    "Kenya": CAF,
    "Lesotho": CAF,
    "Liberia": CAF,
    "Libya": CAF,
    "Madagascar": CAF,
    "Malawi": CAF,
    "Mali": CAF,
    "Mauritania": CAF,
    "Mauritius": CAF,
    "Morocco": CAF,
    "Mozambique": CAF,
    "Namibia": CAF,
    "Niger": CAF,
    "Nigeria": CAF,
    "Rwanda": CAF,
    "São Tomé and Príncipe": CAF,
    "Senegal": CAF,
    "Seychelles": CAF,
    "Sierra Leone": CAF,
    "Somalia": CAF,
    "South Africa": CAF,
    "South Sudan": CAF,         # FIFA member since 2012
    "Sudan": CAF,
    "Tanzania": CAF,
    "Togo": CAF,
    "Tunisia": CAF,
    "Uganda": CAF,
    "Zambia": CAF,
    "Zimbabwe": CAF,

    # ── AFC (Asia) ── 47 members ─────────────────────────────────────────────
    "Afghanistan": AFC,
    "Australia": AFC,           # Moved from OFC to AFC in 2006
    "Bahrain": AFC,
    "Bangladesh": AFC,
    "Bhutan": AFC,
    "Brunei": AFC,
    "Cambodia": AFC,
    "China": AFC,
    "Guam": AFC,
    "Hong Kong": AFC,
    "India": AFC,
    "Indonesia": AFC,
    "Iran": AFC,
    "Iraq": AFC,
    "Japan": AFC,
    "Jordan": AFC,
    "Kuwait": AFC,
    "Kyrgyzstan": AFC,
    "Laos": AFC,
    "Lebanon": AFC,
    "Macau": AFC,
    "Malaysia": AFC,
    "Maldives": AFC,
    "Marshall Islands": AFC,    # FIFA member since 2020
    "Mongolia": AFC,
    "Myanmar": AFC,
    "Nepal": AFC,
    "North Korea": AFC,
    "Northern Mariana Islands": AFC,  # FIFA member since 2009
    "Oman": AFC,
    "Pakistan": AFC,
    "Palestine": AFC,           # FIFA member since 1998
    "Philippines": AFC,
    "Qatar": AFC,
    "Saudi Arabia": AFC,
    "Singapore": AFC,
    "Sri Lanka": AFC,
    "South Korea": AFC,
    "Syria": AFC,
    "Taiwan": AFC,              # Competes as Chinese Taipei
    "Tajikistan": AFC,
    "Thailand": AFC,
    "Timor-Leste": AFC,
    "Turkmenistan": AFC,
    "United Arab Emirates": AFC,
    "Uzbekistan": AFC,
    "Vietnam": AFC,
    "Yemen": AFC,

    # ── OFC (Oceania) ── 14 members ──────────────────────────────────────────
    "American Samoa": OFC,
    "Cook Islands": OFC,
    "Fiji": OFC,
    "Kiribati": OFC,            # FIFA member since 2020
    "New Caledonia": OFC,
    "New Zealand": OFC,
    "Niue": OFC,                # FIFA member since 2010
    "Papua New Guinea": OFC,
    "Samoa": OFC,
    "Solomon Islands": OFC,
    "Tahiti": OFC,              # Competes as French Polynesia
    "Tonga": OFC,
    "Tuvalu": OFC,              # FIFA member since 2020
    "Vanuatu": OFC,
}

# ---------------------------------------------------------------------------
# Teams that are explicitly Other / Non-FIFA (not in dict → default, but
# listed here for documentation clarity of special/historical cases)
# ---------------------------------------------------------------------------
# Historical/defunct: Czechoslovakia, German DR, Yugoslavia, North Vietnam,
#   Vietnam Republic, South Yemen, Yemen DPR, Manchukuo, Saarland
# CONIFA/regional: Abkhazia, Artsakh, Basque Country, Catalonia, Kosovo*
#   (*Kosovo IS now FIFA/UEFA above), Somaliland, South Ossetia, etc.
# Non-FIFA territories: French Guiana, Guadeloupe, Martinique (CONCACAF
#   members but not FIFA), Réunion, Western Sahara, Zanzibar, etc.
# ---------------------------------------------------------------------------


def main():
    csv_path = Path("data/processed/international_elo_ratings.csv")
    df = pd.read_csv(csv_path)

    df["confederation"] = df["team"].map(CONFEDERATION_MAP).fillna(OTHER)

    df.to_csv(csv_path, index=False)

    # ── Summary ──────────────────────────────────────────────────────────────
    counts = df["confederation"].value_counts()
    print("Confederation breakdown:")
    print("-" * 35)
    for conf, n in counts.items():
        print(f"  {conf:<25} {n:>3}")
    print(f"  {'TOTAL':<25} {len(df):>3}")

    non_fifa = sorted(df.loc[df["confederation"] == OTHER, "team"].tolist())
    print(f"\nTeams mapped to '{OTHER}' ({len(non_fifa)} teams):")
    for t in non_fifa:
        print(f"  - {t}")

    print(f"\nSaved enriched file to {csv_path}")


if __name__ == "__main__":
    main()

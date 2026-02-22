# scripts/team_meta.py

# scripts/team_meta.py

# Base metadata that doesn't change often (principals might, but less freq than cars)
# We can override principals in the yearly map if needed.

TEAM_META_BASE = {
    "red_bull": {"principal": "Christian Horner", "engine": "Honda RBPT"},
    "ferrari": {"principal": "Frédéric Vasseur", "engine": "Ferrari"},
    "mercedes": {"principal": "Toto Wolff", "engine": "Mercedes"},
    "mclaren": {"principal": "Andrea Stella", "engine": "Mercedes"},
    "aston_martin": {"principal": "Mike Krack", "engine": "Mercedes"},
    "alpine": {"principal": "Bruno Famin", "engine": "Renault"},
    "williams": {"principal": "James Vowles", "engine": "Mercedes"},
    "haas": {"principal": "Ayao Komatsu", "engine": "Ferrari"},
    "rb": {"principal": "Laurent Mekies", "engine": "Honda RBPT"},
    "sauber": {"principal": "Alessandro Alunni Bravi", "engine": "Ferrari"}, # Audi in 2026
    "audi": {"principal": "Mattia Binotto", "engine": "Audi"} # Future proofing
}

# Yearly specific data (Cars)
TEAM_YEARLY = {
    2024: {
        "red_bull": {"car": "RB20"},
        "ferrari": {"car": "SF-24"},
        "mercedes": {"car": "W15"},
        "mclaren": {"car": "MCL38"},
        "aston_martin": {"car": "AMR24"},
        "alpine": {"car": "A524"},
        "williams": {"car": "FW46"},
        "haas": {"car": "VF-24"},
        "rb": {"car": "VCARB 01"},
        "sauber": {"car": "C44"}
    },
    2025: {
        "red_bull": {"car": "RB21"},
        "ferrari": {"car": "SF-25"},
        "mercedes": {"car": "W16"},
        "mclaren": {"car": "MCL39"},
        "aston_martin": {"car": "AMR25"},
        "alpine": {"car": "A525"},
        "williams": {"car": "FW47"},
        "haas": {"car": "VF-25"},
        "rb": {"car": "VCARB 02"},
        "sauber": {"car": "C45"}
    },
    2026: {
        "red_bull": {"car": "RB22"},
        "ferrari": {"car": "SF-26"},
        "mercedes": {"car": "W17"},
        "mclaren": {"car": "MCL40"},
        "aston_martin": {"car": "AMR26"},
        "alpine": {"car": "A526"},
        "williams": {"car": "FW48"},
        "haas": {"car": "VF-26"},
        "rb": {"car": "VCARB 03"},
        "sauber": {"car": "Audi F1", "principal": "Mattia Binotto", "engine": "Audi"},
        "audi": {"car": "Audi F1"}
    }
}

# Aliases to map weird API IDs to our standard keys
TEAM_ALIASES = {
    "red_bull_racing": "red_bull",
    "scuderia_ferrari": "ferrari",
    "mercedes_amg_petronas_f1_team": "mercedes",
    "mclaren_racing": "mclaren",
    "aston_martin_aramco_cognizant_f1_team": "aston_martin",
    "alpine_f1_team": "alpine",
    "williams_racing": "williams",
    "haas_f1_team": "haas",
    "scuderia_alphatauri": "rb",
    "alphatauri": "rb",
    "racing_bulls": "rb",
    "rb": "rb",
    "alfa_romeo": "sauber",
    "alfa_romeo_racing": "sauber",
    "kick_sauber": "sauber",
    "stake_f1_team_kick_sauber": "sauber",
    "audi": "sauber",
    "mclaren": "mclaren",
    "mercedes": "mercedes",
    "ferrari": "ferrari",
    "williams": "williams",
    "alpine": "alpine",
    "aston_martin": "aston_martin",
    "haas": "haas"
}

CDN_SLUG_MAP = {
    "red_bull": "redbullracing",
    "ferrari": "ferrari",
    "mercedes": "mercedes",
    "mclaren": "mclaren",
    "aston_martin": "astonmartin",
    "alpine": "alpine",
    "williams": "williams",
    "haas": "haasf1team",
    "rb": "racingbulls",
    "sauber": "kicksauber",
    "audi": "audi"
}

def get_team_meta(constructor_id, season=None):
    """
    Safe lookup for team metadata handling aliases and seasons.
    If season is None or not found, defaults to 2024 data (most complete imagery).
    """
    # Normalize ID
    team_key = constructor_id
    if constructor_id in TEAM_ALIASES:
        team_key = TEAM_ALIASES[constructor_id]
        
    # Get Base Data
    base = TEAM_META_BASE.get(team_key, {}).copy()
    
    # Resolve Season Year
    try:
        year = int(season) if season else 2024
    except:
        year = 2024

    # Get Yearly Data
    season_data = TEAM_YEARLY.get(year, TEAM_YEARLY.get(2024, {})).get(team_key, {})
    
    # Dynamic F1 CDN URL Generation
    slug = CDN_SLUG_MAP.get(team_key)
    if slug:
        # F1 introduced a new CDN structure and relies on fallback properties for new/unrevealed cars
        if year >= 2026:
            fallback = f"d_common:f1:{year}:fallback:car:{year}fallbackcarright.webp/"
        else:
            fallback = ""
            
        season_data["car_image"] = f"https://media.formula1.com/image/upload/c_lfill,w_512/q_auto/{fallback}v1740000000/common/f1/{year}/{slug}/{year}{slug}carright.webp"

    # Merge
    base.update(season_data)
    
    return base

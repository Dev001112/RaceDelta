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

# Yearly specific data (Cars, Images)
TEAM_YEARLY = {
    2024: {
        "red_bull": {"car": "RB20", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Red_Bull_Racing.png"},
        "ferrari": {"car": "SF-24", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Ferrari.png"},
        "mercedes": {"car": "W15", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Mercedes.png"},
        "mclaren": {"car": "MCL38", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/McLaren_FK4.png"},
        "aston_martin": {"car": "AMR24", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Aston_Martin.png"},
        "alpine": {"car": "A524", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Alpine.png"},
        "williams": {"car": "FW46", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Williams.png"},
        "haas": {"car": "VF-24", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Haas.png"},
        "rb": {"car": "VCARB 01", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/RB.png"},
        "sauber": {"car": "C44", "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Kick_Sauber.png"}
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
    "audi": "sauber"
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
    # If explicit year missing, fall back to 2024 (has images)
    season_data = TEAM_YEARLY.get(year, TEAM_YEARLY.get(2024, {})).get(team_key, {})
    
    # If the specific season doesn't have an image, try to fallback to 2024 image
    # so we don't show blank 
    if "car_image" not in season_data and year != 2024:
        fallback_img = TEAM_YEARLY.get(2024, {}).get(team_key, {}).get("car_image")
        if fallback_img:
            season_data["car_image"] = fallback_img
            
    # Merge
    base.update(season_data)
    
    return base

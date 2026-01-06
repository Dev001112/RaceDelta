# scripts/team_meta.py

TEAM_META = {
    "red_bull": {
        "principal": "Christian Horner",
        "engine": "Honda RBPT",
        "car": "RB20",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Red_Bull_Racing.png"
    },
    "ferrari": {
        "principal": "Frédéric Vasseur",
        "engine": "Ferrari",
        "car": "SF-24",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Ferrari.png"
    },
    "mercedes": {
        "principal": "Toto Wolff",
        "engine": "Mercedes",
        "car": "W15",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Mercedes.png"
    },
    "mclaren": {
        "principal": "Andrea Stella",
        "engine": "Mercedes",
        "car": "MCL38",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/McLaren_FK4.png"
    },
    "aston_martin": {
        "principal": "Mike Krack",
        "engine": "Mercedes",
        "car": "AMR24",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Aston_Martin.png"
    },
    "alpine": {
        "principal": "Bruno Famin",
        "engine": "Renault",
        "car": "A524",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Alpine.png"
    },
    "williams": {
        "principal": "James Vowles",
        "engine": "Mercedes",
        "car": "FW46",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Williams.png"
    },
    "haas": {
        "principal": "Ayao Komatsu",
        "engine": "Ferrari",
        "car": "VF-24",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Haas.png"
    },
    "rb": {
        "principal": "Laurent Mekies",
        "engine": "Honda RBPT",
        "car": "VCARB 01",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/RB.png"
    },
    "sauber": {
        "principal": "Alessandro Alunni Bravi",
        "engine": "Ferrari",
        "car": "C44",
        "car_image": "https://media.formula1.com/image/upload/f_auto/q_auto/v1708092248/f1/cars/2024/Kick_Sauber.png"
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
    "alfa_romeo": "sauber",
    "alfa_romeo_racing": "sauber",
    "kick_sauber": "sauber",
    "stake_f1_team_kick_sauber": "sauber"
}

def get_team_meta(constructor_id):
    """Safe lookup for team metadata handling aliases"""
    # Try direct match
    if constructor_id in TEAM_META:
        return TEAM_META[constructor_id]
    
    # Try alias
    normalized = TEAM_ALIASES.get(constructor_id)
    if normalized and normalized in TEAM_META:
        return TEAM_META[normalized]
        
    return {}

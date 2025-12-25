# app/services/points_system.py

FIA_POINTS = {
    1: 25,
    2: 18,
    3: 15,
    4: 12,
    5: 10,
    6: 8,
    7: 6,
    8: 4,
    9: 2,
    10: 1
}

def points_for_position(position):
    try:
        position = int(position)
    except (TypeError, ValueError):
        return 0

    return FIA_POINTS.get(position, 0)

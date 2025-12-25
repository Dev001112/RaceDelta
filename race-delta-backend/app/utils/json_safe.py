import math

def make_json_safe(value):
    if isinstance(value, float) and math.isnan(value):
        return 0
    return value

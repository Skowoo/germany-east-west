
EAST_GERMANY = {
    "DE40": "Brandenburg",
    "DE80": "Mecklenburg-Vorpommern",
    "DED2": "Dresden",
    "DED4": "Chemnitz",
    "DED5": "Leipzig",
    "DEE0": "Sachsen-Anhalt",
    "DEG0": "Thüringen",
}

BERLIN = "DE30"


def get_region_group(geo_code: str) -> str | None:
    if geo_code in EAST_GERMANY:
        return "East"

    if geo_code == BERLIN:
        return None

    if geo_code.startswith("DE") and len(geo_code) == 4:
        return "West"

    return None

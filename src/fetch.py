import requests

URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = [
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "cloud_cover",
    "temperature_2m",
    "wind_speed_10m",
]


def fetch_data(locations, hourly_vars=HOURLY_VARS, timezone="Asia/Makassar", timeout=30):
    params = {
        "latitude": ",".join(str(loc["lat"]) for loc in locations),
        "longitude": ",".join(str(loc["lon"]) for loc in locations),
        "hourly": ",".join(hourly_vars),
        "timezone": timezone,
    }

    response = requests.get(URL, params=params, timeout=timeout)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict):
        data = [data]

    if len(data) != len(locations):
        raise ValueError(f"Jumlah respons ({len(data)}) != jumlah lokasi ({len(locations)})")

    return data
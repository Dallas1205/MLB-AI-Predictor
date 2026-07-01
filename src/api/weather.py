import requests
from datetime import datetime, timezone


STADIUM_COORDS = {
    "Oriole Park at Camden Yards": {"lat": 39.2839, "lon": -76.6217},
    "Guaranteed Rate Field": {"lat": 41.8300, "lon": -87.6339},
    "Yankee Stadium": {"lat": 40.8296, "lon": -73.9262},
    "Fenway Park": {"lat": 42.3467, "lon": -71.0972},
    "Dodger Stadium": {"lat": 34.0739, "lon": -118.2400},
    "Oracle Park": {"lat": 37.7786, "lon": -122.3893},
    "Coors Field": {"lat": 39.7559, "lon": -104.9942},
    "Wrigley Field": {"lat": 41.9484, "lon": -87.6553},
    "Citi Field": {"lat": 40.7571, "lon": -73.8458},
    "T-Mobile Park": {"lat": 47.5914, "lon": -122.3325},
    "Petco Park": {"lat": 32.7073, "lon": -117.1573},
    "Chase Field": {"lat": 33.4455, "lon": -112.0667},
    "Globe Life Field": {"lat": 32.7473, "lon": -97.0842},
    "Minute Maid Park": {"lat": 29.7573, "lon": -95.3555},
    "Great American Ball Park": {"lat": 39.0979, "lon": -84.5082},
    "Citizens Bank Park": {"lat": 39.9061, "lon": -75.1665},
    "Busch Stadium": {"lat": 38.6226, "lon": -90.1928},
    "American Family Field": {"lat": 43.0280, "lon": -87.9712},
    "Comerica Park": {"lat": 42.3390, "lon": -83.0485},
    "Truist Park": {"lat": 33.8908, "lon": -84.4678},
    "PNC Park": {"lat": 40.4469, "lon": -80.0057},
    "Progressive Field": {"lat": 41.4962, "lon": -81.6852},
    "Kauffman Stadium": {"lat": 39.0517, "lon": -94.4803},
    "Target Field": {"lat": 44.9817, "lon": -93.2776},
    "Rogers Centre": {"lat": 43.6414, "lon": -79.3894},
    "loanDepot park": {"lat": 25.7781, "lon": -80.2197},
    "Tropicana Field": {"lat": 27.7682, "lon": -82.6534},
    "Angel Stadium": {"lat": 33.8003, "lon": -117.8827},
    "Oakland Coliseum": {"lat": 37.7516, "lon": -122.2005},
    "Sutter Health Park": {"lat": 38.5804, "lon": -121.5135},
    "Nationals Park": {"lat": 38.8730, "lon": -77.0074},
}


def get_stadium_coords(venue):
    return STADIUM_COORDS.get(venue)


def get_game_hour_index(hourly_times, game_time):
    if not game_time or game_time == "Unknown":
        return 0

    game_dt = datetime.fromisoformat(game_time.replace("Z", "+00:00"))

    best_index = 0
    best_diff = None

    for i, time_str in enumerate(hourly_times):
        weather_dt = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
        diff = abs((weather_dt - game_dt).total_seconds())

        if best_diff is None or diff < best_diff:
            best_diff = diff
            best_index = i

    return best_index


def get_weather_for_game(game):
    venue = game.get("venue", "Unknown")
    coords = get_stadium_coords(venue)

    if coords is None:
        return {
            "temp_f": 72,
            "wind_mph": 0,
            "wind_direction": "none",
            "humidity": "unknown",
            "source": f"no stadium coordinates for {venue}",
        }

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": coords["lat"],
        "longitude": coords["lon"],
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,precipitation_probability",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "UTC",
        "forecast_days": 2,
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {
            "temp_f": 72,
            "wind_mph": 0,
            "wind_direction": "none",
            "humidity": "unknown",
            "source": f"weather error: {e}",
        }

    hourly = data.get("hourly", {})
    times = hourly.get("time", [])

    if not times:
        return {
            "temp_f": 72,
            "wind_mph": 0,
            "wind_direction": "none",
            "humidity": "unknown",
            "source": "weather unavailable",
        }

    idx = get_game_hour_index(times, game.get("game_time"))

    temp = hourly["temperature_2m"][idx]
    humidity = hourly["relative_humidity_2m"][idx]
    wind_mph = hourly["wind_speed_10m"][idx]
    wind_deg = hourly["wind_direction_10m"][idx]
    rain = hourly["precipitation_probability"][idx]

    return {
        "temp_f": round(temp, 1),
        "wind_mph": round(wind_mph, 1),
        "wind_degrees": wind_deg,
        "wind_direction": "unknown",
        "humidity": humidity,
        "precipitation_probability": rain,
        "source": "Open-Meteo",
    }


def weather_multiplier(weather):
    temp = weather.get("temp_f", 72)
    wind = weather.get("wind_mph", 0)
    direction = weather.get("wind_direction", "unknown")

    multiplier = 1.00

    if temp >= 85:
        multiplier += 0.05
    elif temp >= 75:
        multiplier += 0.03
    elif temp <= 55:
        multiplier -= 0.03

    if direction == "out":
        multiplier += wind * 0.005
    elif direction == "in":
        multiplier -= wind * 0.005

    return max(0.85, min(multiplier, 1.20))
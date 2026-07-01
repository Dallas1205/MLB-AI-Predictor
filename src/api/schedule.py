import requests

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"


def get_pitcher_info(team_data):
    pitcher = team_data.get("probablePitcher", {})

    return {
        "name": pitcher.get("fullName", "TBD"),
        "id": pitcher.get("id", None),
    }


def get_todays_games():
    params = {
        "sportId": 1,
        "hydrate": "probablePitcher,venue,team",
    }

    response = requests.get(SCHEDULE_URL, params=params, timeout=20)
    response.raise_for_status()

    data = response.json()
    games = []

    for date in data.get("dates", []):
        for game in date.get("games", []):
            away_team = game["teams"]["away"]["team"]
            home_team = game["teams"]["home"]["team"]

            away_pitcher = get_pitcher_info(game["teams"]["away"])
            home_pitcher = get_pitcher_info(game["teams"]["home"])

            games.append({
                "game_id": game["gamePk"],
                "game_time": game.get("gameDate", "Unknown"),

                "away": away_team["name"],
                "home": home_team["name"],

                "away_id": away_team["id"],
                "home_id": home_team["id"],

                "away_abbr": away_team.get("abbreviation", away_team["name"]),
                "home_abbr": home_team.get("abbreviation", home_team["name"]),

                "away_pitcher": away_pitcher["name"],
                "home_pitcher": home_pitcher["name"],

                "away_pitcher_id": away_pitcher["id"],
                "home_pitcher_id": home_pitcher["id"],

                "venue": game.get("venue", {}).get("name", "Unknown"),
                "status": game.get("status", {}).get("detailedState", "Unknown"),
            })

    return games
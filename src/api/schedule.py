import requests
from datetime import datetime, timedelta

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"


def get_pitcher_info(team_data):
    pitcher = team_data.get("probablePitcher", {})

    return {
        "name": pitcher.get("fullName", "TBD"),
        "id": pitcher.get("id"),
    }


def normalize_date(date_value):
    """
    Accepts dates such as:
    2026-07-04
    2026-7-4

    Returns:
    2026-07-04
    """

    parsed_date = datetime.strptime(date_value.strip(), "%Y-%m-%d")
    return parsed_date.strftime("%Y-%m-%d")


def get_games(date=None):
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    else:
        date = normalize_date(date)

    print(f"Fetching games for: {date}")

    params = {
        "sportId": 1,
        "date": date,
        "hydrate": "probablePitcher,venue,team",
    }

    response = requests.get(
        SCHEDULE_URL,
        params=params,
        timeout=20,
    )
    response.raise_for_status()

    data = response.json()
    games = []

    for day in data.get("dates", []):
        schedule_date = day.get("date", date)

        for game in day.get("games", []):
            away = game["teams"]["away"]["team"]
            home = game["teams"]["home"]["team"]

            away_pitcher = get_pitcher_info(
                game["teams"]["away"]
            )
            home_pitcher = get_pitcher_info(
                game["teams"]["home"]
            )

            games.append({
                "game_id": game["gamePk"],
                "schedule_date": schedule_date,
                "game_time": game.get(
                    "gameDate",
                    "Unknown",
                ),

                "away": away["name"],
                "home": home["name"],

                "away_id": away["id"],
                "home_id": home["id"],

                "away_abbr": away.get(
                    "abbreviation",
                    away["name"],
                ),
                "home_abbr": home.get(
                    "abbreviation",
                    home["name"],
                ),

                "away_pitcher": away_pitcher["name"],
                "home_pitcher": home_pitcher["name"],

                "away_pitcher_id": away_pitcher["id"],
                "home_pitcher_id": home_pitcher["id"],

                "venue": game.get(
                    "venue",
                    {},
                ).get(
                    "name",
                    "Unknown",
                ),

                "status": game.get(
                    "status",
                    {},
                ).get(
                    "detailedState",
                    "Unknown",
                ),
            })

    return games


def get_todays_games():
    today = datetime.now().strftime("%Y-%m-%d")
    return get_games(today)


def get_yesterdays_games():
    yesterday = (
        datetime.now() - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    return get_games(yesterday)


def get_tomorrows_games():
    tomorrow = (
        datetime.now() + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    return get_games(tomorrow)


def get_games_in_range(start_date, end_date):
    """
    Returns every MLB game from start_date through end_date,
    including both dates.
    """

    start = datetime.strptime(
        normalize_date(start_date),
        "%Y-%m-%d",
    )

    end = datetime.strptime(
        normalize_date(end_date),
        "%Y-%m-%d",
    )

    if end < start:
        raise ValueError(
            "End date cannot be before start date."
        )

    all_games = []
    current_date = start

    while current_date <= end:
        date_string = current_date.strftime("%Y-%m-%d")

        daily_games = get_games(date_string)
        all_games.extend(daily_games)

        current_date += timedelta(days=1)

    return all_games
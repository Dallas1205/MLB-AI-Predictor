import requests
from datetime import datetime, timedelta

SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"


def get_recent_team_form(team_id, games_back=20):
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=75)

    params = {
        "sportId": 1,
        "teamId": team_id,
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
    }

    try:
        response = requests.get(SCHEDULE_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return default_form()

    games = []

    for day in data.get("dates", []):
        for game in day.get("games", []):
            if game.get("status", {}).get("detailedState") != "Final":
                continue

            home = game["teams"]["home"]
            away = game["teams"]["away"]

            if home["team"]["id"] == team_id:
                scored = home.get("score", 0)
                allowed = away.get("score", 0)
            else:
                scored = away.get("score", 0)
                allowed = home.get("score", 0)

            games.append({
                "scored": scored,
                "allowed": allowed,
                "win": scored > allowed,
            })

    games = games[-games_back:]

    if not games:
        return default_form()

    runs_scored = sum(g["scored"] for g in games)
    runs_allowed = sum(g["allowed"] for g in games)
    wins = sum(1 for g in games if g["win"])
    losses = len(games) - wins

    return {
        "games": len(games),
        "runs_scored": runs_scored,
        "runs_allowed": runs_allowed,
        "wins": wins,
        "losses": losses,
        "runs_per_game": runs_scored / len(games),
        "runs_allowed_per_game": runs_allowed / len(games),
        "run_diff_per_game": (runs_scored - runs_allowed) / len(games),
        "available": True,
    }


def default_form():
    return {
        "games": 0,
        "runs_scored": 0,
        "runs_allowed": 0,
        "wins": 0,
        "losses": 0,
        "runs_per_game": 4.4,
        "runs_allowed_per_game": 4.4,
        "run_diff_per_game": 0,
        "available": False,
    }
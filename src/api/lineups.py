import requests
from src.api.roster import get_likely_hitters
from src.api.players import get_player_bio


def get_game_lineups(game_id, away_team_id=None, home_team_id=None):
    url = f"https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"

    away_lineup = []
    home_lineup = []
    away_sides = []
    home_sides = []

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        teams = data.get("teams", {})
        away = teams.get("away", {})
        home = teams.get("home", {})

        away_players = away.get("players", {})
        home_players = home.get("players", {})

        for player_id in away.get("battingOrder", []):
            player = away_players.get(f"ID{player_id}")
            if player:
                pid = player["person"]["id"]
                bio = get_player_bio(pid)

                away_lineup.append(player["person"]["fullName"])
                away_sides.append(bio.get("bat_side", "R"))

        for player_id in home.get("battingOrder", []):
            player = home_players.get(f"ID{player_id}")
            if player:
                pid = player["person"]["id"]
                bio = get_player_bio(pid)

                home_lineup.append(player["person"]["fullName"])
                home_sides.append(bio.get("bat_side", "R"))

    except Exception:
        pass

    away_fallback = []
    home_fallback = []

    if not away_lineup and away_team_id:
        away_fallback = get_likely_hitters(away_team_id)

    if not home_lineup and home_team_id:
        home_fallback = get_likely_hitters(home_team_id)

    if away_lineup and home_lineup:
        status = "confirmed"
    elif away_lineup or home_lineup:
        status = "partially confirmed"
    else:
        status = "not posted yet - showing active roster hitters as fallback"

    return {
        "away_lineup": away_lineup,
        "home_lineup": home_lineup,
        "away_sides": away_sides,
        "home_sides": home_sides,
        "away_fallback_hitters": away_fallback,
        "home_fallback_hitters": home_fallback,
        "status": status,
    }
import requests
from src.api.players import get_player_bio


def get_active_roster(team_id):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"
    params = {"rosterType": "active"}

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    players = []

    for item in data.get("roster", []):
        person = item.get("person", {})
        position = item.get("position", {})

        player_id = person.get("id")
        bio = get_player_bio(player_id)

        players.append({
            "name": person.get("fullName", "Unknown"),
            "id": player_id,
            "position": position.get("abbreviation", "Unknown"),
            "bat_side": bio.get("bat_side", "R"),
            "throw_hand": bio.get("throw_hand", "R"),
        })

    return players


def get_likely_hitters(team_id):
    roster = get_active_roster(team_id)

    return [
        player for player in roster
        if player["position"] != "P"
    ]
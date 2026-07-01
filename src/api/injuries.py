import requests


def get_team_roster_status(team_id):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster"

    params = {
        "rosterType": "40Man"
    }

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    players = []

    for item in data.get("roster", []):
        person = item.get("person", {})
        status = item.get("status", {})
        position = item.get("position", {})

        players.append({
            "name": person.get("fullName", "Unknown"),
            "id": person.get("id"),
            "position": position.get("abbreviation", "Unknown"),
            "status": status.get("description", "Active")
        })

    return players


def get_injury_notes(players):
    notes = []

    for player in players:
        status = player.get("status", "").lower()

        if "injured" in status or "il" in status or "day" in status:
            notes.append(player)

    return notes
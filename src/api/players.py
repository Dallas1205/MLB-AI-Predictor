import requests


def get_player_bio(player_id):
    if not player_id:
        return {
            "name": "Unknown",
            "bat_side": "R",
            "throw_hand": "R",
        }

    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return {
            "name": "Unknown",
            "bat_side": "R",
            "throw_hand": "R",
        }

    people = data.get("people", [])

    if not people:
        return {
            "name": "Unknown",
            "bat_side": "R",
            "throw_hand": "R",
        }

    player = people[0]

    return {
        "name": player.get("fullName", "Unknown"),
        "bat_side": player.get("batSide", {}).get("code", "R"),
        "throw_hand": player.get("pitchHand", {}).get("code", "R"),
    }
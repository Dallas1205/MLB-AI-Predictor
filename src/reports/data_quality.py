def calculate_data_quality_score(game, lineups, away_status, home_status, weather, park):
    score = 100
    notes = []

    if game.get("away_pitcher") == "TBD":
        score -= 10
        notes.append("Away pitcher is TBD")

    if game.get("home_pitcher") == "TBD":
        score -= 10
        notes.append("Home pitcher is TBD")

    if lineups.get("status") != "confirmed":
        score -= 25
        notes.append("Lineups are not fully confirmed")

    if weather.get("source") == "default placeholder":
        score -= 10
        notes.append("Weather is placeholder data")

    if park.get("run_factor") == 1.00:
        notes.append("Using neutral/default park factor")

    if not away_status:
        score -= 5
        notes.append("Away roster status unavailable")

    if not home_status:
        score -= 5
        notes.append("Home roster status unavailable")

    score = max(0, min(score, 100))

    return {
        "score": score,
        "notes": notes
    }
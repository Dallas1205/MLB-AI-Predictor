def build_model_explanation(game, simulation, park, weather, quality):
    home_prob = simulation["home_win_probability"]
    away_prob = simulation["away_win_probability"]

    text = "\nWhy This Prediction Happened\n"
    text += "----------------------------\n"

    if home_prob > away_prob:
        text += f"- {game['home']} is favored by the simulation.\n"
    else:
        text += f"- {game['away']} is favored by the simulation.\n"

    if game.get("home_pitcher") != "TBD":
        text += f"- Home starter confirmed: {game['home_pitcher']}.\n"

    if game.get("away_pitcher") != "TBD":
        text += f"- Away starter confirmed: {game['away_pitcher']}.\n"

    run_factor = park.get("run_factor", 1.00)

    if run_factor > 1.03:
        text += "- Stadium is hitter-friendly.\n"
    elif run_factor < 0.97:
        text += "- Stadium is pitcher-friendly.\n"
    else:
        text += "- Stadium is close to neutral.\n"

    if weather.get("source") == "default placeholder":
        text += "- Weather is still placeholder data, so confidence is lower.\n"
    else:
        text += "- Weather data is included.\n"

    if quality["score"] < 80:
        text += "- Data quality issues reduce confidence.\n"

    return text
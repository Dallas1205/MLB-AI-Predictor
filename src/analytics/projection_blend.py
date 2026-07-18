def pythagorean_win_pct(runs_scored, runs_allowed, exponent=1.83):
    if runs_scored <= 0 or runs_allowed <= 0:
        return 0.500

    rs = runs_scored ** exponent
    ra = runs_allowed ** exponent

    return rs / (rs + ra)


def regress_to_mean(value, games, mean=0.500, strength=20):
    weight = games / (games + strength)
    return (value * weight) + (mean * (1 - weight))


def blend_projection(simulation, home_form, away_form):
    raw_home = simulation["home_win_probability"]
    raw_away = simulation["away_win_probability"]

    home_pyth = pythagorean_win_pct(
        home_form["runs_scored"],
        home_form["runs_allowed"]
    )

    away_pyth = pythagorean_win_pct(
        away_form["runs_scored"],
        away_form["runs_allowed"]
    )

    home_pyth = regress_to_mean(home_pyth, home_form["games"])
    away_pyth = regress_to_mean(away_pyth, away_form["games"])

    if home_pyth + away_pyth == 0:
        form_home_prob = 0.500
    else:
        form_home_prob = home_pyth / (home_pyth + away_pyth)

    form_away_prob = 1 - form_home_prob

    final_home = (raw_home * 0.75) + (form_home_prob * 0.25)
    final_away = 1 - final_home

    updated = simulation.copy()

    updated["raw_home_win_probability"] = raw_home
    updated["raw_away_win_probability"] = raw_away

    updated["home_win_probability"] = round(final_home, 3)
    updated["away_win_probability"] = round(final_away, 3)

    updated["winner"] = (
        updated["home_team_name"]
        if final_home > final_away
        else updated["away_team_name"]
    ) if "home_team_name" in updated else updated["winner"]

    updated["projection_layers"] = {
        "sim_home_probability": raw_home,
        "form_home_probability": round(form_home_prob, 3),
        "final_home_probability": round(final_home, 3),
        "home_pythagorean": round(home_pyth, 3),
        "away_pythagorean": round(away_pyth, 3),
    }

    return updated
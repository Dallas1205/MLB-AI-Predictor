import random
import numpy as np
from src.api.weather import weather_multiplier


def basic_team_strength(lineup, pitcher_name):
    strength = 4.25

    if lineup:
        strength += min(len(lineup), 9) * 0.08
    else:
        strength -= 0.35

    if pitcher_name != "TBD":
        strength += 0.10
    else:
        strength -= 0.30

    return strength


def run_basic_game_simulation(game, lineups, park, weather, n_sims=10000):
    park_factor = park.get("run_factor", 1.00)
    weather_factor = weather_multiplier(weather)

    away_base = basic_team_strength(
        lineups.get("away_lineup", []),
        game.get("away_pitcher", "TBD")
    )

    home_base = basic_team_strength(
        lineups.get("home_lineup", []),
        game.get("home_pitcher", "TBD")
    )

    home_base += 0.25

    away_lambda = away_base * park_factor * weather_factor / 4.25
    home_lambda = home_base * park_factor * weather_factor / 4.25

    away_wins = 0
    home_wins = 0

    away_scores = []
    home_scores = []

    for _ in range(n_sims):
        away_score = np.random.poisson(away_lambda)
        home_score = np.random.poisson(home_lambda)

        while away_score == home_score:
            away_score += np.random.poisson(0.45)
            home_score += np.random.poisson(0.48)

        if home_score > away_score:
            home_wins += 1
        else:
            away_wins += 1

        away_scores.append(away_score)
        home_scores.append(home_score)

    home_prob = home_wins / n_sims
    away_prob = away_wins / n_sims

    return {
        "away_win_probability": round(away_prob, 3),
        "home_win_probability": round(home_prob, 3),
        "projected_away_score": round(float(np.mean(away_scores)), 2),
        "projected_home_score": round(float(np.mean(home_scores)), 2),
        "projected_total": round(float(np.mean(away_scores) + np.mean(home_scores)), 2),
        "winner": game["home"] if home_prob > away_prob else game["away"]
    }
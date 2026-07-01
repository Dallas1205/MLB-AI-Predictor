import random
import numpy as np

from src.prediction.pa_predictor import predict_plate_appearance
from src.api.weather import weather_multiplier
from src.api.players import get_player_bio


DEFAULT_PROBS = {
    "out": 0.48,
    "strikeout": 0.22,
    "walk": 0.08,
    "single": 0.15,
    "double": 0.04,
    "triple": 0.01,
    "home_run": 0.02,
}


def normalize_probs(probs):
    total = sum(probs.values())

    if total <= 0:
        return DEFAULT_PROBS.copy()

    return {k: v / total for k, v in probs.items()}


def calibrate_probs(probs):
    probs = probs.copy()

    for key in DEFAULT_PROBS:
        probs[key] = probs.get(key, DEFAULT_PROBS[key])

    probs["home_run"] = min(probs["home_run"], 0.055)
    probs["triple"] = min(probs["triple"], 0.012)
    probs["double"] = min(probs["double"], 0.085)
    probs["single"] = min(probs["single"], 0.220)
    probs["walk"] = min(probs["walk"], 0.140)
    probs["strikeout"] = min(probs["strikeout"], 0.350)

    non_out = (
        probs["single"]
        + probs["double"]
        + probs["triple"]
        + probs["home_run"]
        + probs["walk"]
    )

    max_non_out = 0.34

    if non_out > max_non_out:
        scale = max_non_out / non_out

        for key in ["single", "double", "triple", "home_run", "walk"]:
            probs[key] *= scale

    probs["out"] = 1 - (
        probs["strikeout"]
        + probs["walk"]
        + probs["single"]
        + probs["double"]
        + probs["triple"]
        + probs["home_run"]
    )

    probs["out"] = max(probs["out"], 0.36)

    return normalize_probs(probs)


def adjust_for_context(probs, park, weather):
    adjusted = probs.copy()

    park_factor = park.get("run_factor", 1.00)
    weather_factor = weather_multiplier(weather)

    power_factor = park_factor * weather_factor

    for key in ["double", "triple", "home_run"]:
        if key in adjusted:
            adjusted[key] *= power_factor

    return normalize_probs(adjusted)


def choose_outcome(probs):
    return random.choices(
        list(probs.keys()),
        weights=list(probs.values()),
        k=1
    )[0]


def advance_runners(outcome, bases):
    runs = 0

    if outcome == "walk":
        if bases == [1, 1, 1]:
            runs += 1

        if bases[0] == 0:
            bases[0] = 1
        elif bases[1] == 0:
            bases[1] = 1
        elif bases[2] == 0:
            bases[2] = 1

    elif outcome == "single":
        runs += bases[2]

        runner_from_second_scores = bases[1] and random.random() < 0.62
        runner_from_first_to_third = bases[0] and random.random() < 0.30

        new_third = 1 if runner_from_first_to_third else bases[1]
        new_second = 0 if runner_from_first_to_third else bases[0]

        if runner_from_second_scores:
            runs += 1
            new_third = 0

        bases = [1, new_second, new_third]

    elif outcome == "double":
        runs += bases[2] + bases[1]

        if bases[0] and random.random() < 0.42:
            runs += 1
            bases = [0, 1, 0]
        else:
            bases = [0, 1, bases[0]]

    elif outcome == "triple":
        runs += sum(bases)
        bases = [0, 0, 1]

    elif outcome == "home_run":
        runs += sum(bases) + 1
        bases = [0, 0, 0]

    return runs, bases


def estimate_sides(lineup, fallback_hitters=None):
    if fallback_hitters:
        sides = [p.get("bat_side", "R") for p in fallback_hitters[:9]]

        if len(sides) == len(lineup):
            return sides

    return ["R" for _ in lineup]


def build_matchup_prob_cache(
    lineup,
    pitcher,
    batter_sides,
    pitcher_hand,
    home_team,
    park,
    weather
):
    cache = {}

    for i, batter in enumerate(lineup):
        batter_side = batter_sides[i] if i < len(batter_sides) else "R"

        probs = predict_plate_appearance(
            batter_name=batter,
            pitcher_name=pitcher,
            batter_side=batter_side,
            pitcher_hand=pitcher_hand,
            home_team=home_team,
        )

        if probs is None:
            probs = DEFAULT_PROBS.copy()

        probs = adjust_for_context(probs, park, weather)
        probs = calibrate_probs(probs)

        cache[batter] = probs

    return cache


def simulate_half_inning(lineup, prob_cache, start_index):
    outs = 0
    runs = 0
    bases = [0, 0, 0]
    index = start_index

    safety_counter = 0

    while outs < 3:
        safety_counter += 1

        if safety_counter > 25:
            outs = 3
            break

        batter = lineup[index % len(lineup)]
        probs = prob_cache.get(batter, DEFAULT_PROBS)

        outcome = choose_outcome(probs)

        if outcome in ["out", "strikeout"]:
            outs += 1
        else:
            new_runs, bases = advance_runners(outcome, bases)
            runs += new_runs

        index += 1

    return runs, index


def run_model_game_simulation(game, lineups, park, weather, n_sims=1000):
    away_lineup = lineups.get("away_lineup", [])
    home_lineup = lineups.get("home_lineup", [])

    if not away_lineup:
        away_lineup = [
            player["name"] for player in lineups.get("away_fallback_hitters", [])[:9]
        ]

    if not home_lineup:
        home_lineup = [
            player["name"] for player in lineups.get("home_fallback_hitters", [])[:9]
        ]

    if len(away_lineup) < 9 or len(home_lineup) < 9:
        return None

    away_sides = lineups.get("away_sides", [])
    home_sides = lineups.get("home_sides", [])

    if len(away_sides) != len(away_lineup):
        away_sides = estimate_sides(
            away_lineup,
            lineups.get("away_fallback_hitters", [])
        )

    if len(home_sides) != len(home_lineup):
        home_sides = estimate_sides(
            home_lineup,
            lineups.get("home_fallback_hitters", [])
        )

    away_pitcher = game.get("away_pitcher", "TBD")
    home_pitcher = game.get("home_pitcher", "TBD")

    away_pitcher_bio = get_player_bio(game.get("away_pitcher_id"))
    home_pitcher_bio = get_player_bio(game.get("home_pitcher_id"))

    away_pitcher_hand = away_pitcher_bio.get("throw_hand", "R")
    home_pitcher_hand = home_pitcher_bio.get("throw_hand", "R")

    print("Building matchup probability cache...")

    away_prob_cache = build_matchup_prob_cache(
        lineup=away_lineup,
        pitcher=home_pitcher,
        batter_sides=away_sides,
        pitcher_hand=home_pitcher_hand,
        home_team=game["home"],
        park=park,
        weather=weather,
    )

    home_prob_cache = build_matchup_prob_cache(
        lineup=home_lineup,
        pitcher=away_pitcher,
        batter_sides=home_sides,
        pitcher_hand=away_pitcher_hand,
        home_team=game["home"],
        park=park,
        weather=weather,
    )

    print("Running simulations...")

    away_scores = []
    home_scores = []

    home_wins = 0
    away_wins = 0

    for _ in range(n_sims):
        away_score = 0
        home_score = 0

        away_index = 0
        home_index = 0

        for inning in range(9):
            away_runs, away_index = simulate_half_inning(
                lineup=away_lineup,
                prob_cache=away_prob_cache,
                start_index=away_index,
            )

            home_runs, home_index = simulate_half_inning(
                lineup=home_lineup,
                prob_cache=home_prob_cache,
                start_index=home_index,
            )

            away_score += away_runs
            home_score += home_runs

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
        "winner": game["home"] if home_prob > away_prob else game["away"],
        "engine": "Statcast PA model with calibrated cached matchups",
    }
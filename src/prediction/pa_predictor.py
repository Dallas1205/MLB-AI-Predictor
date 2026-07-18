import numpy as np
import pandas as pd

from src.prediction.model_loader import load_pa_model
from src.prediction.player_lookup import get_player_id


OUTCOMES = [
    "out",
    "strikeout",
    "walk",
    "single",
    "double",
    "triple",
    "home_run",
]

FALLBACK_LEAGUE_RATES = {
    "out": 0.460,
    "strikeout": 0.225,
    "walk": 0.085,
    "single": 0.145,
    "double": 0.045,
    "triple": 0.005,
    "home_run": 0.035,
}


def normalize_player_id(value):
    if value is None:
        return "unknown"

    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def safe_hand(value, default="R"):
    value = str(value or default).strip().upper()

    if value not in {"L", "R", "S"}:
        return default

    return value


def determine_platoon(batter_side, pitcher_hand):
    if batter_side == "S":
        return "switch"

    if batter_side == pitcher_hand:
        return "same"

    return "opposite"


def get_player_stats(
    player_id,
    stats_dictionary,
):
    return stats_dictionary.get(
        normalize_player_id(player_id),
        {},
    )


def build_prediction_row(
    batter_id,
    pitcher_id,
    batter_side,
    pitcher_hand,
    home_team,
    metadata,
    balls=0,
    strikes=0,
    outs_when_up=0,
    runner_on_first=0,
    runner_on_second=0,
    runner_on_third=0,
):
    league_rates = metadata.get(
        "league_rates",
        FALLBACK_LEAGUE_RATES,
    )

    batter_stats_dictionary = metadata.get(
        "batter_stats",
        {},
    )

    pitcher_stats_dictionary = metadata.get(
        "pitcher_stats",
        {},
    )

    batter_key = normalize_player_id(batter_id)
    pitcher_key = normalize_player_id(pitcher_id)

    batter_stats = get_player_stats(
        batter_key,
        batter_stats_dictionary,
    )

    pitcher_stats = get_player_stats(
        pitcher_key,
        pitcher_stats_dictionary,
    )

    batter_side = safe_hand(
        batter_side,
        default="R",
    )

    pitcher_hand = safe_hand(
        pitcher_hand,
        default="R",
    )

    row = {
        "batter_id": batter_key,
        "pitcher_id": pitcher_key,
        "stand": batter_side,
        "p_throws": pitcher_hand,
        "home_team": str(
            home_team or "UNK"
        ).strip().upper(),
        "platoon": determine_platoon(
            batter_side,
            pitcher_hand,
        ),
        "balls": float(
            max(0, min(int(balls), 3))
        ),
        "strikes": float(
            max(0, min(int(strikes), 2))
        ),
        "outs_when_up": float(
            max(0, min(int(outs_when_up), 2))
        ),
        "runner_on_first": float(
            1 if runner_on_first else 0
        ),
        "runner_on_second": float(
            1 if runner_on_second else 0
        ),
        "runner_on_third": float(
            1 if runner_on_third else 0
        ),
        "batter_pa": float(
            batter_stats.get("pa", 0.0)
        ),
        "pitcher_pa": float(
            pitcher_stats.get("pa", 0.0)
        ),
    }

    for outcome in OUTCOMES:
        league_rate = float(
            league_rates.get(
                outcome,
                FALLBACK_LEAGUE_RATES[outcome],
            )
        )

        row[f"batter_{outcome}_rate"] = float(
            batter_stats.get(
                f"{outcome}_rate",
                league_rate,
            )
        )

        row[f"pitcher_{outcome}_rate"] = float(
            pitcher_stats.get(
                f"{outcome}_rate",
                league_rate,
            )
        )

    return row


def normalize_probability_output(probabilities):
    cleaned = {
        outcome: max(
            0.0,
            float(probabilities.get(outcome, 0.0)),
        )
        for outcome in OUTCOMES
    }

    total = sum(cleaned.values())

    if total <= 0:
        return FALLBACK_LEAGUE_RATES.copy()

    return {
        outcome: probability / total
        for outcome, probability in cleaned.items()
    }


def predict_plate_appearance(
    batter_name,
    pitcher_name,
    batter_side,
    pitcher_hand,
    home_team,
    balls=0,
    strikes=0,
    outs_when_up=0,
    runner_on_first=0,
    runner_on_second=0,
    runner_on_third=0,
):
    model, metadata, status = load_pa_model()

    if status != "loaded":
        return None

    if not isinstance(metadata, dict):
        return None

    model_version = metadata.get(
        "model_version",
        "",
    )

    # The updated predictor requires the v2 artifact metadata.
    if not model_version.startswith("pa_v2"):
        return None

    batter_id = get_player_id(batter_name)
    pitcher_id = get_player_id(pitcher_name)

    if batter_id is None:
        batter_id = "unknown"

    if pitcher_id is None:
        pitcher_id = "unknown"

    row = build_prediction_row(
        batter_id=batter_id,
        pitcher_id=pitcher_id,
        batter_side=batter_side,
        pitcher_hand=pitcher_hand,
        home_team=home_team,
        metadata=metadata,
        balls=balls,
        strikes=strikes,
        outs_when_up=outs_when_up,
        runner_on_first=runner_on_first,
        runner_on_second=runner_on_second,
        runner_on_third=runner_on_third,
    )

    feature_columns = metadata.get(
        "all_features"
    )

    if not feature_columns:
        return None

    X = pd.DataFrame(
        [row],
        columns=feature_columns,
    )

    try:
        raw_probabilities = model.predict_proba(X)[0]
    except Exception:
        return None

    classes = list(
        getattr(
            model,
            "classes_",
            metadata.get("classes", []),
        )
    )

    probability_map = {
        str(class_name): float(probability)
        for class_name, probability in zip(
            classes,
            raw_probabilities,
        )
    }

    return normalize_probability_output(
        probability_map
    )
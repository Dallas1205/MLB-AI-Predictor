import pandas as pd

from src.prediction.model_loader import load_pa_model
from src.prediction.player_lookup import get_player_id


def predict_plate_appearance(
    batter_name,
    pitcher_name,
    batter_side,
    pitcher_hand,
    home_team,
    balls=0,
    strikes=0
):
    model, columns, status = load_pa_model()

    if status != "loaded":
        return None

    batter_id = get_player_id(batter_name)
    pitcher_id = get_player_id(pitcher_name)

    if batter_id is None or pitcher_id is None:
        return None

    row = {
        "batter": batter_id,
        "pitcher": pitcher_id,
        "stand": batter_side,
        "p_throws": pitcher_hand,
        "balls": balls,
        "strikes": strikes,
        "home_team": home_team,
    }

    X = pd.DataFrame([row])
    X = pd.get_dummies(X)
    X = X.reindex(columns=columns, fill_value=0)

    probs = model.predict_proba(X)[0]

    return dict(zip(model.classes_, probs))
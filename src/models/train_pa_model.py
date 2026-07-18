from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from pybaseball import statcast

from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


MODEL_PATH = Path("models/pa_model.pkl")
METADATA_PATH = Path("models/pa_metadata.pkl")

OUTCOMES = [
    "out",
    "strikeout",
    "walk",
    "single",
    "double",
    "triple",
    "home_run",
]

CATEGORICAL_FEATURES = [
    "batter_id",
    "pitcher_id",
    "stand",
    "p_throws",
    "home_team",
    "platoon",
]

NUMERIC_FEATURES = [
    "balls",
    "strikes",
    "outs_when_up",
    "runner_on_first",
    "runner_on_second",
    "runner_on_third",
    "batter_pa",
    "pitcher_pa",
]

for outcome in OUTCOMES:
    NUMERIC_FEATURES.append(f"batter_{outcome}_rate")
    NUMERIC_FEATURES.append(f"pitcher_{outcome}_rate")

ALL_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES


def simplify_event(event):
    """
    Convert Statcast events into the seven outcomes used by the simulator.
    """

    event = str(event).strip().lower()

    if event == "strikeout":
        return "strikeout"

    if event in {
        "walk",
        "intent_walk",
        "hit_by_pitch",
        "catcher_interf",
    }:
        return "walk"

    if event in {
        "single",
        "field_error",
    }:
        return "single"

    if event == "double":
        return "double"

    if event == "triple":
        return "triple"

    if event == "home_run":
        return "home_run"

    return "out"


def normalize_player_id(value):
    """
    Player IDs must be categorical strings, not numeric measurements.
    """

    if pd.isna(value):
        return "unknown"

    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value).strip()


def safe_binary_runner(value):
    return 0 if pd.isna(value) else 1


def add_basic_features(df):
    """
    Create features that are available both during training and prediction.
    """

    result = df.copy()

    result["batter_id"] = result["batter"].apply(normalize_player_id)
    result["pitcher_id"] = result["pitcher"].apply(normalize_player_id)

    result["stand"] = (
        result["stand"]
        .fillna("R")
        .astype(str)
        .str.upper()
    )

    result["p_throws"] = (
        result["p_throws"]
        .fillna("R")
        .astype(str)
        .str.upper()
    )

    result["home_team"] = (
        result["home_team"]
        .fillna("UNK")
        .astype(str)
        .str.upper()
    )

    result["platoon"] = np.where(
        result["stand"] == "S",
        "switch",
        np.where(
            result["stand"] == result["p_throws"],
            "same",
            "opposite",
        ),
    )

    result["balls"] = (
        pd.to_numeric(result["balls"], errors="coerce")
        .fillna(0)
        .clip(0, 3)
        .astype(float)
    )

    result["strikes"] = (
        pd.to_numeric(result["strikes"], errors="coerce")
        .fillna(0)
        .clip(0, 2)
        .astype(float)
    )

    result["outs_when_up"] = (
        pd.to_numeric(
            result.get("outs_when_up", 0),
            errors="coerce",
        )
        .fillna(0)
        .clip(0, 2)
        .astype(float)
    )

    if "on_1b" in result.columns:
        result["runner_on_first"] = result["on_1b"].apply(
            safe_binary_runner
        )
    else:
        result["runner_on_first"] = 0

    if "on_2b" in result.columns:
        result["runner_on_second"] = result["on_2b"].apply(
            safe_binary_runner
        )
    else:
        result["runner_on_second"] = 0

    if "on_3b" in result.columns:
        result["runner_on_third"] = result["on_3b"].apply(
            safe_binary_runner
        )
    else:
        result["runner_on_third"] = 0

    return result


def calculate_league_rates(df):
    counts = df["outcome"].value_counts()
    total = max(len(df), 1)

    return {
        outcome: float(counts.get(outcome, 0) / total)
        for outcome in OUTCOMES
    }


def build_player_rate_table(
    df,
    player_column,
    league_rates,
    prior_strength,
):
    """
    Build smoothed player event rates.

    Smoothing prevents players with very small samples from receiving
    extreme rates.
    """

    grouped = df.groupby(player_column, observed=True)
    pa_counts = grouped.size().rename("pa")

    event_counts = pd.crosstab(
        df[player_column],
        df["outcome"],
    )

    event_counts = event_counts.reindex(
        columns=OUTCOMES,
        fill_value=0,
    )

    stats = pd.DataFrame(index=pa_counts.index)
    stats["pa"] = pa_counts.astype(float)

    for outcome in OUTCOMES:
        prior_events = prior_strength * league_rates[outcome]

        stats[f"{outcome}_rate"] = (
            event_counts[outcome].astype(float)
            + prior_events
        ) / (
            stats["pa"]
            + prior_strength
        )

    return stats


def apply_player_rate_features(
    df,
    batter_stats,
    pitcher_stats,
    league_rates,
):
    result = df.copy()

    batter_lookup = batter_stats.to_dict(orient="index")
    pitcher_lookup = pitcher_stats.to_dict(orient="index")

    result["batter_pa"] = result["batter_id"].map(
        lambda player_id: float(
            batter_lookup.get(player_id, {}).get("pa", 0.0)
        )
    )

    result["pitcher_pa"] = result["pitcher_id"].map(
        lambda player_id: float(
            pitcher_lookup.get(player_id, {}).get("pa", 0.0)
        )
    )

    for outcome in OUTCOMES:
        result[f"batter_{outcome}_rate"] = result["batter_id"].map(
            lambda player_id, event=outcome: float(
                batter_lookup.get(player_id, {}).get(
                    f"{event}_rate",
                    league_rates[event],
                )
            )
        )

        result[f"pitcher_{outcome}_rate"] = result["pitcher_id"].map(
            lambda player_id, event=outcome: float(
                pitcher_lookup.get(player_id, {}).get(
                    f"{event}_rate",
                    league_rates[event],
                )
            )
        )

    return result


def multiclass_brier_score(y_true, probabilities, classes):
    class_to_index = {
        class_name: index
        for index, class_name in enumerate(classes)
    }

    actual = np.zeros_like(probabilities, dtype=float)

    for row_index, label in enumerate(y_true):
        class_index = class_to_index.get(label)

        if class_index is not None:
            actual[row_index, class_index] = 1.0

    return float(
        np.mean(
            np.sum(
                (probabilities - actual) ** 2,
                axis=1,
            )
        )
    )


def prepare_statcast_data(start_date, end_date):
    print("Downloading Statcast data...")
    df = statcast(start_date, end_date)

    if df is None or df.empty:
        raise RuntimeError(
            "Statcast returned no data for the selected date range."
        )

    print("Cleaning Statcast data...")

    required_columns = [
        "events",
        "batter",
        "pitcher",
        "stand",
        "p_throws",
        "balls",
        "strikes",
        "home_team",
        "game_date",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise RuntimeError(
            f"Statcast data is missing required columns: {missing}"
        )

    df = df.dropna(
        subset=[
            "events",
            "batter",
            "pitcher",
            "game_date",
        ]
    ).copy()

    df["outcome"] = df["events"].apply(simplify_event)
    df["game_date"] = pd.to_datetime(
        df["game_date"],
        errors="coerce",
    )

    df = df.dropna(subset=["game_date"])

    df = add_basic_features(df)

    return df.sort_values(
        ["game_date"],
        kind="stable",
    ).reset_index(drop=True)


def make_pipeline():
    categorical_transformer = OneHotEncoder(
        handle_unknown="ignore",
        min_frequency=10,
        sparse_output=True,
        dtype=np.float32,
    )

    numeric_transformer = StandardScaler(
        with_mean=False
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "categorical",
                categorical_transformer,
                CATEGORICAL_FEATURES,
            ),
            (
                "numeric",
                numeric_transformer,
                NUMERIC_FEATURES,
            ),
        ],
        remainder="drop",
        sparse_threshold=1.0,
    )

    classifier = LogisticRegression(
        solver="saga",
        penalty="l2",
        C=0.60,
        max_iter=400,
        tol=1e-4,
        n_jobs=-1,
        random_state=42,
    )

    return Pipeline(
        steps=[
            ("preprocessing", preprocessing),
            ("classifier", classifier),
        ]
    )


def train_pa_model(
    start_date="2024-03-20",
    end_date="2024-10-01",
):
    df = prepare_statcast_data(
        start_date,
        end_date,
    )

    if len(df) < 10000:
        raise RuntimeError(
            "Not enough plate appearances were returned. "
            "Use a larger training date range."
        )

    split_index = int(len(df) * 0.80)

    train_df = df.iloc[:split_index].copy()
    validation_df = df.iloc[split_index:].copy()

    print(
        f"Training rows: {len(train_df):,}"
    )
    print(
        f"Validation rows: {len(validation_df):,}"
    )

    train_league_rates = calculate_league_rates(train_df)

    train_batter_stats = build_player_rate_table(
        train_df,
        player_column="batter_id",
        league_rates=train_league_rates,
        prior_strength=200.0,
    )

    train_pitcher_stats = build_player_rate_table(
        train_df,
        player_column="pitcher_id",
        league_rates=train_league_rates,
        prior_strength=300.0,
    )

    train_features = apply_player_rate_features(
        train_df,
        batter_stats=train_batter_stats,
        pitcher_stats=train_pitcher_stats,
        league_rates=train_league_rates,
    )

    validation_features = apply_player_rate_features(
        validation_df,
        batter_stats=train_batter_stats,
        pitcher_stats=train_pitcher_stats,
        league_rates=train_league_rates,
    )

    X_train = train_features[ALL_FEATURES]
    y_train = train_features["outcome"]

    X_validation = validation_features[ALL_FEATURES]
    y_validation = validation_features["outcome"]

    model = make_pipeline()

    print("Training PA model v2...")
    model.fit(X_train, y_train)

    predictions = model.predict(X_validation)
    probabilities = model.predict_proba(X_validation)
    classes = list(model.classes_)

    accuracy = accuracy_score(
        y_validation,
        predictions,
    )

    validation_log_loss = log_loss(
        y_validation,
        probabilities,
        labels=classes,
    )

    brier = multiclass_brier_score(
        y_validation.to_numpy(),
        probabilities,
        classes,
    )

    print()
    print("Chronological validation results")
    print("--------------------------------")
    print(f"Accuracy: {accuracy:.4f}")
    print(f"Log loss: {validation_log_loss:.4f}")
    print(f"Multiclass Brier score: {brier:.4f}")

    print()
    print("Fitting final model on all selected data...")

    full_league_rates = calculate_league_rates(df)

    full_batter_stats = build_player_rate_table(
        df,
        player_column="batter_id",
        league_rates=full_league_rates,
        prior_strength=200.0,
    )

    full_pitcher_stats = build_player_rate_table(
        df,
        player_column="pitcher_id",
        league_rates=full_league_rates,
        prior_strength=300.0,
    )

    full_features = apply_player_rate_features(
        df,
        batter_stats=full_batter_stats,
        pitcher_stats=full_pitcher_stats,
        league_rates=full_league_rates,
    )

    final_model = make_pipeline()
    final_model.fit(
        full_features[ALL_FEATURES],
        full_features["outcome"],
    )

    batter_stats_dict = {
        str(player_id): {
            key: float(value)
            for key, value in row.items()
        }
        for player_id, row in full_batter_stats.to_dict(
            orient="index"
        ).items()
    }

    pitcher_stats_dict = {
        str(player_id): {
            key: float(value)
            for key, value in row.items()
        }
        for player_id, row in full_pitcher_stats.to_dict(
            orient="index"
        ).items()
    }

    metadata = {
        "model_version": "pa_v2_categorical_rates_logistic",
        "trained_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "training_start_date": start_date,
        "training_end_date": end_date,
        "training_rows": int(len(df)),
        "classes": list(final_model.classes_),
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "all_features": ALL_FEATURES,
        "league_rates": full_league_rates,
        "batter_stats": batter_stats_dict,
        "pitcher_stats": pitcher_stats_dict,
        "validation": {
            "accuracy": float(accuracy),
            "log_loss": float(validation_log_loss),
            "multiclass_brier": float(brier),
            "validation_rows": int(len(validation_df)),
        },
    }

    artifact = {
        "model": final_model,
        "metadata": metadata,
    }

    MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        artifact,
        MODEL_PATH,
        compress=3,
    )

    joblib.dump(
        metadata,
        METADATA_PATH,
        compress=3,
    )

    print()
    print(f"Saved model: {MODEL_PATH}")
    print(f"Saved metadata: {METADATA_PATH}")
    print(
        "Model version: "
        f"{metadata['model_version']}"
    )


if __name__ == "__main__":
    train_pa_model()
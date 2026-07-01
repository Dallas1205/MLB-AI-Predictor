from pathlib import Path
import joblib
import pandas as pd
from pybaseball import statcast
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, log_loss


MODEL_PATH = Path("models/pa_model.pkl")
COLUMNS_PATH = Path("models/pa_columns.pkl")


def simplify_event(event):
    if event == "strikeout":
        return "strikeout"
    if event == "walk":
        return "walk"
    if event == "single":
        return "single"
    if event == "double":
        return "double"
    if event == "triple":
        return "triple"
    if event == "home_run":
        return "home_run"
    return "out"


def train_pa_model(start_date="2024-03-20", end_date="2024-10-01"):
    print("Downloading Statcast data...")
    df = statcast(start_date, end_date)

    print("Cleaning data...")
    df = df.dropna(subset=["events"]).copy()
    df["outcome"] = df["events"].apply(simplify_event)

    features = [
        "batter",
        "pitcher",
        "stand",
        "p_throws",
        "balls",
        "strikes",
        "home_team"
    ]

    df = df[features + ["outcome"]].dropna()

    X = pd.get_dummies(df[features])
    y = df["outcome"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=16,
        min_samples_leaf=8,
        random_state=42,
        class_weight="balanced",
        n_jobs=-1
    )

    print("Training model...")
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    probs = model.predict_proba(X_test)

    acc = accuracy_score(y_test, preds)
    loss = log_loss(y_test, probs, labels=model.classes_)

    print(f"Accuracy: {acc:.3f}")
    print(f"Log loss: {loss:.3f}")

    Path("models").mkdir(exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(list(X.columns), COLUMNS_PATH)

    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved columns to {COLUMNS_PATH}")


if __name__ == "__main__":
    train_pa_model()
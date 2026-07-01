from pathlib import Path
import joblib


MODEL_PATH = Path("models/pa_model.pkl")
COLUMNS_PATH = Path("models/pa_columns.pkl")


def load_pa_model():
    if not MODEL_PATH.exists():
        return None, None, "Model not trained yet"

    if not COLUMNS_PATH.exists():
        return None, None, "Model columns not found"

    model = joblib.load(MODEL_PATH)
    columns = joblib.load(COLUMNS_PATH)

    return model, columns, "loaded"
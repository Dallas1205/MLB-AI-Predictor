from pathlib import Path

import joblib


MODEL_PATH = Path("models/pa_model.pkl")

_MODEL_CACHE = None
_MODEL_MODIFIED_TIME = None


def clear_model_cache():
    global _MODEL_CACHE
    global _MODEL_MODIFIED_TIME

    _MODEL_CACHE = None
    _MODEL_MODIFIED_TIME = None


def load_pa_model():
    """
    Load and cache the PA model.

    Returns:
        model
        metadata
        status
    """

    global _MODEL_CACHE
    global _MODEL_MODIFIED_TIME

    if not MODEL_PATH.exists():
        return None, None, "Model not trained yet"

    try:
        modified_time = MODEL_PATH.stat().st_mtime

        if (
            _MODEL_CACHE is not None
            and _MODEL_MODIFIED_TIME == modified_time
        ):
            return (
                _MODEL_CACHE["model"],
                _MODEL_CACHE["metadata"],
                "loaded",
            )

        loaded = joblib.load(MODEL_PATH)

        if isinstance(loaded, dict) and "model" in loaded:
            artifact = loaded

            metadata = artifact.get(
                "metadata",
                {},
            )

        else:
            # Compatibility with the old champion model format.
            artifact = {
                "model": loaded,
                "metadata": {
                    "model_version": "legacy_pa_model",
                    "classes": list(
                        getattr(loaded, "classes_", [])
                    ),
                },
            }

        _MODEL_CACHE = artifact
        _MODEL_MODIFIED_TIME = modified_time

        return (
            artifact["model"],
            artifact.get("metadata", {}),
            "loaded",
        )

    except Exception as error:
        clear_model_cache()

        return (
            None,
            None,
            f"Could not load model: {error}",
        )


def get_model_version():
    _, metadata, status = load_pa_model()

    if status != "loaded":
        return "not loaded"

    return metadata.get(
        "model_version",
        "unknown",
    )
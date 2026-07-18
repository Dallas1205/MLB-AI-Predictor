from difflib import get_close_matches
from pathlib import Path
import re
import unicodedata

import pandas as pd
from pybaseball import chadwick_register


CACHE_PATH = Path("data/cache/player_lookup.csv")

_PLAYER_CACHE = None
_NAME_TO_ID = None


def normalize_name(name):
    if not name:
        return ""

    text = unicodedata.normalize(
        "NFKD",
        str(name),
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace("'", "")

    text = re.sub(
        r"\b(jr|sr|ii|iii|iv)\b",
        "",
        text,
    )

    text = re.sub(
        r"[^a-z0-9 ]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    return text


def build_player_cache():
    print(
        "Building player lookup cache. "
        "This may take a minute on the first run..."
    )

    players = chadwick_register()

    required_columns = [
        "key_mlbam",
        "name_first",
        "name_last",
    ]

    missing = [
        column
        for column in required_columns
        if column not in players.columns
    ]

    if missing:
        raise RuntimeError(
            f"Player register is missing columns: {missing}"
        )

    players = players.dropna(
        subset=required_columns
    ).copy()

    players["key_mlbam"] = pd.to_numeric(
        players["key_mlbam"],
        errors="coerce",
    )

    players = players.dropna(
        subset=["key_mlbam"]
    )

    players["key_mlbam"] = (
        players["key_mlbam"]
        .astype(int)
    )

    players["full_name"] = (
        players["name_first"].astype(str).str.strip()
        + " "
        + players["name_last"].astype(str).str.strip()
    )

    players["normalized_name"] = players[
        "full_name"
    ].apply(normalize_name)

    players = players[
        [
            "key_mlbam",
            "full_name",
            "normalized_name",
        ]
    ]

    players = players.drop_duplicates(
        subset=[
            "key_mlbam",
            "normalized_name",
        ]
    )

    CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    players.to_csv(
        CACHE_PATH,
        index=False,
    )

    return players


def load_player_cache(force_refresh=False):
    global _PLAYER_CACHE
    global _NAME_TO_ID

    if (
        _PLAYER_CACHE is not None
        and not force_refresh
    ):
        return _PLAYER_CACHE

    if CACHE_PATH.exists() and not force_refresh:
        try:
            players = pd.read_csv(CACHE_PATH)

            required = {
                "key_mlbam",
                "full_name",
                "normalized_name",
            }

            if required.issubset(players.columns):
                players["key_mlbam"] = pd.to_numeric(
                    players["key_mlbam"],
                    errors="coerce",
                )

                players = players.dropna(
                    subset=["key_mlbam"]
                )

                players["key_mlbam"] = (
                    players["key_mlbam"].astype(int)
                )

                _PLAYER_CACHE = players

            else:
                _PLAYER_CACHE = build_player_cache()

        except Exception:
            _PLAYER_CACHE = build_player_cache()

    else:
        _PLAYER_CACHE = build_player_cache()

    _NAME_TO_ID = {}

    for row in _PLAYER_CACHE.itertuples():
        normalized = str(row.normalized_name)

        # Later Chadwick rows usually represent the most recent player
        # record when duplicate names exist.
        _NAME_TO_ID[normalized] = int(row.key_mlbam)

    return _PLAYER_CACHE


def get_player_id(full_name):
    global _NAME_TO_ID

    players = load_player_cache()
    clean_name = normalize_name(full_name)

    if not clean_name:
        return None

    exact = _NAME_TO_ID.get(clean_name)

    if exact is not None:
        return exact

    # Handle names entered as "Last, First".
    if "," in str(full_name):
        pieces = [
            piece.strip()
            for piece in str(full_name).split(",")
        ]

        if len(pieces) == 2:
            reversed_name = normalize_name(
                f"{pieces[1]} {pieces[0]}"
            )

            exact = _NAME_TO_ID.get(reversed_name)

            if exact is not None:
                return exact

    # Conservative fuzzy fallback for punctuation or minor spelling issues.
    possible_names = list(_NAME_TO_ID.keys())

    matches = get_close_matches(
        clean_name,
        possible_names,
        n=1,
        cutoff=0.94,
    )

    if matches:
        return _NAME_TO_ID[matches[0]]

    return None


def refresh_player_cache():
    return load_player_cache(
        force_refresh=True
    )
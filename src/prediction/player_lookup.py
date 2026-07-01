from pybaseball import chadwick_register


_PLAYER_CACHE = None


def load_player_cache():
    global _PLAYER_CACHE

    if _PLAYER_CACHE is not None:
        return _PLAYER_CACHE

    players = chadwick_register()

    players = players.dropna(subset=["key_mlbam", "name_first", "name_last"])

    players["full_name"] = (
        players["name_first"].astype(str).str.lower().str.strip()
        + " "
        + players["name_last"].astype(str).str.lower().str.strip()
    )

    _PLAYER_CACHE = players

    return _PLAYER_CACHE


def get_player_id(full_name):
    players = load_player_cache()

    clean_name = full_name.lower().strip()

    matches = players[players["full_name"] == clean_name]

    if matches.empty:
        return None

    return int(matches.iloc[-1]["key_mlbam"])
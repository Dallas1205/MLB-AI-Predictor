import streamlit as st

from src.api.schedule import get_todays_games
from src.api.lineups import get_game_lineups
from src.api.injuries import get_team_roster_status
from src.api.weather import get_weather_for_game
from src.api.park_factors import get_park_factor
from src.reports.data_quality import calculate_data_quality_score
from src.simulation.game import run_basic_game_simulation
from src.simulation.model_game import run_model_game_simulation


st.set_page_config(
    page_title="MLB AI Predictor",
    page_icon="⚾",
    layout="wide"
)

st.title("⚾ MLB AI Predictor")

page = st.sidebar.radio(
    "Menu",
    ["Today's Games", "Batter Matchup"]
)


def moneyline(prob):
    prob = max(0.001, min(prob, 0.999))

    if prob >= 0.5:
        return round(-100 * prob / (1 - prob))

    return round(100 * (1 - prob) / prob)


if page == "Today's Games":
    st.header("Today's Games")

    games = get_todays_games()

    if not games:
        st.warning("No games found.")
    else:
        labels = [
            f"{g['away']} @ {g['home']} — {g['status']}"
            for g in games
        ]

        selected = st.selectbox("Select a game", labels)
        game = games[labels.index(selected)]

        st.write(f"**Venue:** {game['venue']}")
        st.write(f"**Pitchers:** {game['away_pitcher']} vs {game['home_pitcher']}")
        st.write(f"**Status:** {game['status']}")

        sims = st.slider("Simulations", 500, 5000, 1000, step=500)

        if st.button("Run Prediction"):
            with st.spinner("Downloading data and running simulation..."):
                lineups = get_game_lineups(
                    game["game_id"],
                    away_team_id=game["away_id"],
                    home_team_id=game["home_id"]
                )

                away_status = get_team_roster_status(game["away_id"])
                home_status = get_team_roster_status(game["home_id"])

                weather = get_weather_for_game(game)
                park = get_park_factor(game["venue"])

                quality = calculate_data_quality_score(
                    game=game,
                    lineups=lineups,
                    away_status=away_status,
                    home_status=home_status,
                    weather=weather,
                    park=park
                )

                sim = run_model_game_simulation(
                    game=game,
                    lineups=lineups,
                    park=park,
                    weather=weather,
                    n_sims=sims
                )

                if sim is None:
                    sim = run_basic_game_simulation(
                        game=game,
                        lineups=lineups,
                        park=park,
                        weather=weather,
                        n_sims=sims
                    )

            st.subheader("Prediction")

            c1, c2, c3 = st.columns(3)

            c1.metric("Predicted Winner", sim["winner"])
            c2.metric(f"{game['home']} Win %", f"{sim['home_win_probability'] * 100:.1f}%")
            c3.metric(f"{game['away']} Win %", f"{sim['away_win_probability'] * 100:.1f}%")

            st.write(
                f"**Projected Score:** {game['away']} {sim['projected_away_score']} - "
                f"{game['home']} {sim['projected_home_score']}"
            )

            st.write(f"**Projected Total:** {sim['projected_total']}")

            st.subheader("Fair Odds")
            st.write(f"**{game['home']}:** {moneyline(sim['home_win_probability'])}")
            st.write(f"**{game['away']}:** {moneyline(sim['away_win_probability'])}")

            st.subheader("Weather")
            st.write(f"**Temp:** {weather.get('temp_f')}°F")
            st.write(f"**Wind:** {weather.get('wind_mph')} mph {weather.get('wind_direction')}")
            st.write(f"**Humidity:** {weather.get('humidity')}")
            st.write(f"**Source:** {weather.get('source')}")

            st.subheader("Data Quality")
            st.write(f"**Score:** {quality['score']}/100")

            if quality["notes"]:
                for note in quality["notes"]:
                    st.write(f"- {note}")

            st.subheader("Lineups")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**{game['away']}**")
                away_lineup = lineups.get("away_lineup", [])

                if away_lineup:
                    for i, player in enumerate(away_lineup, start=1):
                        st.write(f"{i}. {player}")
                else:
                    st.write("Official lineup not posted.")
                    for player in lineups.get("away_fallback_hitters", [])[:9]:
                        st.write(f"- {player['name']} ({player['position']})")

            with col2:
                st.write(f"**{game['home']}**")
                home_lineup = lineups.get("home_lineup", [])

                if home_lineup:
                    for i, player in enumerate(home_lineup, start=1):
                        st.write(f"{i}. {player}")
                else:
                    st.write("Official lineup not posted.")
                    for player in lineups.get("home_fallback_hitters", [])[:9]:
                        st.write(f"- {player['name']} ({player['position']})")


elif page == "Batter Matchup":
    st.header("Individual Batter Matchup")

    st.info("Basic app page ready. We will connect this after deployment works.")
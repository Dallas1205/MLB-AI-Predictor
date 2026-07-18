from pathlib import Path

from src.api.schedule import (
    get_todays_games,
    get_tomorrows_games,
    get_yesterdays_games,
    get_games,
    get_games_in_range,
)
from src.api.lineups import get_game_lineups
from src.api.injuries import get_team_roster_status
from src.api.weather import get_weather_for_game
from src.api.park_factors import get_park_factor

from src.reports.data_quality import (
    calculate_data_quality_score,
)
from src.reports.game_report import (
    build_game_report,
    save_game_report,
)

from src.simulation.game import (
    run_basic_game_simulation,
)
from src.simulation.model_game import (
    run_model_game_simulation,
)

from src.prediction.model_loader import load_pa_model

from src.ui.progress import progress_bar, step

from src.analytics.team_form import (
    get_recent_team_form,
)
from src.analytics.projection_blend import (
    blend_projection,
)


def print_header():
    print("\n╔════════════════════════════════════════╗")
    print("║            MLB AI Predictor            ║")
    print("╠════════════════════════════════════════╣")
    print("║ 1. Predict All Games                   ║")
    print("║ 2. Predict One Game                    ║")
    print("║ 3. Custom Matchup                      ║")
    print("║ 4. Train Models                        ║")
    print("║ 5. View Saved Results                  ║")
    print("║ 6. Settings                            ║")
    print("║ 7. Exit                                ║")
    print("╚════════════════════════════════════════╝")


def moneyline(probability):
    probability = max(
        0.001,
        min(probability, 0.999),
    )

    if probability >= 0.5:
        return round(
            -100
            * probability
            / (1 - probability)
        )

    return round(
        100
        * (1 - probability)
        / probability
    )


def choose_schedule():
    print("\nChoose Schedule")
    print("----------------")
    print("1. Today's Games")
    print("2. Yesterday's Games")
    print("3. Tomorrow's Games")
    print("4. Single Custom Date")
    print("5. Date Range")

    choice = input("\nSelection: ").strip()

    try:
        if choice == "1":
            return get_todays_games()

        if choice == "2":
            return get_yesterdays_games()

        if choice == "3":
            return get_tomorrows_games()

        if choice == "4":
            selected_date = input(
                "\nEnter date (YYYY-MM-DD): "
            ).strip()

            return get_games(selected_date)

        if choice == "5":
            start_date = input(
                "\nEnter start date (YYYY-MM-DD): "
            ).strip()

            end_date = input(
                "Enter end date (YYYY-MM-DD): "
            ).strip()

            return get_games_in_range(
                start_date,
                end_date,
            )

    except ValueError as error:
        print(f"\nDate error: {error}")
        return []

    except Exception as error:
        print(f"\nCould not load schedule: {error}")
        return []

    print("\nInvalid choice.")
    return []


def run_prediction_for_game(
    game,
    n_sims=1000,
    print_steps=True,
):
    if print_steps:
        print(
            f"\nPredicting: "
            f"{game['away']} @ {game['home']}"
        )

        step("Getting lineups")

    lineups = get_game_lineups(
        game["game_id"],
        away_team_id=game["away_id"],
        home_team_id=game["home_id"],
    )

    if print_steps:
        step("Checking injuries")

    away_status = get_team_roster_status(
        game["away_id"]
    )
    home_status = get_team_roster_status(
        game["home_id"]
    )

    if print_steps:
        step("Getting weather")

    weather = get_weather_for_game(game)

    if print_steps:
        step("Getting park factors")

    park = get_park_factor(game["venue"])

    if print_steps:
        step("Calculating data quality")

    quality = calculate_data_quality_score(
        game=game,
        lineups=lineups,
        away_status=away_status,
        home_status=home_status,
        weather=weather,
        park=park,
    )

    if print_steps:
        step("Loading model")

    model, model_columns, model_status = (
        load_pa_model()
    )

    if print_steps:
        if model_status == "loaded":
            print("✓ PA model loaded")
        else:
            print(
                f"⚠ Model issue: "
                f"{model_status}"
            )

        step("Running simulation")

    simulation = run_model_game_simulation(
        game=game,
        lineups=lineups,
        park=park,
        weather=weather,
        n_sims=n_sims,
    )

    if simulation is None:
        simulation = run_basic_game_simulation(
            game=game,
            lineups=lineups,
            park=park,
            weather=weather,
            n_sims=n_sims,
        )

    if print_steps:
        step("Adding recent team form")

    home_form = get_recent_team_form(
        game["home_id"]
    )
    away_form = get_recent_team_form(
        game["away_id"]
    )

    simulation["home_team_name"] = game["home"]
    simulation["away_team_name"] = game["away"]

    simulation = blend_projection(
        simulation=simulation,
        home_form=home_form,
        away_form=away_form,
    )

    report = build_game_report(
        game=game,
        lineups=lineups,
        away_status=away_status,
        home_status=home_status,
        weather=weather,
        park=park,
        quality=quality,
        simulation=simulation,
    )

    return {
        "game": game,
        "lineups": lineups,
        "weather": weather,
        "park": park,
        "quality": quality,
        "simulation": simulation,
        "report": report,
        "home_form": home_form,
        "away_form": away_form,
    }


def predict_all_games():
    games = choose_schedule()

    if not games:
        print("\nNo games found.")
        input("\nPress Enter to return...")
        return

    print("\nPredicting all selected games...")
    print("--------------------------------")

    results = []
    total_games = len(games)

    for game_number, game in enumerate(
        games,
        start=1,
    ):
        try:
            progress_bar(
                game_number - 1,
                total_games,
                label="Predicting games",
            )

            game_date = game.get(
                "schedule_date",
                "Unknown date",
            )

            print(
                f"\nCurrent: {game_date} | "
                f"{game['away']} @ {game['home']}"
            )

            result = run_prediction_for_game(
                game=game,
                n_sims=1000,
                print_steps=False,
            )

            results.append(result)

            progress_bar(
                game_number,
                total_games,
                label="Predicting games",
            )

        except Exception as error:
            print(
                f"\nError predicting "
                f"{game['away']} @ "
                f"{game['home']}: {error}"
            )

    progress_bar(
        total_games,
        total_games,
        label="Predicting games",
    )

    print("\n")
    print(
        "════════════════════════════════════════"
        "════════════════════════════════════════"
    )
    print("MLB PREDICTIONS")
    print(
        "════════════════════════════════════════"
        "════════════════════════════════════════"
    )
    print()

    for result in results:
        game = result["game"]
        simulation = result["simulation"]
        weather = result["weather"]
        quality = result["quality"]

        away_probability = simulation[
            "away_win_probability"
        ]
        home_probability = simulation[
            "home_win_probability"
        ]

        away_line = moneyline(
            away_probability
        )
        home_line = moneyline(
            home_probability
        )

        print(
            "────────────────────────────────────────"
            "────────────────────────────────────────"
        )

        print(
            f"Date: "
            f"{game.get('schedule_date', 'Unknown')}"
        )
        print(
            f"{game['away']} @ {game['home']}"
        )
        print(
            f"Status: "
            f"{game.get('status', 'Unknown')}"
        )
        print(
            f"Venue: "
            f"{game.get('venue', 'Unknown')}"
        )
        print()

        print(
            f"Predicted Winner: "
            f"{simulation['winner']}"
        )

        print(
            f"{game['away']} Win %: "
            f"{away_probability * 100:.1f}% | "
            f"Fair Line: {away_line}"
        )

        print(
            f"{game['home']} Win %: "
            f"{home_probability * 100:.1f}% | "
            f"Fair Line: {home_line}"
        )

        print()

        print(
            f"Projected Score: "
            f"{game['away']} "
            f"{simulation['projected_away_score']} - "
            f"{game['home']} "
            f"{simulation['projected_home_score']}"
        )

        print(
            f"Projected Total: "
            f"{simulation['projected_total']}"
        )

        print()

        print(
            f"Weather: "
            f"{weather.get('temp_f')}°F, "
            f"wind "
            f"{weather.get('wind_mph')} mph "
            f"{weather.get('wind_direction')}"
        )

        print(
            f"Data Quality: "
            f"{quality['score']}/100"
        )

        print(
            f"Engine: "
            f"{simulation.get(
                'engine',
                'Basic Simulator'
            )}"
        )

        print()

    full_report = build_all_games_report(
        results
    )

    path = save_all_games_report(
        full_report
    )

    print(
        "════════════════════════════════════════"
        "════════════════════════════════════════"
    )
    print(
        f"Saved all-games report: {path}"
    )
    print(
        "════════════════════════════════════════"
        "════════════════════════════════════════"
    )

    input("\nPress Enter to return...")


def build_all_games_report(results):
    text = ""
    text += "MLB PREDICTIONS\n"
    text += "===============\n\n"

    for result in results:
        game = result["game"]
        simulation = result["simulation"]
        weather = result["weather"]
        quality = result["quality"]

        away_probability = simulation[
            "away_win_probability"
        ]
        home_probability = simulation[
            "home_win_probability"
        ]

        text += (
            "--------------------------------------------------\n"
        )

        text += (
            f"Date: "
            f"{game.get('schedule_date', 'Unknown')}\n"
        )

        text += (
            f"{game['away']} @ "
            f"{game['home']}\n"
        )

        text += (
            f"Status: "
            f"{game.get('status', 'Unknown')}\n"
        )

        text += (
            f"Venue: "
            f"{game.get('venue', 'Unknown')}\n\n"
        )

        text += (
            f"Predicted Winner: "
            f"{simulation['winner']}\n"
        )

        text += (
            f"{game['away']} Win %: "
            f"{away_probability * 100:.1f}% | "
            f"Fair Line: "
            f"{moneyline(away_probability)}\n"
        )

        text += (
            f"{game['home']} Win %: "
            f"{home_probability * 100:.1f}% | "
            f"Fair Line: "
            f"{moneyline(home_probability)}\n\n"
        )

        text += (
            f"Projected Score: "
            f"{game['away']} "
            f"{simulation['projected_away_score']} - "
            f"{game['home']} "
            f"{simulation['projected_home_score']}\n"
        )

        text += (
            f"Projected Total: "
            f"{simulation['projected_total']}\n\n"
        )

        text += (
            f"Weather: "
            f"{weather.get('temp_f')}°F, "
            f"wind "
            f"{weather.get('wind_mph')} mph "
            f"{weather.get('wind_direction')}\n"
        )

        text += (
            f"Data Quality: "
            f"{quality['score']}/100\n"
        )

        text += (
            f"Engine: "
            f"{simulation.get(
                'engine',
                'Basic Simulator'
            )}\n\n"
        )

    return text


def save_all_games_report(report):
    from datetime import datetime

    Path("outputs").mkdir(exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    path = (
        Path("outputs")
        / f"all_games_predictions_{timestamp}.txt"
    )

    path.write_text(
        report,
        encoding="utf-8",
    )

    return path


def predict_one_game():
    games = choose_schedule()

    if not games:
        input("\nPress Enter to return...")
        return

    print("\nGames")
    print("-----")

    for game_number, game in enumerate(
        games,
        start=1,
    ):
        print(
            f"{game_number}. "
            f"{game.get('schedule_date', 'Unknown')} | "
            f"{game['away']} @ {game['home']}"
        )

        print(
            f"   Pitchers: "
            f"{game['away_pitcher']} vs "
            f"{game['home_pitcher']}"
        )

        print(
            f"   Stadium: "
            f"{game['venue']}"
        )

        print(
            f"   Status: "
            f"{game['status']}"
        )

        print(
            f"   Game ID: "
            f"{game['game_id']}"
        )

        print()

    choice = input(
        "Select a game number "
        "or press Enter to go back: "
    ).strip()

    if choice == "":
        return

    if not choice.isdigit():
        print("Invalid choice.")
        input("\nPress Enter to return...")
        return

    selected_number = int(choice)

    if not 1 <= selected_number <= len(games):
        print("Invalid choice.")
        input("\nPress Enter to return...")
        return

    game = games[selected_number - 1]

    result = run_prediction_for_game(
        game=game,
        n_sims=1000,
        print_steps=True,
    )

    print(result["report"])

    path = save_game_report(
        game,
        result["report"],
    )

    print(f"\nSaved report: {path}")

    input("\nPress Enter to return to menu...")


def custom_matchup():
    print("\nCustom Matchup")
    print("--------------")
    print(
        "Custom matchup still uses "
        "the basic simulator for now."
    )

    away = input("Away team: ").strip()
    home = input("Home team: ").strip()
    stadium = input(
        "Stadium name: "
    ).strip()

    temp = input(
        "Temperature F: "
    ).strip()

    wind = input(
        "Wind MPH: "
    ).strip()

    direction = input(
        "Wind direction "
        "out/in/cross/none: "
    ).strip().lower()

    game = {
        "away": away,
        "home": home,
        "away_pitcher": "Manual/TBD",
        "home_pitcher": "Manual/TBD",
        "away_pitcher_id": None,
        "home_pitcher_id": None,
        "venue": stadium,
        "game_id": "custom",
        "schedule_date": "custom",
        "game_time": "custom",
        "status": "custom",
    }

    lineups = {
        "away_lineup": [],
        "home_lineup": [],
        "away_sides": [],
        "home_sides": [],
        "away_fallback_hitters": [],
        "home_fallback_hitters": [],
        "status": "manual / not confirmed",
    }

    weather = {
        "temp_f": float(temp or 72),
        "wind_mph": float(wind or 0),
        "wind_direction": (
            direction or "none"
        ),
        "humidity": "unknown",
        "source": "manual",
    }

    park = get_park_factor(stadium)

    quality = calculate_data_quality_score(
        game=game,
        lineups=lineups,
        away_status=[],
        home_status=[],
        weather=weather,
        park=park,
    )

    simulation = run_basic_game_simulation(
        game=game,
        lineups=lineups,
        park=park,
        weather=weather,
        n_sims=10000,
    )

    report = build_game_report(
        game=game,
        lineups=lineups,
        away_status=[],
        home_status=[],
        weather=weather,
        park=park,
        quality=quality,
        simulation=simulation,
    )

    print(report)

    path = save_game_report(
        game,
        report,
    )

    print(f"\nSaved report: {path}")

    input("\nPress Enter to return...")


def view_saved_results():
    files = sorted(
        Path("outputs").glob("*.txt"),
        reverse=True,
    )

    print("\nSaved Reports")
    print("-------------")

    if not files:
        print("No saved reports yet.")
        input("\nPress Enter to return...")
        return

    visible_files = files[:20]

    for file_number, file in enumerate(
        visible_files,
        start=1,
    ):
        print(
            f"{file_number}. {file.name}"
        )

    choice = input(
        "\nOpen report number "
        "or press Enter to return: "
    ).strip()

    if choice == "":
        return

    if choice.isdigit():
        selected_number = int(choice)

        if 1 <= selected_number <= len(
            visible_files
        ):
            selected_file = visible_files[
                selected_number - 1
            ]

            print(
                "\n"
                + selected_file.read_text(
                    encoding="utf-8"
                )
            )

    input("\nPress Enter to return...")


def train_models_menu():
    from src.models.train_pa_model import (
        train_pa_model,
    )

    print("\nTrain Plate Appearance Model")
    print("----------------------------")

    start = input(
        "Start date YYYY-MM-DD, "
        "default 2024-06-01: "
    ).strip()

    end = input(
        "End date YYYY-MM-DD, "
        "default 2024-06-30: "
    ).strip()

    if start == "":
        start = "2024-06-01"

    if end == "":
        end = "2024-06-30"

    train_pa_model(
        start,
        end,
    )

    input("\nPress Enter to return...")


def run_menu():
    while True:
        print_header()

        choice = input(
            "\nSelect option: "
        ).strip()

        if choice == "1":
            predict_all_games()

        elif choice == "2":
            predict_one_game()

        elif choice == "3":
            custom_matchup()

        elif choice == "4":
            train_models_menu()

        elif choice == "5":
            view_saved_results()

        elif choice == "6":
            print("\nSettings coming soon.")
            input("\nPress Enter to return...")

        elif choice == "7":
            print("\nGoodbye.")
            break

        else:
            print("\nInvalid option.")
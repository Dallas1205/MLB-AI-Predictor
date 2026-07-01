from pathlib import Path

from src.api.schedule import get_todays_games
from src.api.lineups import get_game_lineups
from src.api.injuries import get_team_roster_status
from src.api.weather import get_weather_for_game
from src.api.park_factors import get_park_factor

from src.reports.data_quality import calculate_data_quality_score
from src.reports.game_report import build_game_report, save_game_report

from src.simulation.game import run_basic_game_simulation
from src.simulation.model_game import run_model_game_simulation

from src.prediction.model_loader import load_pa_model


def print_header():
    print("\n╔════════════════════════════════════════╗")
    print("║            MLB AI Predictor            ║")
    print("╠════════════════════════════════════════╣")
    print("║ 1. Predict All Today's Games           ║")
    print("║ 2. Predict One Game                    ║")
    print("║ 3. Custom Matchup                      ║")
    print("║ 4. Train Models                        ║")
    print("║ 5. View Saved Results                  ║")
    print("║ 6. Settings                            ║")
    print("║ 7. Exit                                ║")
    print("╚════════════════════════════════════════╝")


def moneyline(prob):
    prob = max(0.001, min(prob, 0.999))

    if prob >= 0.5:
        return round(-100 * prob / (1 - prob))

    return round(100 * (1 - prob) / prob)


def run_prediction_for_game(game, n_sims=1000, print_steps=True):
    if print_steps:
        print(f"\nPredicting: {game['away']} @ {game['home']}")

    lineups = get_game_lineups(
        game["game_id"],
        away_team_id=game["away_id"],
        home_team_id=game["home_id"],
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
        park=park,
    )

    model, model_columns, model_status = load_pa_model()

    if print_steps:
        if model_status == "loaded":
            print("✓ PA model loaded")
        else:
            print(f"⚠ Model issue: {model_status}")

    sim = run_model_game_simulation(
        game=game,
        lineups=lineups,
        park=park,
        weather=weather,
        n_sims=n_sims,
    )

    if sim is None:
        sim = run_basic_game_simulation(
            game=game,
            lineups=lineups,
            park=park,
            weather=weather,
            n_sims=n_sims,
        )

    report = build_game_report(
        game=game,
        lineups=lineups,
        away_status=away_status,
        home_status=home_status,
        weather=weather,
        park=park,
        quality=quality,
        simulation=sim,
    )

    return {
        "game": game,
        "lineups": lineups,
        "weather": weather,
        "park": park,
        "quality": quality,
        "simulation": sim,
        "report": report,
    }


def predict_all_games():
    games = get_todays_games()

    if not games:
        print("\nNo games found.")
        input("\nPress Enter to return...")
        return

    print("\nPredicting all today's games...")
    print("--------------------------------")

    results = []

    for game in games:
        try:
            result = run_prediction_for_game(
                game=game,
                n_sims=1000,
                print_steps=True,
            )
            results.append(result)
        except Exception as e:
            print(f"Error predicting {game['away']} @ {game['home']}: {e}")

    print("\n")
    print("════════════════════════════════════════════════════════════════════════════════════")
    print("TODAY'S MLB PREDICTIONS")
    print("════════════════════════════════════════════════════════════════════════════════════")
    print()

    for result in results:
        game = result["game"]
        sim = result["simulation"]
        weather = result["weather"]
        quality = result["quality"]

        away_prob = sim["away_win_probability"]
        home_prob = sim["home_win_probability"]

        away_line = moneyline(away_prob)
        home_line = moneyline(home_prob)

        print("────────────────────────────────────────────────────────────────────────────────")
        print(f"{game['away']} @ {game['home']}")
        print(f"Status: {game.get('status', 'Unknown')}")
        print(f"Venue: {game.get('venue', 'Unknown')}")
        print()
        print(f"Predicted Winner: {sim['winner']}")
        print(f"{game['away']} Win %: {away_prob * 100:.1f}% | Fair Line: {away_line}")
        print(f"{game['home']} Win %: {home_prob * 100:.1f}% | Fair Line: {home_line}")
        print()
        print(f"Projected Score: {game['away']} {sim['projected_away_score']} - {game['home']} {sim['projected_home_score']}")
        print(f"Projected Total: {sim['projected_total']}")
        print()
        print(f"Weather: {weather.get('temp_f')}°F, wind {weather.get('wind_mph')} mph {weather.get('wind_direction')}")
        print(f"Data Quality: {quality['score']}/100")
        print(f"Engine: {sim.get('engine', 'Basic Simulator')}")
        print()

    full_report = build_all_games_report(results)
    path = save_all_games_report(full_report)

    print("════════════════════════════════════════════════════════════════════════════════════")
    print(f"Saved all-games report: {path}")
    print("════════════════════════════════════════════════════════════════════════════════════")

    input("\nPress Enter to return...")


def build_all_games_report(results):
    text = ""
    text += "TODAY'S MLB PREDICTIONS\n"
    text += "=======================\n\n"

    for result in results:
        game = result["game"]
        sim = result["simulation"]
        weather = result["weather"]
        quality = result["quality"]

        away_prob = sim["away_win_probability"]
        home_prob = sim["home_win_probability"]

        text += "--------------------------------------------------\n"
        text += f"{game['away']} @ {game['home']}\n"
        text += f"Status: {game.get('status', 'Unknown')}\n"
        text += f"Venue: {game.get('venue', 'Unknown')}\n\n"

        text += f"Predicted Winner: {sim['winner']}\n"
        text += f"{game['away']} Win %: {away_prob * 100:.1f}% | Fair Line: {moneyline(away_prob)}\n"
        text += f"{game['home']} Win %: {home_prob * 100:.1f}% | Fair Line: {moneyline(home_prob)}\n\n"

        text += f"Projected Score: {game['away']} {sim['projected_away_score']} - {game['home']} {sim['projected_home_score']}\n"
        text += f"Projected Total: {sim['projected_total']}\n\n"

        text += f"Weather: {weather.get('temp_f')}°F, wind {weather.get('wind_mph')} mph {weather.get('wind_direction')}\n"
        text += f"Data Quality: {quality['score']}/100\n"
        text += f"Engine: {sim.get('engine', 'Basic Simulator')}\n\n"

    return text


def save_all_games_report(report):
    from datetime import datetime

    Path("outputs").mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path("outputs") / f"all_games_predictions_{timestamp}.txt"

    path.write_text(report, encoding="utf-8")

    return path


def show_todays_games():
    games = get_todays_games()

    print("\nToday's MLB Games")
    print("------------------")

    if not games:
        print("No games found.")
        return []

    for i, game in enumerate(games, start=1):
        print(f"{i}. {game['away']} @ {game['home']}")
        print(f"   Pitchers: {game['away_pitcher']} vs {game['home_pitcher']}")
        print(f"   Stadium: {game['venue']}")
        print(f"   Status: {game['status']}")
        print(f"   Game ID: {game['game_id']}")
        print()

    return games


def predict_one_game():
    games = show_todays_games()

    if not games:
        input("\nPress Enter to return...")
        return

    choice = input("Select a game number or press Enter to go back: ")

    if choice == "":
        return

    if not choice.isdigit() or not (1 <= int(choice) <= len(games)):
        print("Invalid choice.")
        input("\nPress Enter to return...")
        return

    game = games[int(choice) - 1]

    result = run_prediction_for_game(
        game=game,
        n_sims=1000,
        print_steps=True,
    )

    print(result["report"])

    path = save_game_report(game, result["report"])
    print(f"\nSaved report: {path}")

    input("\nPress Enter to return to menu...")


def custom_matchup():
    print("\nCustom Matchup")
    print("--------------")
    print("Custom matchup still uses the basic simulator for now.")

    away = input("Away team: ").strip()
    home = input("Home team: ").strip()
    stadium = input("Stadium name: ").strip()
    temp = input("Temperature F: ").strip()
    wind = input("Wind MPH: ").strip()
    direction = input("Wind direction out/in/cross/none: ").strip().lower()

    game = {
        "away": away,
        "home": home,
        "away_pitcher": "Manual/TBD",
        "home_pitcher": "Manual/TBD",
        "away_pitcher_id": None,
        "home_pitcher_id": None,
        "venue": stadium,
        "game_id": "custom",
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
        "wind_direction": direction or "none",
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

    sim = run_basic_game_simulation(
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
        simulation=sim,
    )

    print(report)

    path = save_game_report(game, report)
    print(f"\nSaved report: {path}")

    input("\nPress Enter to return...")


def view_saved_results():
    files = sorted(Path("outputs").glob("*.txt"), reverse=True)

    print("\nSaved Reports")
    print("-------------")

    if not files:
        print("No saved reports yet.")
        input("\nPress Enter to return...")
        return

    for i, file in enumerate(files[:20], start=1):
        print(f"{i}. {file.name}")

    choice = input("\nOpen report number or press Enter to return: ")

    if choice == "":
        return

    if choice.isdigit() and 1 <= int(choice) <= len(files[:20]):
        selected = files[int(choice) - 1]
        print("\n" + selected.read_text(encoding="utf-8"))

    input("\nPress Enter to return...")


def train_models_menu():
    from src.models.train_pa_model import train_pa_model

    print("\nTrain Plate Appearance Model")
    print("----------------------------")
    start = input("Start date YYYY-MM-DD, default 2024-06-01: ").strip()
    end = input("End date YYYY-MM-DD, default 2024-06-30: ").strip()

    if start == "":
        start = "2024-06-01"

    if end == "":
        end = "2024-06-30"

    train_pa_model(start, end)

    input("\nPress Enter to return...")


def run_menu():
    while True:
        print_header()

        choice = input("\nSelect option: ").strip()

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
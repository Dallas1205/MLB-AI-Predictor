from pathlib import Path
from datetime import datetime

from src.api.injuries import get_injury_notes
from src.reports.betting import build_betting_summary
from src.reports.confidence import build_confidence_summary
from src.reports.explanation import build_model_explanation


def format_lineup(team_name, lineup, fallback=None):
    text = f"\n{team_name} Lineup\n"

    if lineup:
        for i, player in enumerate(lineup, start=1):
            text += f"{i}. {player}\n"
        return text

    text += "Official lineup not posted yet.\n"

    if fallback:
        text += "\nActive roster hitters fallback:\n"
        for i, player in enumerate(fallback[:13], start=1):
            text += f"{i}. {player['name']} - {player['position']} - Bats {player.get('bat_side', 'R')}\n"

    return text


def build_game_report(game, lineups, away_status, home_status, weather, park, quality, simulation):
    away_injuries = get_injury_notes(away_status)
    home_injuries = get_injury_notes(home_status)

    report = "\n"
    report += "════════════════════════════════════════\n"
    report += "MLB AI Predictor Report\n"
    report += "════════════════════════════════════════\n\n"

    report += "Game\n"
    report += "-------------------------\n"
    report += f"{game['away']} @ {game['home']}\n"
    report += f"Game Time: {game.get('game_time', 'Unknown')}\n"
    report += f"Venue: {game.get('venue', 'Unknown')}\n"
    report += f"Status: {game.get('status', 'Unknown')}\n\n"

    report += "Pitchers\n"
    report += "-------------------------\n"
    report += f"Away: {game.get('away_pitcher', 'TBD')}\n"
    report += f"Home: {game.get('home_pitcher', 'TBD')}\n\n"

    report += "Prediction\n"
    report += "-------------------------\n"
    report += f"Winner: {simulation['winner']}\n"
    report += f"Away Win Probability: {simulation['away_win_probability'] * 100:.1f}%\n"
    report += f"Home Win Probability: {simulation['home_win_probability'] * 100:.1f}%\n"
    report += f"Projected Score: {game['away']} {simulation['projected_away_score']} - {game['home']} {simulation['projected_home_score']}\n"
    report += f"Projected Total: {simulation['projected_total']}\n"
    report += f"Prediction Engine: {simulation.get('engine', 'Basic Simulator')}\n"

    report += build_betting_summary(game, simulation)
    report += "\n"

    report += "Weather\n"
    report += "-------------------------\n"
    report += f"Temp: {weather.get('temp_f')} F\n"
    report += f"Wind: {weather.get('wind_mph')} mph {weather.get('wind_direction')}\n"
    report += f"Source: {weather.get('source')}\n\n"

    report += "Park Factor\n"
    report += "-------------------------\n"
    report += f"Run Factor: {park.get('run_factor')}\n"
    report += f"Source: {park.get('source')}\n\n"

    report += "Lineup Status\n"
    report += "-------------------------\n"
    report += f"{lineups.get('status')}\n"

    report += format_lineup(
        game["away"],
        lineups.get("away_lineup", []),
        lineups.get("away_fallback_hitters", [])
    )

    report += format_lineup(
        game["home"],
        lineups.get("home_lineup", []),
        lineups.get("home_fallback_hitters", [])
    )

    report += "\nInjury / Status Notes\n"
    report += "-------------------------\n"

    if not away_injuries and not home_injuries:
        report += "No injury/status notes found from roster endpoint.\n"
    else:
        for player in away_injuries:
            report += f"{game['away']}: {player['name']} - {player['status']}\n"

        for player in home_injuries:
            report += f"{game['home']}: {player['name']} - {player['status']}\n"

    report += "\nData Quality\n"
    report += "-------------------------\n"
    report += f"Score: {quality['score']}/100\n"

    if quality["notes"]:
        for note in quality["notes"]:
            report += f"- {note}\n"
    else:
        report += "No major data issues found.\n"

    report += build_confidence_summary(quality)
    report += "\n"

    report += build_model_explanation(game, simulation, park, weather, quality)
    report += "\n"

    return report


def save_game_report(game, report):
    Path("outputs").mkdir(exist_ok=True)

    away = game["away"].replace(" ", "_")
    home = game["home"].replace(" ", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{away}_at_{home}_{timestamp}.txt"
    path = Path("outputs") / filename

    path.write_text(report, encoding="utf-8")

    return path
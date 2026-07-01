def american_moneyline_from_probability(prob):
    prob = max(0.001, min(prob, 0.999))

    if prob >= 0.5:
        return round(-100 * prob / (1 - prob))

    return round(100 * (1 - prob) / prob)


def build_betting_summary(game, simulation):
    home_prob = simulation["home_win_probability"]
    away_prob = simulation["away_win_probability"]

    home_line = american_moneyline_from_probability(home_prob)
    away_line = american_moneyline_from_probability(away_prob)

    text = "\nFair Betting Lines\n"
    text += "------------------\n"
    text += f"{game['home']}: {home_line}\n"
    text += f"{game['away']}: {away_line}\n"

    return text
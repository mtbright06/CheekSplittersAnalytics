from calculators.base import BaseCalculator


class StartingPitchingCalculator(BaseCalculator):

    NAME = "Starting Pitching"
    WEIGHT = 0.35

    def score(self, game, index):

        away_score = self._pitcher_score(game.away.pitcher)
        home_score = self._pitcher_score(game.home.pitcher)

        if away_score > home_score:
            return 2

        if home_score > away_score:
            return -2

        return 0

    def reasons(self, game, index):

        away = game.away
        home = game.home

        reasons = []

        comparisons = [
            ("ERA", away.pitcher.era, home.pitcher.era, "lower"),
            ("WHIP", away.pitcher.whip, home.pitcher.whip, "lower"),
            ("K/9", away.pitcher.k_rate, home.pitcher.k_rate, "higher"),
            ("BB/9", away.pitcher.bb_rate, home.pitcher.bb_rate, "lower"),
            ("HR/9", away.pitcher.hr9, home.pitcher.hr9, "lower"),
        ]

        for label, away_value, home_value, direction in comparisons:
            reason = self._comparison_reason(
                label,
                away.name,
                away_value,
                home.name,
                home_value,
                direction,
            )

            if reason:
                reasons.append(reason)

        if not reasons:
            reasons.append("Starting pitching data unavailable or even")

        return reasons

    def _pitcher_score(self, pitcher):

        if pitcher.name is None or pitcher.name == "Unknown Starter":
            return 0

        score = 0

        score += self._lower_score(pitcher.era, 3.25, 4.00, 4.50, 5.00, 2)
        score += self._lower_score(pitcher.whip, 1.15, 1.30, 1.40, 1.50, 2)
        score += self._higher_score(pitcher.k_rate, 9.0, 7.5, 5.5, 4.5, 1)
        score += self._lower_score(pitcher.bb_rate, 2.2, 3.0, 4.0, 5.0, 1)
        score += self._lower_score(pitcher.hr9, 0.7, 1.0, 1.4, 1.8, 1)

        return score

    def _lower_score(self, value, elite, good, bad, awful, points):

        if value is None:
            return 0

        if value <= elite:
            return points

        if value <= good:
            return max(points - 1, 1)

        if value >= awful:
            return -points

        if value >= bad:
            return -max(points - 1, 1)

        return 0

    def _higher_score(self, value, elite, good, bad, awful, points):

        if value is None:
            return 0

        if value >= elite:
            return points

        if value >= good:
            return max(points - 1, 1)

        if value <= awful:
            return -points

        if value <= bad:
            return -max(points - 1, 1)

        return 0

    def _comparison_reason(
        self,
        label,
        away_name,
        away_value,
        home_name,
        home_value,
        direction,
    ):

        if away_value is None or home_value is None:
            return None

        if direction == "lower":
            if away_value < home_value:
                return f"{away_name} has the {label} advantage ({away_value:.2f} vs {home_value:.2f})"

            if home_value < away_value:
                return f"{home_name} has the {label} advantage ({home_value:.2f} vs {away_value:.2f})"

        if direction == "higher":
            if away_value > home_value:
                return f"{away_name} has the {label} advantage ({away_value:.2f} vs {home_value:.2f})"

            if home_value > away_value:
                return f"{home_name} has the {label} advantage ({home_value:.2f} vs {away_value:.2f})"

        return None

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

            if away_value is None or home_value is None:
                continue

            if direction == "lower":
                if away_value < home_value:
                    reasons.append(
                        f"{away.name} has the {label} advantage "
                        f"({away_value:.2f} vs {home_value:.2f})"
                    )
                elif home_value < away_value:
                    reasons.append(
                        f"{home.name} has the {label} advantage "
                        f"({home_value:.2f} vs {away_value:.2f})"
                    )

            if direction == "higher":
                if away_value > home_value:
                    reasons.append(
                        f"{away.name} has the {label} advantage "
                        f"({away_value:.2f} vs {home_value:.2f})"
                    )
                elif home_value > away_value:
                    reasons.append(
                        f"{home.name} has the {label} advantage "
                        f"({home_value:.2f} vs {away_value:.2f})"
                    )

        return reasons

    def _pitcher_score(self, pitcher):

        score = 0

        if pitcher.era is not None:
            if pitcher.era <= 3.25:
                score += 2
            elif pitcher.era <= 4.00:
                score += 1
            elif pitcher.era >= 5.00:
                score -= 2
            elif pitcher.era >= 4.50:
                score -= 1

        if pitcher.whip is not None:
            if pitcher.whip <= 1.15:
                score += 2
            elif pitcher.whip <= 1.30:
                score += 1
            elif pitcher.whip >= 1.50:
                score -= 2
            elif pitcher.whip >= 1.40:
                score -= 1

        if pitcher.k_rate is not None:
            if pitcher.k_rate >= 9.0:
                score += 1
            elif pitcher.k_rate <= 5.5:
                score -= 1

        if pitcher.bb_rate is not None:
            if pitcher.bb_rate <= 2.2:
                score += 1
            elif pitcher.bb_rate >= 4.0:
                score -= 1

        if pitcher.hr9 is not None:
            if pitcher.hr9 <= 0.7:
                score += 1
            elif pitcher.hr9 >= 1.4:
                score -= 1

        return score

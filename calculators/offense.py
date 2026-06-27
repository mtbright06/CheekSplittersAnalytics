from calculators.base import BaseCalculator


class OffenseCalculator(BaseCalculator):

    NAME = "Offense"

    WEIGHT = 0.25

    def score(self, game, index=None):

        away = game.away
        home = game.home

        score = 0

        if away.offense.runs_per_game > home.offense.runs_per_game:
            score += 1
        elif home.offense.runs_per_game > away.offense.runs_per_game:
            score -= 1

        return score

    def reasons(self, game, index=None):

        reasons = []

        away = game.away
        home = game.home

        if away.offense.runs_per_game > home.offense.runs_per_game:
            reasons.append(
                f"{away.name} scores more runs per game "
                f"({away.offense.runs_per_game:.1f} vs {home.offense.runs_per_game:.1f})"
            )

        elif home.offense.runs_per_game > away.offense.runs_per_game:
            reasons.append(
                f"{home.name} scores more runs per game "
                f"({home.offense.runs_per_game:.1f} vs {away.offense.runs_per_game:.1f})"
            )

        return reasons

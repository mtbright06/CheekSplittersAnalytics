from calculators.base import BaseCalculator


class OffenseCalculator(BaseCalculator):

    NAME = "Offense"

    WEIGHT = 0.25

    def score(self, game, index):

        away = game.away
        home = game.home

        if (
            away.offense.runs_per_game is None or
            home.offense.runs_per_game is None
        ):
            return 0

        if away.offense.runs_per_game > home.offense.runs_per_game:
            return 1

        if home.offense.runs_per_game > away.offense.runs_per_game:
            return -1

        return 0

    def reasons(self, game, index):

        away = game.away
        home = game.home

        if (
            away.offense.runs_per_game is None or
            home.offense.runs_per_game is None
        ):
            return ["Offense data unavailable"]

        if away.offense.runs_per_game > home.offense.runs_per_game:
            return [
                f"{away.name} scores more runs per game "
                f"({away.offense.runs_per_game} vs {home.offense.runs_per_game})"
            ]

        if home.offense.runs_per_game > away.offense.runs_per_game:
            return [
                f"{home.name} scores more runs per game "
                f"({home.offense.runs_per_game} vs {away.offense.runs_per_game})"
            ]

        return []

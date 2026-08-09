from calculators.base import BaseCalculator


class BullpenCalculator(BaseCalculator):

    NAME = "Bullpen"

    WEIGHT = 0.125

    ERA_FULL_STRENGTH_DELTA = 1.00

    def score(self, game, index):
        away_score = self._team_score(game.away.bullpen)
        home_score = self._team_score(game.home.bullpen)

        return round(
            self._clamp(
                (away_score - home_score) / 2,
                -1.0,
                1.0,
            ),
            3,
        )

    def _team_score(self, bullpen):
        if bullpen.era is None or bullpen.league_era is None:
            return 0.0

        league_era = self._value_or_default(bullpen.league_era, None)

        if league_era is None:
            return 0.0

        return self._clamp(
            (league_era - float(bullpen.era)) / self.ERA_FULL_STRENGTH_DELTA,
            -1.0,
            1.0,
        )

    def reasons(self, game, index):
        away = game.away
        home = game.home

        if away.bullpen.era is None or home.bullpen.era is None:
            return ["Bullpen data unavailable"]

        if away.bullpen.era < home.bullpen.era:
            return [
                f"{away.name} has the bullpen ERA advantage "
                f"({away.bullpen.era:.2f} vs {home.bullpen.era:.2f})"
            ]

        if home.bullpen.era < away.bullpen.era:
            return [
                f"{home.name} has the bullpen ERA advantage "
                f"({home.bullpen.era:.2f} vs {away.bullpen.era:.2f})"
            ]

        return []

    @staticmethod
    def _value_or_default(value, default):
        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

from calculators.base import BaseCalculator


class OffenseCalculator(BaseCalculator):

    NAME = "Offense"

    WEIGHT = 0.30

    LEAGUE_RPG_CENTER = 4.93
    RPG_FULL_STRENGTH_DELTA = 0.70

    def score(self, game, index):

        away = game.away
        home = game.home

        league_rpg = self._league_rpg(
            away.offense,
            home.offense,
        )
        away_score = self._team_score(
            away.offense.runs_per_game,
            league_rpg,
        )
        home_score = self._team_score(
            home.offense.runs_per_game,
            league_rpg,
        )

        return round(
            self._clamp(
                (away_score - home_score) / 2,
                -1.0,
                1.0,
            ),
            3,
        )

    def _team_score(self, runs_per_game, league_rpg=None):
        if runs_per_game is None:
            return 0.0

        return self._clamp(
            (
                float(runs_per_game)
                - self._value_or_default(
                    league_rpg,
                    self.LEAGUE_RPG_CENTER,
                )
            )
            / self.RPG_FULL_STRENGTH_DELTA,
            -1.0,
            1.0,
        )

    def _league_rpg(self, away_offense, home_offense):
        for offense in (away_offense, home_offense):
            value = self._value_or_default(
                offense.league_runs_per_game,
                None,
            )
            if value is not None:
                return value

        return self.LEAGUE_RPG_CENTER

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

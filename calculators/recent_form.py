from calculators.base import BaseCalculator


class RecentFormCalculator(BaseCalculator):

    NAME = "Recent Form"

    WEIGHT = 0.025

    RPG_FULL_STRENGTH_DELTA = 0.70
    FULL_SAMPLE_GAMES = 10.0
    MAX_SHRINKAGE = 0.25

    def score(self, game, index):
        if self._missing_form(game.away.form) or self._missing_form(game.home.form):
            return 0.0

        away_score = self._team_score(game.away.form)
        home_score = self._team_score(game.home.form)

        return round(
            self._clamp(
                (away_score - home_score) / 2,
                -1.0,
                1.0,
            ),
            3,
        )

    def _team_score(self, form):
        if self._missing_form(form):
            return 0.0

        shrinkage = self._clamp(
            float(form.recent_games) / self.FULL_SAMPLE_GAMES,
            0.0,
            1.0,
        ) * self.MAX_SHRINKAGE

        adjusted_delta = (
            float(form.recent_runs_per_game)
            - float(form.season_runs_per_game)
        ) * shrinkage

        return self._clamp(
            adjusted_delta / self.RPG_FULL_STRENGTH_DELTA,
            -1.0,
            1.0,
        )

    def reasons(self, game, index):
        away = game.away
        home = game.home

        if (
            away.form.recent_runs_per_game is None
            or home.form.recent_runs_per_game is None
        ):
            return ["Recent scoring form unavailable"]

        away_delta = (
            away.form.recent_runs_per_game
            - away.form.season_runs_per_game
        )
        home_delta = (
            home.form.recent_runs_per_game
            - home.form.season_runs_per_game
        )

        if away_delta > home_delta:
            return [
                f"{away.name} has the stronger stabilized recent scoring form "
                f"({away.form.recent_runs_per_game:.2f} vs season "
                f"{away.form.season_runs_per_game:.2f})"
            ]

        if home_delta > away_delta:
            return [
                f"{home.name} has the stronger stabilized recent scoring form "
                f"({home.form.recent_runs_per_game:.2f} vs season "
                f"{home.form.season_runs_per_game:.2f})"
            ]

        return []

    @staticmethod
    def _missing_form(form):
        return (
            form is None
            or form.season_runs_per_game is None
            or form.recent_runs_per_game is None
            or form.recent_games is None
        )

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

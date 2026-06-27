from providers.kbo_provider import KBOProvider


class PitcherLoader:

    @staticmethod
    def load(game):

        PitcherLoader._apply_team_data(game.away)
        PitcherLoader._apply_team_data(game.home)

    @staticmethod
    def _apply_team_data(team):

        data = KBOProvider.get_team_data(team.name)

        if data is None:
            team.pitcher.name = "Unknown Starter"
            team.pitcher.era = None
            team.pitcher.whip = None
            team.offense.runs_per_game = None
            return

        pitcher = data["pitcher"]
        offense = data["offense"]

        team.pitcher.name = pitcher["name"]
        team.pitcher.era = pitcher["era"]
        team.pitcher.whip = pitcher["whip"]

        team.offense.runs_per_game = offense["runs_per_game"]

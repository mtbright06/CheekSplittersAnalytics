from providers.kbo_data_provider import KBODataProvider


class PitcherLoader:

    @staticmethod
    def load(game):

        PitcherLoader._apply_team_data(game.away)
        PitcherLoader._apply_team_data(game.home)

        if not game.game_url:
            return

        details = KBODataProvider.get_game_details(game.game_url)

        away = details["away"]
        home = details["home"]

        game.away.pitcher.name = away["name"]
        game.away.pitcher.era = float(away["era"])

        game.home.pitcher.name = home["name"]
        game.home.pitcher.era = float(home["era"])

    @staticmethod
    def _apply_team_data(team):

        data = KBODataProvider.get_team_data(team.name)

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

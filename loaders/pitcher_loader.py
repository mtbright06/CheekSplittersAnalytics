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

        PitcherLoader._apply_live_pitcher(game.away.pitcher, away)
        PitcherLoader._apply_live_pitcher(game.home.pitcher, home)

    @staticmethod
    def _apply_live_pitcher(pitcher, summary):

        if summary["name"] == "Unknown Starter":
            PitcherLoader._clear_pitcher(pitcher)
            pitcher.name = "Unknown Starter"
            return

        pitcher.name = summary["name"]
        pitcher.record = summary["record"]
        pitcher.era = PitcherLoader._to_float(summary["era"])

        profile_url = summary.get("profile_url")

        if not profile_url:
            return

        details = KBODataProvider.get_pitcher_details(profile_url)

        pitcher.throws = details.get("throws")
        pitcher.bats = details.get("bats")
        pitcher.whip = details.get("whip")
        pitcher.ip = details.get("ip")
        pitcher.so = details.get("so")
        pitcher.bb = details.get("bb")
        pitcher.hr_allowed = details.get("hr_allowed")
        pitcher.k_rate = details.get("k_rate")
        pitcher.bb_rate = details.get("bb_rate")
        pitcher.hr9 = details.get("hr9")

        if details.get("record"):
            pitcher.record = details.get("record")

        if details.get("era") is not None:
            pitcher.era = details.get("era")

    @staticmethod
    def _apply_team_data(team):

        data = KBODataProvider.get_team_data(team.name)

        if data is None:
            PitcherLoader._clear_pitcher(team.pitcher)
            team.offense.runs_per_game = None
            return

        offense = data["offense"]
        team.offense.runs_per_game = offense["runs_per_game"]

    @staticmethod
    def _clear_pitcher(pitcher):

        pitcher.name = None
        pitcher.throws = None
        pitcher.bats = None
        pitcher.record = None
        pitcher.era = None
        pitcher.whip = None
        pitcher.ip = None
        pitcher.so = None
        pitcher.bb = None
        pitcher.hr_allowed = None
        pitcher.k_rate = None
        pitcher.bb_rate = None
        pitcher.hr9 = None

    @staticmethod
    def _to_float(value):

        if value is None or value == "":
            return None

        try:
            return float(value)
        except ValueError:
            return None

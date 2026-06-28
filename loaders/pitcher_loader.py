from providers.kbo_data_provider import KBODataProvider


class PitcherLoader:

    @staticmethod
    def load(game):

        PitcherLoader._apply_team_data(game.away)
        PitcherLoader._apply_team_data(game.home)

        if not game.game_url:
            return

        details = KBODataProvider.get_game_details(game.game_url)

        PitcherLoader._apply_live_pitcher(
            game.away.pitcher,
            details["away"]
        )

        PitcherLoader._apply_live_pitcher(
            game.home.pitcher,
            details["home"]
        )

    @staticmethod
    def _apply_live_pitcher(pitcher, summary):

        if summary["name"] == "Unknown Starter":
            PitcherLoader._clear_pitcher(pitcher)
            pitcher.name = "Unknown Starter"
            return

        pitcher.name = summary["name"]
        pitcher.record = summary.get("record")
        pitcher.era = PitcherLoader._to_float(summary.get("era"))

        profile_url = summary.get("profile_url")

        if not profile_url:
            return

        profile = KBODataProvider.get_pitcher_details(profile_url)

        pitcher.throws = profile.get("throws")
        pitcher.bats = profile.get("bats")
        pitcher.whip = profile.get("whip")
        pitcher.ip = profile.get("ip")
        pitcher.so = profile.get("so")
        pitcher.bb = profile.get("bb")
        pitcher.hr_allowed = profile.get("hr_allowed")
        pitcher.k_rate = profile.get("k_rate")
        pitcher.bb_rate = profile.get("bb_rate")
        pitcher.hr9 = profile.get("hr9")

        if profile.get("record"):
            pitcher.record = profile.get("record")

        if profile.get("era") is not None:
            pitcher.era = profile.get("era")

    @staticmethod
    def _apply_team_data(team):

        data = KBODataProvider.get_team_data(team.name)

        PitcherLoader._clear_pitcher(team.pitcher)

        if data is None:
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

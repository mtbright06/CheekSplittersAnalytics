from providers.kbo_data_provider import KBODataProvider
from datetime import date


class PitcherLoader:

    @staticmethod
    def load(game):

        PitcherLoader._apply_team_data(game.away)
        PitcherLoader._apply_team_data(game.home)

        if not game.game_url:
            return

        details = KBODataProvider.get_game_details(game.game_url)
        game_date = details.get("game_date")

        PitcherLoader._apply_live_pitcher(
            game.away.pitcher,
            details["away"],
            game_date=game_date,
        )

        PitcherLoader._apply_live_pitcher(
            game.home.pitcher,
            details["home"],
            game_date=game_date,
        )

        PitcherLoader._guard_distinct_starters(
            game.away.pitcher,
            game.home.pitcher,
        )

    @staticmethod
    def _apply_live_pitcher(pitcher, summary, *, game_date=None):
        league_era = pitcher.league_era

        if summary["name"] == "Unknown Starter":
            PitcherLoader._clear_pitcher(pitcher)
            pitcher.league_era = league_era
            pitcher.name = "Unknown Starter"
            pitcher.data_source = "starter_unavailable"
            pitcher.starter_confirmed = False
            return

        pitcher.name = summary.get("name") or None
        pitcher.record = summary.get("record")
        pitcher.era = PitcherLoader._to_float(summary.get("era"))
        pitcher.league_era = league_era
        pitcher.data_source = "starter_summary"
        pitcher.starter_confirmed = bool(pitcher.name)

        profile_url = summary.get("profile_url")
        pitcher.profile_url = profile_url

        if not profile_url:
            return

        profile = KBODataProvider.get_pitcher_details(profile_url)

        if profile.get("name"):
            pitcher.name = profile["name"]

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
        pitcher.games = profile.get("games")
        pitcher.games_started = profile.get("games_started")
        pitcher.last_role = profile.get("last_role")
        pitcher.previous_appearance_date = profile.get(
            "previous_appearance_date"
        )
        pitcher.previous_start_date = profile.get("previous_start_date")
        pitcher.previous_start_ip = profile.get("previous_start_ip")
        pitcher.previous_start_pitch_count = profile.get(
            "previous_start_pitch_count"
        )
        pitcher.days_rest = PitcherLoader._days_between(
            pitcher.previous_start_date,
            game_date,
        )
        pitcher.role_context = PitcherLoader._role_context(pitcher)
        pitcher.data_source = "starter_profile"
        pitcher.starter_confirmed = bool(pitcher.name)

        if profile.get("record"):
            pitcher.record = profile.get("record")

        if profile.get("era") is not None:
            pitcher.era = profile.get("era")

    @staticmethod
    def _role_context(pitcher):
        games_started = getattr(pitcher, "games_started", None)

        if games_started is None:
            return None

        if games_started == 0:
            return "no_prior_starts"

        if games_started <= 2:
            return "limited_starting_role"

        return "established_starter"

    @staticmethod
    def _days_between(previous, current):
        if not previous or not current:
            return None

        try:
            return (
                date.fromisoformat(current)
                - date.fromisoformat(previous)
            ).days
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _guard_distinct_starters(away_pitcher, home_pitcher):
        away_key = PitcherLoader._starter_identity_key(away_pitcher)
        home_key = PitcherLoader._starter_identity_key(home_pitcher)

        if not away_key or not home_key or away_key != home_key:
            return

        PitcherLoader._mark_mapping_unverified(away_pitcher)
        PitcherLoader._mark_mapping_unverified(home_pitcher)

    @staticmethod
    def _starter_identity_key(pitcher):
        for attr in ("id", "profile_url"):
            value = getattr(pitcher, attr, None)
            if value:
                return f"{attr}:{value}"

        name = getattr(pitcher, "name", None)
        if name and name != "Unknown Starter":
            return f"name:{name}"

        return None

    @staticmethod
    def _mark_mapping_unverified(pitcher):
        PitcherLoader._clear_pitcher(pitcher)
        pitcher.name = "Unknown Starter"
        pitcher.data_source = "starter_mapping_unverified"
        pitcher.starter_confirmed = False

    @staticmethod
    def _apply_team_data(team):

        data = KBODataProvider.get_team_data(team.name)

        PitcherLoader._clear_pitcher(team.pitcher)

        if data is None:
            team.offense.runs_per_game = None
            return

        offense = data["offense"]
        team.offense.runs_per_game = offense["runs_per_game"]
        team.offense.league_runs_per_game = offense.get(
            "league_runs_per_game"
        )
        team.offense.offense_source = offense.get("offense_source")
        team.offense.runs_allowed_per_game = offense.get(
            "runs_allowed_per_game"
        )
        team.offense.home_runs_per_game = offense.get(
            "home_runs_per_game"
        )
        team.offense.away_runs_per_game = offense.get(
            "away_runs_per_game"
        )
        team.offense.home_games = offense.get("home_games")
        team.offense.away_games = offense.get("away_games")
        team.offense.source_url = offense.get("source_url")
        team.offense.retrieved_at = offense.get("retrieved_at")
        team.offense.source_row = offense.get("source_row")
        team.bullpen.era = offense.get("bullpen_era")
        team.bullpen.league_era = offense.get("league_bullpen_era")
        team.bullpen.source = offense.get("bullpen_source")
        team.pitcher.league_era = offense.get("league_starting_era")
        team.form.season_runs_per_game = offense.get("runs_per_game")
        team.form.recent_runs_per_game = offense.get("last_10_runs_per_game")
        team.form.recent_games = offense.get("last_10_games")
        team.form.source = offense.get("recent_form_source")

    @staticmethod
    def _clear_pitcher(pitcher):

        pitcher.name = None
        pitcher.id = None
        pitcher.profile_url = None
        pitcher.throws = None
        pitcher.bats = None
        pitcher.record = None
        pitcher.era = None
        pitcher.league_era = None
        pitcher.whip = None
        pitcher.ip = None
        pitcher.so = None
        pitcher.bb = None
        pitcher.hr_allowed = None
        pitcher.k_rate = None
        pitcher.bb_rate = None
        pitcher.hr9 = None
        pitcher.games = None
        pitcher.games_started = None
        pitcher.last_role = None
        pitcher.previous_appearance_date = None
        pitcher.previous_start_date = None
        pitcher.previous_start_ip = None
        pitcher.previous_start_pitch_count = None
        pitcher.days_rest = None
        pitcher.role_context = None
        pitcher.data_source = None
        pitcher.starter_confirmed = False

    @staticmethod
    def _to_float(value):

        if value is None or value == "":
            return None

        try:
            return float(value)
        except ValueError:
            return None

from __future__ import annotations

from engine.nhl.models import (
    NHLGoalieStats,
    NHLMoneyPuckGoalieStats,
    NHLMoneyPuckSkaterStats,
    NHLMoneyPuckTeamStats,
    NHLSkaterStats,
    NHLTeam,
    NHLTeamStats,
)
from engine.nhl.profiles import (
    NHLStatisticalProfileService,
    moneypuck_to_official_season,
    official_to_moneypuck_season,
)


class FakeOfficialProvider:
    def __init__(
        self,
        *,
        teams=None,
        skaters=None,
        goalies=None,
        fail=False,
    ):
        self.teams = teams or []
        self.skaters = skaters or []
        self.goalies = goalies or []
        self.fail = fail

    def load_team_stats(self, *, season_id):
        if self.fail:
            raise RuntimeError("official down")
        return self.teams

    def load_skater_stats(self, *, season_id):
        if self.fail:
            raise RuntimeError("official down")
        return self.skaters

    def load_goalie_stats(self, *, season_id):
        if self.fail:
            raise RuntimeError("official down")
        return self.goalies


class FakeAdvancedProvider:
    def __init__(
        self,
        *,
        teams=None,
        skaters=None,
        goalies=None,
        fail=False,
    ):
        self.teams = teams or []
        self.skaters = skaters or []
        self.goalies = goalies or []
        self.fail = fail

    def load_team_advanced_stats(self, *, season):
        if self.fail:
            raise RuntimeError("advanced down")
        return self.teams

    def load_skater_advanced_stats(self, *, season):
        if self.fail:
            raise RuntimeError("advanced down")
        return self.skaters

    def load_goalie_advanced_stats(self, *, season):
        if self.fail:
            raise RuntimeError("advanced down")
        return self.goalies


def test_season_mapping_preserves_official_and_moneypuck_contracts():
    assert official_to_moneypuck_season(20252026) == 2025
    assert moneypuck_to_official_season(2025) == 20252026
    try:
        official_to_moneypuck_season(2025)
    except ValueError:
        pass
    else:
        raise AssertionError("invalid official season id should fail")


def test_team_profile_merges_official_and_moneypuck_by_canonical_team():
    service = _service(
        official=FakeOfficialProvider(teams=[_team_stats()]),
        advanced=FakeAdvancedProvider(teams=[_team_advanced("ALL")]),
    )

    profile = service.load_team_profiles(
        season_id=20252026,
        teams=[_team()],
    )[0]

    assert profile.team_id == 6
    assert profile.abbreviation == "BOS"
    assert profile.full_name == "Boston Bruins"
    assert profile.official.team_id == 6
    assert profile.advanced["ALL"].x_goals_percentage == 0.53
    assert profile.source_state.official_available is True
    assert profile.source_state.advanced_available is True
    assert profile.source_state.concerns == ()


def test_profiles_keep_official_only_and_advanced_only_rows():
    service = _service(
        official=FakeOfficialProvider(skaters=[_skater_stats()]),
        advanced=FakeAdvancedProvider(
            skaters=[_skater_advanced(player_id=99, name="Advanced Only")]
        ),
    )

    profiles = {
        profile.player_id: profile
        for profile in service.load_skater_profiles(season_id=20252026)
    }

    assert profiles[8478402].official is not None
    assert profiles[8478402].advanced == {}
    assert "advanced_stats_missing" in profiles[8478402].source_state.concerns
    assert profiles[99].official is None
    assert profiles[99].advanced["ALL"][0].name == "Advanced Only"
    assert "official_stats_missing" in profiles[99].source_state.concerns


def test_skater_profile_preserves_money_puck_situations_and_trade_rows():
    service = _service(
        official=FakeOfficialProvider(
            skaters=[_skater_stats(team_abbreviations="EDM,TOR")]
        ),
        advanced=FakeAdvancedProvider(
            skaters=[
                _skater_advanced(team_abbreviation="EDM", situation="ALL"),
                _skater_advanced(team_abbreviation="TOR", situation="ALL"),
                _skater_advanced(team_abbreviation="TOR", situation="5ON5"),
            ]
        ),
    )

    profile = service.load_skater_profiles(season_id=20252026)[0]

    assert profile.player_id == 8478402
    assert profile.team_context == "EDM,TOR"
    assert len(profile.advanced["ALL"]) == 2
    assert profile.advanced["5ON5"][0].team_abbreviation == "TOR"
    assert "multi_team_advanced_context" in profile.source_state.concerns
    assert "team_context_mismatch" not in profile.source_state.concerns


def test_goalie_profile_merges_by_player_id_and_preserves_situation():
    service = _service(
        official=FakeOfficialProvider(goalies=[_goalie_stats()]),
        advanced=FakeAdvancedProvider(
            goalies=[
                _goalie_advanced(situation="ALL"),
                _goalie_advanced(situation="5ON5"),
            ]
        ),
    )

    profile = service.load_goalie_profiles(season_id=20252026)[0]

    assert profile.player_id == 8480280
    assert profile.name == "Jeremy Swayman"
    assert profile.official.save_pct == 0.916
    assert profile.advanced["ALL"][0].goals_saved_above_expected == 5.5
    assert profile.advanced["5ON5"][0].expected_goals_against == 130.5


def test_provider_failure_is_source_state_not_profile_corruption():
    service = _service(
        official=FakeOfficialProvider(fail=True),
        advanced=FakeAdvancedProvider(skaters=[_skater_advanced()]),
    )

    profile = service.load_skater_profiles(season_id=20252026)[0]

    assert profile.official is None
    assert profile.advanced["ALL"][0].player_id == 8478402
    assert "official_source_unavailable" in profile.source_state.concerns
    assert profile.source_state.advanced_available is True


def test_empty_sources_are_safe():
    service = _service()

    assert service.load_team_profiles(season_id=20252026, teams=[]) == []
    assert service.load_skater_profiles(season_id=20252026) == []
    assert service.load_goalie_profiles(season_id=20252026) == []


def _service(
    *,
    official=None,
    advanced=None,
):
    return NHLStatisticalProfileService(
        official_provider=official or FakeOfficialProvider(),
        advanced_provider=advanced or FakeAdvancedProvider(),
        team_loader=lambda: [_team()],
    )


def _team():
    return NHLTeam(
        source_team_id=6,
        full_name="Boston Bruins",
        abbreviation="BOS",
        logo_key="bos",
    )


def _team_stats():
    return NHLTeamStats(
        team_id=6,
        team_name="Boston Bruins",
        season_id=20252026,
        situation="ALL",
        games_played=82,
        goals_for=250,
    )


def _team_advanced(situation):
    return NHLMoneyPuckTeamStats(
        team_abbreviation="BOS",
        season=2025,
        situation=situation,
        games_played=82,
        x_goals_percentage=0.53,
    )


def _skater_stats(**overrides):
    values = {
        "player_id": 8478402,
        "name": "Connor McDavid",
        "season_id": 20252026,
        "situation": "ALL",
        "team_abbreviations": "EDM",
        "position": "C",
        "games_played": 82,
        "goals": 44,
    }
    values.update(overrides)
    return NHLSkaterStats(**values)


def _skater_advanced(**overrides):
    values = {
        "player_id": 8478402,
        "name": "Connor McDavid",
        "team_abbreviation": "EDM",
        "position": "C",
        "season": 2025,
        "situation": "ALL",
        "games_played": 82,
        "individual_x_goals": 42.5,
    }
    values.update(overrides)
    return NHLMoneyPuckSkaterStats(**values)


def _goalie_stats():
    return NHLGoalieStats(
        player_id=8480280,
        name="Jeremy Swayman",
        season_id=20252026,
        situation="ALL",
        team_abbreviations="BOS",
        games_played=55,
        save_pct=0.916,
    )


def _goalie_advanced(**overrides):
    values = {
        "player_id": 8480280,
        "name": "Jeremy Swayman",
        "team_abbreviation": "BOS",
        "season": 2025,
        "situation": "ALL",
        "games_played": 55,
        "expected_goals_against": 130.5,
        "goals_against": 125.0,
        "goals_saved_above_expected": 5.5,
    }
    values.update(overrides)
    return NHLMoneyPuckGoalieStats(**values)

from __future__ import annotations

from datetime import UTC, date, datetime

from engine.nhl.availability import NHLGameAvailability, NHLTeamAvailability
from engine.nhl.goalies import CONFIRMED, PROJECTED, UNKNOWN
from engine.nhl.matchups import (
    NHLMatchupContextComposer,
    build_nhl_matchup_contexts,
    statistical_season_id_for_game_date,
)
from engine.nhl.models import (
    NHLGame,
    NHLGameSourceState,
    NHLGoalieAssignment,
    NHLGoalieProfile,
    NHLMoneyPuckGoalieStats,
    NHLMoneyPuckTeamStats,
    NHLPlayer,
    NHLProfileSourceState,
    NHLTeam,
    NHLTeamProfile,
)


def test_team_profiles_attach_to_correct_away_and_home_sides():
    composer = NHLMatchupContextComposer(
        profile_service=FakeProfiles(
            team_profiles=[
                _team_profile("BOS", 6),
                _team_profile("NYR", 3),
            ],
        ),
        availability_provider=FakeAvailability(_availability()),
    )

    context = composer.build_contexts([_game()])[0]

    assert context.away_team_profile.abbreviation == "BOS"
    assert context.home_team_profile.abbreviation == "NYR"
    assert "ALL" in context.away_team_profile.advanced
    assert "5ON5" in context.home_team_profile.advanced


def test_confirmed_and_projected_goalie_profiles_resolve_by_player_id():
    availability = _availability(
        away_assignment=_assignment(CONFIRMED, _player(10, "Away Goalie")),
        home_assignment=_assignment(PROJECTED, _player(20, "Home Goalie")),
    )
    composer = NHLMatchupContextComposer(
        profile_service=FakeProfiles(
            team_profiles=[_team_profile("BOS", 6), _team_profile("NYR", 3)],
            goalie_profiles=[
                _goalie_profile(10, "Away Goalie"),
                _goalie_profile(20, "Home Goalie"),
            ],
        ),
        availability_provider=FakeAvailability(availability),
    )

    context = composer.build_contexts([_game()])[0]

    assert context.away_goalie_profile.player_id == 10
    assert context.home_goalie_profile.player_id == 20
    assert context.away_goalie_assignment.status == CONFIRMED
    assert context.home_goalie_assignment.status == PROJECTED


def test_unknown_goalie_keeps_team_context_without_choosing_candidate():
    composer = NHLMatchupContextComposer(
        profile_service=FakeProfiles(
            team_profiles=[_team_profile("BOS", 6), _team_profile("NYR", 3)],
            goalie_profiles=[_goalie_profile(10, "Away Goalie")],
        ),
        availability_provider=FakeAvailability(
            _availability(away_assignment=_assignment(UNKNOWN, None))
        ),
    )

    context = composer.build_contexts([_game()])[0]

    assert context.away_team_profile.abbreviation == "BOS"
    assert context.away_goalie_profile is None
    assert "away_goalie_profile_missing" not in context.concerns


def test_goalie_identity_mismatch_is_a_concern_not_an_inferred_profile():
    composer = NHLMatchupContextComposer(
        profile_service=FakeProfiles(
            team_profiles=[_team_profile("BOS", 6), _team_profile("NYR", 3)],
            goalie_profiles=[_goalie_profile(99, "Other Goalie")],
        ),
        availability_provider=FakeAvailability(
            _availability(
                away_assignment=_assignment(CONFIRMED, _player(10, "Away Goalie"))
            )
        ),
    )

    context = composer.build_contexts([_game()])[0]

    assert context.away_goalie_profile is None
    assert "away_goalie_profile_missing" in context.concerns


def test_availability_failure_preserves_statistical_context():
    composer = NHLMatchupContextComposer(
        profile_service=FakeProfiles(
            team_profiles=[_team_profile("BOS", 6), _team_profile("NYR", 3)],
        ),
        availability_provider=FailingAvailability(),
    )

    context = composer.build_contexts([_game()])[0]

    assert context.away_team_profile.abbreviation == "BOS"
    assert context.home_team_profile.abbreviation == "NYR"
    assert context.away_availability is None
    assert "availability_unavailable" in context.concerns


def test_partial_statistical_profiles_leave_context_buildable():
    composer = NHLMatchupContextComposer(
        profile_service=FakeProfiles(team_profiles=[_team_profile("BOS", 6)]),
        availability_provider=FakeAvailability(_availability()),
    )

    context = composer.build_contexts([_game()])[0]

    assert context.away_team_profile.abbreviation == "BOS"
    assert context.home_team_profile is None
    assert "home_team_profile_missing" in context.concerns


def test_future_season_without_stats_does_not_use_prior_season():
    context = NHLMatchupContextComposer(
        profile_service=FakeProfiles(team_profiles=[]),
        availability_provider=FakeAvailability(_availability()),
    ).build_contexts([_game(start=datetime(2026, 10, 10, tzinfo=UTC))])[0]

    assert context.statistical_season_id == 20262027
    assert context.statistical_context == "REQUESTED_SEASON"
    assert context.away_team_profile is None
    assert "away_team_profile_missing" in context.concerns


def test_historical_game_current_availability_contamination_stays_visible():
    historical = _game(
        start=datetime(2025, 1, 10, tzinfo=UTC),
        source_state=NHLGameSourceState(
            roster_context="CURRENT_ROSTER_OMITTED_HISTORICAL",
            concerns=("current_roster_not_attached_to_historical_game",),
        ),
    )
    availability = _availability(
        concerns=("historical_availability_omitted",),
    )
    context = NHLMatchupContextComposer(
        profile_service=FakeProfiles(
            team_profiles=[_team_profile("BOS", 6), _team_profile("NYR", 3)],
        ),
        availability_provider=FakeAvailability(availability),
    ).build_contexts([historical])[0]

    assert context.statistical_season_id == 20242025
    assert "current_roster_not_attached_to_historical_game" in context.concerns
    assert "historical_availability_omitted" in context.concerns


def test_empty_slate_is_safe_and_bulk_composition_is_deterministic():
    service = FakeProfiles()
    provider = FakeAvailability(_availability())
    composer = NHLMatchupContextComposer(
        profile_service=service,
        availability_provider=provider,
    )

    assert composer.build_contexts([]) == []
    contexts = composer.build_contexts([_game(), _game(game_id=2)])

    assert [context.game.source_game_id for context in contexts] == [1, 2]
    assert service.team_loads == 1
    assert service.goalie_loads == 1
    assert provider.loads == 2


def test_bulk_helper_uses_game_loader_once():
    calls = []

    def game_loader(target_date):
        calls.append(target_date)
        return [_game()]

    contexts = build_nhl_matchup_contexts(
        date(2026, 10, 10),
        game_loader=game_loader,
        profile_service=FakeProfiles(
            team_profiles=[_team_profile("BOS", 6), _team_profile("NYR", 3)],
        ),
        availability_provider=FakeAvailability(_availability()),
    )

    assert len(contexts) == 1
    assert calls == [date(2026, 10, 10)]


def test_statistical_season_mapping():
    assert statistical_season_id_for_game_date(date(2026, 8, 9)) == 20252026
    assert statistical_season_id_for_game_date(date(2026, 10, 1)) == 20262027


class FakeProfiles:
    def __init__(self, *, team_profiles=None, goalie_profiles=None):
        self.team_profiles = team_profiles or []
        self.goalie_profiles = goalie_profiles or []
        self.team_loads = 0
        self.goalie_loads = 0

    def load_team_profiles(self, *, season_id=None):
        self.team_loads += 1
        return self.team_profiles

    def load_goalie_profiles(self, *, season_id=None):
        self.goalie_loads += 1
        return self.goalie_profiles

    def load_skater_profiles(self, *, season_id=None):
        return []


class FakeAvailability:
    def __init__(self, availability):
        self.availability = availability
        self.loads = 0

    def load_game_availability(self, game):
        self.loads += 1
        return self.availability


class FailingAvailability:
    def load_game_availability(self, game):
        raise RuntimeError("availability down")


def _game(
    *,
    game_id=1,
    start=datetime(2026, 10, 10, tzinfo=UTC),
    source_state=None,
):
    return NHLGame(
        source_game_id=game_id,
        game_date=start,
        away_team=_team("BOS", 6, "Boston Bruins"),
        home_team=_team("NYR", 3, "New York Rangers"),
        game_status="SCHEDULED",
        source_state=source_state or NHLGameSourceState(),
    )


def _team(abbreviation, team_id, name):
    return NHLTeam(
        source_team_id=team_id,
        full_name=name,
        abbreviation=abbreviation,
        logo_key=abbreviation.lower(),
    )


def _team_profile(abbreviation, team_id):
    return NHLTeamProfile(
        team_id=team_id,
        abbreviation=abbreviation,
        full_name=f"{abbreviation} Team",
        season_id=20262027,
        moneypuck_season=2026,
        advanced={
            "ALL": NHLMoneyPuckTeamStats(
                team_abbreviation=abbreviation,
                season=2026,
                situation="ALL",
                games_played=82,
            ),
            "5ON5": NHLMoneyPuckTeamStats(
                team_abbreviation=abbreviation,
                season=2026,
                situation="5ON5",
                games_played=82,
            ),
        },
        source_state=NHLProfileSourceState(
            official_available=True,
            advanced_available=True,
        ),
    )


def _goalie_profile(player_id, name):
    return NHLGoalieProfile(
        player_id=player_id,
        name=name,
        team_context="BOS",
        season_id=20262027,
        moneypuck_season=2026,
        advanced={
            "5ON5": (
                NHLMoneyPuckGoalieStats(
                    player_id=player_id,
                    name=name,
                    team_abbreviation="BOS",
                    season=2026,
                    situation="5ON5",
                    games_played=30,
                ),
            )
        },
        source_state=NHLProfileSourceState(
            official_available=True,
            advanced_available=True,
        ),
    )


def _availability(
    *,
    away_assignment=None,
    home_assignment=None,
    concerns=(),
):
    return NHLGameAvailability(
        source_game_id=1,
        away=NHLTeamAvailability(
            team_abbreviation="BOS",
            goalie_assignment=away_assignment or _assignment(UNKNOWN, None),
            state="COMPLETE",
        ),
        home=NHLTeamAvailability(
            team_abbreviation="NYR",
            goalie_assignment=home_assignment or _assignment(UNKNOWN, None),
            state="COMPLETE",
        ),
        concerns=concerns,
    )


def _assignment(status, player):
    return NHLGoalieAssignment(
        status=status,
        player=player,
        source="test",
    )


def _player(player_id, name):
    return NHLPlayer(
        source_player_id=player_id,
        name=name,
        position="G",
    )

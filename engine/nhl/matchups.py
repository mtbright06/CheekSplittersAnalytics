from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Protocol

from engine.nhl.availability import (
    DailyFaceoffAvailabilityProvider,
    NHLGameAvailability,
    NHLGameAvailabilityProvider,
)
from engine.nhl.game_builder import build_nhl_games
from engine.nhl.goalies import CONFIRMED, PROJECTED
from engine.nhl.models import (
    NHLGame,
    NHLGoalieAssignment,
    NHLGoalieProfile,
    NHLSkaterProfile,
    NHLTeamProfile,
)
from engine.nhl.profiles import NHLStatisticalProfileService
from engine.nhl.stats import current_nhl_season_id
from engine.nhl.teams import normalize_nhl_abbreviation


@dataclass(frozen=True)
class NHLMatchupContext:
    game: NHLGame
    statistical_season_id: int
    statistical_context: str
    away_team_profile: NHLTeamProfile | None = None
    home_team_profile: NHLTeamProfile | None = None
    away_availability: NHLGameAvailability | None = None
    home_availability: NHLGameAvailability | None = None
    away_goalie_assignment: NHLGoalieAssignment | None = None
    home_goalie_assignment: NHLGoalieAssignment | None = None
    away_goalie_profile: NHLGoalieProfile | None = None
    home_goalie_profile: NHLGoalieProfile | None = None
    concerns: tuple[str, ...] = ()


class NHLProfileServiceProtocol(Protocol):
    def load_team_profiles(
        self,
        *,
        season_id: int | None = None,
    ) -> list[NHLTeamProfile]:
        ...

    def load_goalie_profiles(
        self,
        *,
        season_id: int | None = None,
    ) -> list[NHLGoalieProfile]:
        ...

    def load_skater_profiles(
        self,
        *,
        season_id: int | None = None,
    ) -> list[NHLSkaterProfile]:
        ...


class NHLMatchupContextComposer:
    def __init__(
        self,
        *,
        profile_service: NHLProfileServiceProtocol | None = None,
        availability_provider: NHLGameAvailabilityProvider | None = None,
    ) -> None:
        self._profile_service = profile_service or NHLStatisticalProfileService()
        self._availability_provider = (
            availability_provider or DailyFaceoffAvailabilityProvider()
        )

    def build_contexts(
        self,
        games: list[NHLGame],
        *,
        target_date: str | date | None = None,
    ) -> list[NHLMatchupContext]:
        if not games:
            return []
        season_id = statistical_season_id_for_game_date(
            _context_date(
                target_date,
                games[0].game_date,
            )
        )
        team_profiles = {
            normalize_nhl_abbreviation(profile.abbreviation): profile
            for profile in self._profile_service.load_team_profiles(
                season_id=season_id
            )
        }
        goalie_profiles = {
            profile.player_id: profile
            for profile in self._profile_service.load_goalie_profiles(
                season_id=season_id
            )
        }
        contexts = []
        for game in games:
            contexts.append(
                self._build_context(
                    game,
                    season_id=season_id,
                    team_profiles=team_profiles,
                    goalie_profiles=goalie_profiles,
                )
            )
        return contexts

    def _build_context(
        self,
        game: NHLGame,
        *,
        season_id: int,
        team_profiles: dict[str, NHLTeamProfile],
        goalie_profiles: dict[int, NHLGoalieProfile],
    ) -> NHLMatchupContext:
        concerns: list[str] = []
        away_team_profile = team_profiles.get(
            normalize_nhl_abbreviation(game.away_team.abbreviation)
        )
        home_team_profile = team_profiles.get(
            normalize_nhl_abbreviation(game.home_team.abbreviation)
        )
        if away_team_profile is None:
            concerns.append("away_team_profile_missing")
        if home_team_profile is None:
            concerns.append("home_team_profile_missing")

        availability = self._load_availability(game)
        if availability is None:
            concerns.append("availability_unavailable")
            away_availability = None
            home_availability = None
            away_assignment = game.away_goalie_status
            home_assignment = game.home_goalie_status
        else:
            away_availability = availability
            home_availability = availability
            concerns.extend(availability.concerns)
            away_assignment = availability.away.goalie_assignment
            home_assignment = availability.home.goalie_assignment

        away_goalie_profile, away_goalie_concerns = _goalie_profile_for_assignment(
            away_assignment,
            goalie_profiles,
            side="away",
        )
        home_goalie_profile, home_goalie_concerns = _goalie_profile_for_assignment(
            home_assignment,
            goalie_profiles,
            side="home",
        )
        concerns.extend(away_goalie_concerns)
        concerns.extend(home_goalie_concerns)
        concerns.extend(game.source_state.concerns)

        return NHLMatchupContext(
            game=game,
            statistical_season_id=season_id,
            statistical_context="REQUESTED_SEASON",
            away_team_profile=away_team_profile,
            home_team_profile=home_team_profile,
            away_availability=away_availability,
            home_availability=home_availability,
            away_goalie_assignment=away_assignment,
            home_goalie_assignment=home_assignment,
            away_goalie_profile=away_goalie_profile,
            home_goalie_profile=home_goalie_profile,
            concerns=tuple(dict.fromkeys(concerns)),
        )

    def _load_availability(
        self,
        game: NHLGame,
    ) -> NHLGameAvailability | None:
        try:
            return self._availability_provider.load_game_availability(game)
        except Exception:
            return None


def build_nhl_matchup_contexts(
    target_date: str | date | None = None,
    *,
    game_loader: Callable[..., list[NHLGame]] = build_nhl_games,
    profile_service: NHLProfileServiceProtocol | None = None,
    availability_provider: NHLGameAvailabilityProvider | None = None,
) -> list[NHLMatchupContext]:
    games = game_loader(target_date)
    return NHLMatchupContextComposer(
        profile_service=profile_service,
        availability_provider=availability_provider,
    ).build_contexts(
        games,
        target_date=target_date,
    )


def statistical_season_id_for_game_date(
    game_date: str | date | datetime,
) -> int:
    parsed = _date_from_value(game_date)
    return current_nhl_season_id(parsed)


def _goalie_profile_for_assignment(
    assignment: NHLGoalieAssignment | None,
    profiles: dict[int, NHLGoalieProfile],
    *,
    side: str,
) -> tuple[NHLGoalieProfile | None, tuple[str, ...]]:
    if assignment is None:
        return None, (f"{side}_goalie_assignment_missing",)
    if assignment.status not in {CONFIRMED, PROJECTED}:
        return None, ()
    if assignment.player is None:
        return None, (f"{side}_goalie_identity_unresolved",)
    profile = profiles.get(assignment.player.source_player_id)
    if profile is None:
        return None, (f"{side}_goalie_profile_missing",)
    return profile, ()


def _context_date(
    target_date: str | date | None,
    fallback: datetime,
) -> date:
    if target_date is not None:
        return _date_from_value(target_date)
    return fallback.date()


def _date_from_value(
    value: str | date | datetime,
) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))

from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Any, Callable

from engine.nhl.models import (
    NHLGame,
    NHLGameSourceState,
    NHLTeam,
)
from engine.nhl.goalies import load_game_goalie_assignments
from engine.nhl.players import NHLRosterService
from engine.nhl.schedule import build_nhl_schedule
from engine.nhl.teams import load_nhl_teams, normalize_nhl_abbreviation


def build_nhl_games(
    target_date: str | date | None = None,
    *,
    raw_schedule: dict[str, Any] | None = None,
    teams: list[NHLTeam] | None = None,
    roster_service: NHLRosterService | None = None,
    goalie_status_loader: Callable[..., tuple] | None = (
        load_game_goalie_assignments
    ),
    team_loader: Callable[[], list[NHLTeam]] = load_nhl_teams,
) -> list[NHLGame]:
    schedule_games = build_nhl_schedule(
        target_date,
        raw_schedule=raw_schedule,
    )
    if not schedule_games:
        return []

    team_registry = _team_registry(
        teams
        if teams is not None
        else team_loader()
    )
    service = roster_service or NHLRosterService()
    attach_current_rosters = _should_attach_current_rosters(
        target_date
    )

    return [
        enrich_nhl_game(
            game,
            team_registry=team_registry,
            roster_service=service,
            goalie_status_loader=goalie_status_loader,
            attach_current_rosters=attach_current_rosters,
        )
        for game in schedule_games
    ]


def enrich_nhl_game(
    game: NHLGame,
    *,
    team_registry: dict[str, NHLTeam],
    roster_service: NHLRosterService,
    goalie_status_loader: Callable[..., tuple] | None = (
        load_game_goalie_assignments
    ),
    attach_current_rosters: bool = True,
) -> NHLGame:
    away_team = _canonical_team(
        game.away_team,
        team_registry,
    )
    home_team = _canonical_team(
        game.home_team,
        team_registry,
    )

    if not attach_current_rosters:
        enriched = replace(
            game,
            away_team=away_team,
            home_team=home_team,
            away_roster=(),
            home_roster=(),
            source_state=NHLGameSourceState(
                roster_context="CURRENT_ROSTER_OMITTED_HISTORICAL",
                away_roster_state="OMITTED_HISTORICAL",
                home_roster_state="OMITTED_HISTORICAL",
                concerns=(
                    "current_roster_not_attached_to_historical_game",
                ),
            ),
        )
        return _attach_goalie_status(
            enriched,
            goalie_status_loader,
        )

    away_roster = tuple(
        roster_service.load_team_roster(away_team)
    )
    home_roster = tuple(
        roster_service.load_team_roster(home_team)
    )
    concerns = []
    if not away_roster:
        concerns.append("away_roster_unavailable")
    if not home_roster:
        concerns.append("home_roster_unavailable")

    enriched = replace(
        game,
        away_team=away_team,
        home_team=home_team,
        away_roster=away_roster,
        home_roster=home_roster,
        source_state=NHLGameSourceState(
            roster_context="CURRENT_ROSTER",
            away_roster_state=(
                "LOADED"
                if away_roster
                else "UNAVAILABLE"
            ),
            home_roster_state=(
                "LOADED"
                if home_roster
                else "UNAVAILABLE"
            ),
            concerns=tuple(concerns),
        ),
    )
    return _attach_goalie_status(
        enriched,
        goalie_status_loader,
    )


def _attach_goalie_status(
    game: NHLGame,
    goalie_status_loader: Callable[..., tuple] | None,
) -> NHLGame:
    if goalie_status_loader is None:
        return game
    away_status, home_status = goalie_status_loader(game)
    return replace(
        game,
        away_goalie_status=away_status,
        home_goalie_status=home_status,
    )


def _team_registry(
    teams: list[NHLTeam],
) -> dict[str, NHLTeam]:
    return {
        team.abbreviation: team
        for team in teams
        if team.abbreviation
    }


def _canonical_team(
    team: NHLTeam,
    team_registry: dict[str, NHLTeam],
) -> NHLTeam:
    return team_registry.get(
        normalize_nhl_abbreviation(team.abbreviation),
        team,
    )


def _should_attach_current_rosters(
    target_date: str | date | None,
) -> bool:
    if target_date is None:
        return True
    parsed = _parse_schedule_date(target_date)
    if parsed is None:
        return True
    return parsed >= date.today()


def _parse_schedule_date(
    value: str | date,
) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None

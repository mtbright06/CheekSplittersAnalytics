from __future__ import annotations

from collections import defaultdict
from typing import Callable

from engine.nhl.models import (
    NHLGoalieProfile,
    NHLGoalieStats,
    NHLMoneyPuckGoalieStats,
    NHLMoneyPuckSkaterStats,
    NHLMoneyPuckTeamStats,
    NHLProfileSourceState,
    NHLSkaterProfile,
    NHLSkaterStats,
    NHLTeam,
    NHLTeamProfile,
    NHLTeamStats,
)
from engine.nhl.moneypuck import MoneyPuckProvider, SOURCE as MONEYPUCK_SOURCE
from engine.nhl.stats import NHLStatsProvider, SOURCE as NHL_STATS_SOURCE
from engine.nhl.stats import current_nhl_season_id
from engine.nhl.teams import load_nhl_teams, normalize_nhl_abbreviation


def official_to_moneypuck_season(season_id: int) -> int:
    text = str(int(season_id))
    if len(text) != 8:
        raise ValueError(f"invalid NHL season id: {season_id}")
    return int(text[:4])


def moneypuck_to_official_season(season: int) -> int:
    start = int(season)
    return int(f"{start}{start + 1}")


class NHLStatisticalProfileService:
    def __init__(
        self,
        *,
        official_provider: NHLStatsProvider | None = None,
        advanced_provider: MoneyPuckProvider | None = None,
        team_loader: Callable[[], list[NHLTeam]] = load_nhl_teams,
    ) -> None:
        self._official_provider = official_provider or NHLStatsProvider()
        self._advanced_provider = advanced_provider or MoneyPuckProvider()
        self._team_loader = team_loader

    def load_team_profiles(
        self,
        *,
        season_id: int | None = None,
        teams: list[NHLTeam] | None = None,
    ) -> list[NHLTeamProfile]:
        season = season_id or current_nhl_season_id()
        mp_season = official_to_moneypuck_season(season)
        registry = teams if teams is not None else self._safe_load_teams()
        by_id = {
            team.source_team_id: team
            for team in registry
            if team.source_team_id is not None
        }
        by_abbrev = {
            normalize_nhl_abbreviation(team.abbreviation): team
            for team in registry
            if team.abbreviation
        }
        official, official_failed = self._safe_official_teams(season)
        advanced, advanced_failed = self._safe_advanced_teams(mp_season)

        official_by_id = {row.team_id: row for row in official}
        advanced_by_abbrev = _team_advanced_by_abbreviation(advanced)
        keys = set(advanced_by_abbrev)
        keys.update(
            by_id[row.team_id].abbreviation
            for row in official
            if row.team_id in by_id
        )
        official_without_registry = {
            f"TEAM{row.team_id}": row
            for row in official
            if row.team_id not in by_id
        }
        keys.update(official_without_registry)
        profiles = []
        for abbreviation in sorted(keys):
            team = by_abbrev.get(abbreviation)
            official_row = (
                official_by_id.get(team.source_team_id)
                if team and team.source_team_id is not None
                else official_without_registry.get(abbreviation)
            )
            source_state = _source_state(
                official_row,
                bool(advanced_by_abbrev.get(abbreviation)),
                official_failed=official_failed,
                advanced_failed=advanced_failed,
                concerns=(
                    ()
                    if team
                    else ("team_identity_missing",)
                ),
            )
            profiles.append(
                NHLTeamProfile(
                    team_id=team.source_team_id if team else None,
                    abbreviation=abbreviation,
                    full_name=(
                        team.full_name
                        if team
                        else (official_row.team_name if official_row else abbreviation)
                    ),
                    season_id=season,
                    moneypuck_season=mp_season,
                    official=official_row,
                    advanced=advanced_by_abbrev.get(abbreviation, {}),
                    source_state=source_state,
                )
            )
        return profiles

    def load_skater_profiles(
        self,
        *,
        season_id: int | None = None,
    ) -> list[NHLSkaterProfile]:
        season = season_id or current_nhl_season_id()
        mp_season = official_to_moneypuck_season(season)
        official, official_failed = self._safe_official_skaters(season)
        advanced, advanced_failed = self._safe_advanced_skaters(mp_season)
        official_by_id = {row.player_id: row for row in official}
        advanced_by_id = _skater_advanced_by_player(advanced)
        profiles = []
        for player_id in sorted(set(official_by_id) | set(advanced_by_id)):
            official_row = official_by_id.get(player_id)
            advanced_rows = advanced_by_id.get(player_id, {})
            flat_advanced = [
                row
                for rows in advanced_rows.values()
                for row in rows
            ]
            profile = _build_skater_profile(
                player_id,
                season,
                mp_season,
                official_row,
                advanced_rows,
                flat_advanced,
                official_failed=official_failed,
                advanced_failed=advanced_failed,
            )
            profiles.append(profile)
        return profiles

    def load_goalie_profiles(
        self,
        *,
        season_id: int | None = None,
    ) -> list[NHLGoalieProfile]:
        season = season_id or current_nhl_season_id()
        mp_season = official_to_moneypuck_season(season)
        official, official_failed = self._safe_official_goalies(season)
        advanced, advanced_failed = self._safe_advanced_goalies(mp_season)
        official_by_id = {row.player_id: row for row in official}
        advanced_by_id = _goalie_advanced_by_player(advanced)
        profiles = []
        for player_id in sorted(set(official_by_id) | set(advanced_by_id)):
            official_row = official_by_id.get(player_id)
            advanced_rows = advanced_by_id.get(player_id, {})
            flat_advanced = [
                row
                for rows in advanced_rows.values()
                for row in rows
            ]
            profiles.append(
                _build_goalie_profile(
                    player_id,
                    season,
                    mp_season,
                    official_row,
                    advanced_rows,
                    flat_advanced,
                    official_failed=official_failed,
                    advanced_failed=advanced_failed,
                )
            )
        return profiles

    def _safe_load_teams(self) -> list[NHLTeam]:
        try:
            return self._team_loader()
        except Exception:
            return []

    def _safe_official_teams(
        self,
        season_id: int,
    ) -> tuple[list[NHLTeamStats], bool]:
        try:
            return self._official_provider.load_team_stats(season_id=season_id), False
        except Exception:
            return [], True

    def _safe_official_skaters(
        self,
        season_id: int,
    ) -> tuple[list[NHLSkaterStats], bool]:
        try:
            return self._official_provider.load_skater_stats(season_id=season_id), False
        except Exception:
            return [], True

    def _safe_official_goalies(
        self,
        season_id: int,
    ) -> tuple[list[NHLGoalieStats], bool]:
        try:
            return self._official_provider.load_goalie_stats(season_id=season_id), False
        except Exception:
            return [], True

    def _safe_advanced_teams(
        self,
        season: int,
    ) -> tuple[list[NHLMoneyPuckTeamStats], bool]:
        try:
            return self._advanced_provider.load_team_advanced_stats(
                season=season
            ), False
        except Exception:
            return [], True

    def _safe_advanced_skaters(
        self,
        season: int,
    ) -> tuple[list[NHLMoneyPuckSkaterStats], bool]:
        try:
            return self._advanced_provider.load_skater_advanced_stats(
                season=season
            ), False
        except Exception:
            return [], True

    def _safe_advanced_goalies(
        self,
        season: int,
    ) -> tuple[list[NHLMoneyPuckGoalieStats], bool]:
        try:
            return self._advanced_provider.load_goalie_advanced_stats(
                season=season
            ), False
        except Exception:
            return [], True


def _build_skater_profile(
    player_id: int,
    season_id: int,
    mp_season: int,
    official: NHLSkaterStats | None,
    advanced: dict[str, tuple[NHLMoneyPuckSkaterStats, ...]],
    flat_advanced: list[NHLMoneyPuckSkaterStats],
    *,
    official_failed: bool,
    advanced_failed: bool,
) -> NHLSkaterProfile:
    first_advanced = flat_advanced[0] if flat_advanced else None
    concerns = _player_concerns(
        official.team_abbreviations if official else None,
        [row.team_abbreviation for row in flat_advanced],
    )
    return NHLSkaterProfile(
        player_id=player_id,
        name=official.name if official else first_advanced.name,
        position=official.position if official else first_advanced.position,
        team_context=_team_context(
            official.team_abbreviations if official else None,
            [row.team_abbreviation for row in flat_advanced],
        ),
        season_id=season_id,
        moneypuck_season=mp_season,
        official=official,
        advanced=advanced,
        source_state=_source_state(
            official,
            bool(flat_advanced),
            official_failed=official_failed,
            advanced_failed=advanced_failed,
            concerns=concerns,
        ),
    )


def _build_goalie_profile(
    player_id: int,
    season_id: int,
    mp_season: int,
    official: NHLGoalieStats | None,
    advanced: dict[str, tuple[NHLMoneyPuckGoalieStats, ...]],
    flat_advanced: list[NHLMoneyPuckGoalieStats],
    *,
    official_failed: bool,
    advanced_failed: bool,
) -> NHLGoalieProfile:
    first_advanced = flat_advanced[0] if flat_advanced else None
    concerns = _player_concerns(
        official.team_abbreviations if official else None,
        [row.team_abbreviation for row in flat_advanced],
    )
    return NHLGoalieProfile(
        player_id=player_id,
        name=official.name if official else first_advanced.name,
        team_context=_team_context(
            official.team_abbreviations if official else None,
            [row.team_abbreviation for row in flat_advanced],
        ),
        season_id=season_id,
        moneypuck_season=mp_season,
        official=official,
        advanced=advanced,
        source_state=_source_state(
            official,
            bool(flat_advanced),
            official_failed=official_failed,
            advanced_failed=advanced_failed,
            concerns=concerns,
        ),
    )


def _team_advanced_by_abbreviation(
    rows: list[NHLMoneyPuckTeamStats],
) -> dict[str, dict[str, NHLMoneyPuckTeamStats]]:
    grouped: dict[str, dict[str, NHLMoneyPuckTeamStats]] = defaultdict(dict)
    for row in rows:
        grouped[row.team_abbreviation][row.situation] = row
    return dict(grouped)


def _skater_advanced_by_player(
    rows: list[NHLMoneyPuckSkaterStats],
) -> dict[int, dict[str, tuple[NHLMoneyPuckSkaterStats, ...]]]:
    return _advanced_by_player(rows)


def _goalie_advanced_by_player(
    rows: list[NHLMoneyPuckGoalieStats],
) -> dict[int, dict[str, tuple[NHLMoneyPuckGoalieStats, ...]]]:
    return _advanced_by_player(rows)


def _advanced_by_player(rows):
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row.player_id][row.situation].append(row)
    return {
        player_id: {
            situation: tuple(situation_rows)
            for situation, situation_rows in by_situation.items()
        }
        for player_id, by_situation in grouped.items()
    }


def _source_state(
    official_row,
    advanced_available: bool,
    *,
    official_failed: bool,
    advanced_failed: bool,
    concerns: tuple[str, ...] = (),
) -> NHLProfileSourceState:
    all_concerns = list(concerns)
    if official_failed:
        all_concerns.append("official_source_unavailable")
    elif official_row is None:
        all_concerns.append("official_stats_missing")
    if advanced_failed:
        all_concerns.append("advanced_source_unavailable")
    elif not advanced_available:
        all_concerns.append("advanced_stats_missing")
    return NHLProfileSourceState(
        official_available=official_row is not None,
        advanced_available=advanced_available,
        official_source=NHL_STATS_SOURCE if official_row is not None else None,
        advanced_source=MONEYPUCK_SOURCE if advanced_available else None,
        concerns=tuple(dict.fromkeys(all_concerns)),
    )


def _player_concerns(
    official_team_context: str | None,
    advanced_teams: list[str],
) -> tuple[str, ...]:
    concerns = []
    unique_advanced = {
        normalize_nhl_abbreviation(team)
        for team in advanced_teams
        if team
    }
    if len(unique_advanced) > 1:
        concerns.append("multi_team_advanced_context")
    official_teams = _team_tokens(official_team_context)
    if (
        official_teams
        and unique_advanced
        and not unique_advanced.issubset(official_teams)
    ):
        concerns.append("team_context_mismatch")
    return tuple(concerns)


def _team_context(
    official_team_context: str | None,
    advanced_teams: list[str],
) -> str | None:
    official_teams = sorted(_team_tokens(official_team_context))
    if official_teams:
        return ",".join(official_teams)
    unique_advanced = sorted(
        {
            normalize_nhl_abbreviation(team)
            for team in advanced_teams
            if team
        }
    )
    if unique_advanced:
        return ",".join(unique_advanced)
    return None


def _team_tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    return {
        normalize_nhl_abbreviation(token)
        for token in str(value).replace("/", ",").split(",")
        if normalize_nhl_abbreviation(token)
    }

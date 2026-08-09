from __future__ import annotations

from collections import Counter, defaultdict

from engine.nfl.models import (
    NFLDriveContext,
    NFLPlayer,
    NFLPlayerOpportunitySummary,
    NFLScoringOpportunity,
    NFLTeamOpportunitySummary,
)
from engine.nfl.teams import normalize_nfl_abbreviation


SOURCE = "nfl_opportunity_read_model"


def summarize_player_opportunities(
    opportunities: list[NFLScoringOpportunity] | None,
    *,
    season: int,
    week: int | None = None,
    game_id: str | None = None,
    team: str | None = None,
    player_id: str | None = None,
) -> list[NFLPlayerOpportunitySummary]:
    filtered = _filter_opportunities(
        opportunities or [],
        season=season,
        week=week,
        game_id=game_id,
        team=team,
        player_id=player_id,
    )
    buckets = defaultdict(list)
    for opportunity in filtered:
        if opportunity.play_type == "run" and opportunity.rusher_id:
            buckets[opportunity.rusher_id].append(("rush", opportunity))
        if opportunity.play_type == "pass" and opportunity.receiver_id:
            buckets[opportunity.receiver_id].append(("receive", opportunity))

    summaries = []
    for current_player_id, rows in buckets.items():
        player = _first_player(rows)
        summaries.append(
            NFLPlayerOpportunitySummary(
                player_id=current_player_id,
                player=player,
                team_abbreviation=_first_team(rows),
                season=season,
                week=week,
                games_represented=tuple(
                    sorted({opportunity.game_id for _, opportunity in rows})
                ),
                red_zone_rush_opportunities=_count(rows, "rush", "RED_ZONE"),
                inside_10_rush_opportunities=_count(rows, "rush", "INSIDE_10"),
                inside_5_rush_opportunities=_count(rows, "rush", "INSIDE_5"),
                red_zone_receiving_opportunities=_count(
                    rows,
                    "receive",
                    "RED_ZONE",
                ),
                inside_10_receiving_opportunities=_count(
                    rows,
                    "receive",
                    "INSIDE_10",
                ),
                inside_5_receiving_opportunities=_count(
                    rows,
                    "receive",
                    "INSIDE_5",
                ),
                rushing_touchdowns_from_qualified_events=_touchdowns(rows, "rush"),
                receiving_touchdowns_from_qualified_events=_touchdowns(
                    rows,
                    "receive",
                ),
            )
        )
    return sorted(
        summaries,
        key=lambda summary: (
            summary.team_abbreviation or "",
            summary.player_id,
        ),
    )


def summarize_team_opportunities(
    opportunities: list[NFLScoringOpportunity] | None,
    *,
    season: int,
    week: int | None = None,
    game_id: str | None = None,
    team: str | None = None,
    drives: list[NFLDriveContext] | None = None,
) -> list[NFLTeamOpportunitySummary]:
    filtered = _filter_opportunities(
        opportunities or [],
        season=season,
        week=week,
        game_id=game_id,
        team=team,
    )
    by_team = defaultdict(list)
    for opportunity in filtered:
        by_team[opportunity.offense_team].append(opportunity)

    drive_counts = _drive_counts_by_team(
        drives or [],
        season=season,
        week=week,
        game_id=game_id,
        team=team,
    )
    for team_key in drive_counts:
        by_team.setdefault(team_key, [])

    summaries = []
    for team_key, rows in by_team.items():
        summaries.append(
            NFLTeamOpportunitySummary(
                team_abbreviation=team_key,
                season=season,
                week=week,
                games_represented=tuple(
                    sorted(
                        {
                            row.game_id
                            for row in rows
                        }
                        | {
                            game
                            for game, _ in drive_counts.get(team_key, [])
                        }
                    )
                ),
                scoring_opportunities_20=sum(
                    "RED_ZONE" in row.scoring_zones for row in rows
                ),
                scoring_opportunities_10=sum(
                    "INSIDE_10" in row.scoring_zones for row in rows
                ),
                scoring_opportunities_5=sum(
                    "INSIDE_5" in row.scoring_zones for row in rows
                ),
                rush_opportunities=sum(row.play_type == "run" for row in rows),
                pass_opportunities=sum(row.play_type == "pass" for row in rows),
                touchdown_opportunities=sum(row.touchdown for row in rows),
                drive_result_counts=tuple(
                    sorted(
                        Counter(
                            result
                            for _, result in drive_counts.get(team_key, [])
                            if result
                        ).items()
                    )
                ),
            )
        )
    return sorted(summaries, key=lambda summary: summary.team_abbreviation)


def _filter_opportunities(
    opportunities: list[NFLScoringOpportunity],
    *,
    season: int,
    week: int | None,
    game_id: str | None,
    team: str | None,
    player_id: str | None = None,
) -> list[NFLScoringOpportunity]:
    requested_team = normalize_nfl_abbreviation(team) if team else None
    filtered = []
    for opportunity in opportunities:
        if opportunity.season != int(season):
            continue
        if week is not None and opportunity.week != int(week):
            continue
        if game_id and opportunity.game_id != game_id:
            continue
        if requested_team and opportunity.offense_team != requested_team:
            continue
        if player_id and player_id not in {
            opportunity.rusher_id,
            opportunity.receiver_id,
        }:
            continue
        filtered.append(opportunity)
    return filtered


def _drive_counts_by_team(
    drives: list[NFLDriveContext],
    *,
    season: int,
    week: int | None,
    game_id: str | None,
    team: str | None,
) -> dict[str, list[tuple[str, str | None]]]:
    requested_team = normalize_nfl_abbreviation(team) if team else None
    by_team = defaultdict(list)
    for drive in drives:
        if drive.season != int(season):
            continue
        if week is not None and drive.week != int(week):
            continue
        if game_id and drive.game_id != game_id:
            continue
        if not drive.possession_team:
            continue
        if requested_team and drive.possession_team != requested_team:
            continue
        by_team[drive.possession_team].append((drive.game_id, drive.drive_result))
    return by_team


def _count(
    rows: list[tuple[str, NFLScoringOpportunity]],
    kind: str,
    zone: str,
) -> int:
    return sum(
        row_kind == kind and zone in opportunity.scoring_zones
        for row_kind, opportunity in rows
    )


def _touchdowns(
    rows: list[tuple[str, NFLScoringOpportunity]],
    kind: str,
) -> int:
    return sum(
        row_kind == kind and opportunity.touchdown
        for row_kind, opportunity in rows
    )


def _first_player(
    rows: list[tuple[str, NFLScoringOpportunity]],
) -> NFLPlayer | None:
    for kind, opportunity in rows:
        if kind == "rush" and opportunity.rusher:
            return opportunity.rusher
        if kind == "receive" and opportunity.receiver:
            return opportunity.receiver
    return None


def _first_team(
    rows: list[tuple[str, NFLScoringOpportunity]],
) -> str | None:
    for _, opportunity in rows:
        if opportunity.offense_team:
            return opportunity.offense_team
    return None

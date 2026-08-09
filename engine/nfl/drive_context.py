from __future__ import annotations

from collections import defaultdict

from engine.nfl.models import NFLDriveContext, NFLPlay, NFLScoringOpportunity
from engine.nfl.play_by_play import NFLPlayByPlayProvider
from engine.nfl.scoring_opportunities import normalize_scoring_opportunities
from engine.nfl.teams import normalize_nfl_abbreviation


SOURCE = "nfl_drive_context"


def build_nfl_drive_contexts(
    *,
    season: int,
    week: int | None = None,
    game_id: str | None = None,
    team: str | None = None,
    plays: list[NFLPlay] | None = None,
    provider: NFLPlayByPlayProvider | None = None,
) -> list[NFLDriveContext]:
    selected_plays = plays
    if selected_plays is None:
        selected_plays = (provider or NFLPlayByPlayProvider()).load_plays(
            season=season,
            week=week,
            game_id=game_id,
            team=team,
        )
    contexts = normalize_drive_contexts(selected_plays)
    return _filter_contexts(
        contexts,
        season=season,
        week=week,
        game_id=game_id,
        team=team,
    )


def normalize_drive_contexts(
    plays: list[NFLPlay] | None,
    *,
    scoring_opportunities: list[NFLScoringOpportunity] | None = None,
) -> list[NFLDriveContext]:
    grouped: dict[tuple[str, int], list[NFLPlay]] = defaultdict(list)
    for play in plays or []:
        if play.drive_id is None:
            continue
        grouped[(play.game_id, play.drive_id)].append(play)

    opportunity_ids = _scoring_opportunity_ids(
        scoring_opportunities
        if scoring_opportunities is not None
        else normalize_scoring_opportunities(plays or [])
    )
    contexts = []
    for (game_id, drive_id), drive_plays in grouped.items():
        ordered_plays = sorted(drive_plays, key=lambda play: play.play_id)
        first = ordered_plays[0]
        drive_play_ids = tuple(play.play_id for play in ordered_plays)
        contexts.append(
            NFLDriveContext(
                game_id=game_id,
                drive_id=drive_id,
                season=first.season,
                week=first.week,
                game_type=first.season_type,
                possession_team=_first_present(
                    play.possession_team for play in ordered_plays
                ),
                defensive_team=_first_present(
                    play.defensive_team for play in ordered_plays
                ),
                start_quarter=first.drive_quarter_start,
                end_quarter=first.drive_quarter_end,
                start_yard_line=first.drive_start_yard_line,
                end_yard_line=first.drive_end_yard_line,
                play_count=first.drive_play_count or len(ordered_plays),
                drive_result=first.drive_result,
                play_ids=drive_play_ids,
                scoring_opportunity_play_ids=tuple(
                    play_id
                    for play_id in drive_play_ids
                    if (game_id, drive_id, play_id) in opportunity_ids
                ),
                concerns=_drive_concerns(ordered_plays),
            )
        )
    return sorted(
        contexts,
        key=lambda context: (
            context.season,
            context.week,
            context.game_id,
            context.drive_id,
        ),
    )


def _filter_contexts(
    contexts: list[NFLDriveContext],
    *,
    season: int,
    week: int | None,
    game_id: str | None,
    team: str | None,
) -> list[NFLDriveContext]:
    requested_team = normalize_nfl_abbreviation(team) if team else None
    filtered = []
    for context in contexts:
        if context.season != int(season):
            continue
        if week is not None and context.week != int(week):
            continue
        if game_id and context.game_id != game_id:
            continue
        if requested_team and requested_team not in {
            context.possession_team,
            context.defensive_team,
        }:
            continue
        filtered.append(context)
    return filtered


def _scoring_opportunity_ids(
    opportunities: list[NFLScoringOpportunity],
) -> set[tuple[str, int, int]]:
    return {
        (opportunity.game_id, opportunity.drive_id, opportunity.play_id)
        for opportunity in opportunities
        if opportunity.drive_id is not None
    }


def _first_present(values) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _drive_concerns(
    plays: list[NFLPlay],
) -> tuple[str, ...]:
    concerns = []
    first = plays[0]
    if first.possession_team is None:
        concerns.append("drive_possession_team_missing")
    if first.drive_result is None:
        concerns.append("drive_result_missing")
    if first.drive_quarter_start is None:
        concerns.append("drive_start_quarter_missing")
    if first.drive_quarter_end is None:
        concerns.append("drive_end_quarter_missing")
    return tuple(concerns)

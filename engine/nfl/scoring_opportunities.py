from __future__ import annotations

from engine.nfl.models import NFLPlay, NFLScoringOpportunity
from engine.nfl.play_by_play import NFLPlayByPlayProvider
from engine.nfl.teams import normalize_nfl_abbreviation


SCORING_SOURCE = "nfl_scoring_opportunities"
SCRIMMAGE_PLAY_TYPES = {"pass", "run"}
EXCLUDED_PLAY_TYPES = {
    "extra_point",
    "field_goal",
    "kickoff",
    "no_play",
    "punt",
    "qb_kneel",
    "qb_spike",
    "timeout",
}


def build_nfl_scoring_opportunities(
    *,
    season: int,
    week: int | None = None,
    game_id: str | None = None,
    team: str | None = None,
    player_id: str | None = None,
    scoring_zone: str | None = None,
    plays: list[NFLPlay] | None = None,
    provider: NFLPlayByPlayProvider | None = None,
) -> list[NFLScoringOpportunity]:
    selected_plays = plays
    if selected_plays is None:
        selected_plays = (provider or NFLPlayByPlayProvider()).load_plays(
            season=season,
            week=week,
            game_id=game_id,
            team=team,
        )
    opportunities = normalize_scoring_opportunities(selected_plays)
    return _filter_opportunities(
        opportunities,
        season=season,
        week=week,
        game_id=game_id,
        team=team,
        player_id=player_id,
        scoring_zone=scoring_zone,
    )


def normalize_scoring_opportunities(
    plays: list[NFLPlay] | None,
) -> list[NFLScoringOpportunity]:
    opportunities = []
    for play in plays or []:
        opportunity = scoring_opportunity_from_play(play)
        if opportunity is not None:
            opportunities.append(opportunity)
    return sorted(
        opportunities,
        key=lambda opportunity: (
            opportunity.season,
            opportunity.week,
            opportunity.game_id,
            opportunity.play_id,
        ),
    )


def scoring_opportunity_from_play(
    play: NFLPlay,
) -> NFLScoringOpportunity | None:
    if not _qualifies_as_offensive_scrimmage_play(play):
        return None
    zones = _scoring_zones(play.yardline_100)
    if not zones:
        return None
    concerns = []
    if play.play_type == "run" and play.rusher_id is None:
        concerns.append("rusher_identity_missing")
    if play.play_type == "pass" and play.passer_id is None:
        concerns.append("passer_identity_missing")
    return NFLScoringOpportunity(
        game_id=play.game_id,
        play_id=play.play_id,
        drive_id=play.drive_id,
        season=play.season,
        week=play.week,
        offense_team=play.possession_team,
        defense_team=play.defensive_team,
        yardline_100=play.yardline_100,
        scoring_zones=zones,
        play_type=play.play_type,
        down=play.down,
        yards_to_go=play.yards_to_go,
        touchdown=play.touchdown,
        passer_id=play.passer_id,
        passer=play.passer,
        rusher_id=play.rusher_id,
        rusher=play.rusher,
        receiver_id=play.receiver_id,
        receiver=play.receiver,
        concerns=tuple(dict.fromkeys(play.concerns + tuple(concerns))),
    )


def _qualifies_as_offensive_scrimmage_play(
    play: NFLPlay,
) -> bool:
    if play.possession_team is None:
        return False
    if play.yardline_100 is None or play.yardline_100 < 0:
        return False
    play_type = play.play_type
    if play_type is None or play_type in EXCLUDED_PLAY_TYPES:
        return False
    return play_type in SCRIMMAGE_PLAY_TYPES


def _scoring_zones(
    yardline_100: int | None,
) -> tuple[str, ...]:
    if yardline_100 is None or yardline_100 > 20:
        return ()
    zones = ["RED_ZONE"]
    if yardline_100 <= 10:
        zones.append("INSIDE_10")
    if yardline_100 <= 5:
        zones.append("INSIDE_5")
    return tuple(zones)


def _filter_opportunities(
    opportunities: list[NFLScoringOpportunity],
    *,
    season: int,
    week: int | None,
    game_id: str | None,
    team: str | None,
    player_id: str | None,
    scoring_zone: str | None,
) -> list[NFLScoringOpportunity]:
    requested_team = normalize_nfl_abbreviation(team) if team else None
    requested_zone = scoring_zone.upper() if scoring_zone else None
    filtered = []
    for opportunity in opportunities:
        if opportunity.season != int(season):
            continue
        if week is not None and opportunity.week != int(week):
            continue
        if game_id and opportunity.game_id != game_id:
            continue
        if requested_team and requested_team not in {
            opportunity.offense_team,
            opportunity.defense_team,
        }:
            continue
        if requested_zone and requested_zone not in opportunity.scoring_zones:
            continue
        if player_id and player_id not in {
            opportunity.passer_id,
            opportunity.rusher_id,
            opportunity.receiver_id,
        }:
            continue
        filtered.append(opportunity)
    return filtered

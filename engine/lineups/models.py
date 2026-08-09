from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class GameLineupStatus(StrEnum):
    UNKNOWN = "UNKNOWN"
    NOT_POSTED = "NOT_POSTED"
    PARTIAL = "PARTIAL"
    CONFIRMED = "CONFIRMED"
    UPDATED = "UPDATED"


class PlayerLineupStatus(StrEnum):
    CONFIRMED_STARTER = "CONFIRMED_STARTER"
    BENCH = "BENCH"
    NOT_LISTED = "NOT_LISTED"
    UNKNOWN = "UNKNOWN"


class LineupActionability(StrEnum):
    ACTIONABLE = "ACTIONABLE"
    PENDING_LINEUP = "PENDING_LINEUP"
    NOT_STARTING = "NOT_STARTING"
    SOURCE_UNKNOWN = "SOURCE_UNKNOWN"


@dataclass(frozen=True)
class LineupPlayer:
    player_id: int | None
    player_name: str | None
    team_id: int | None
    team_name: str | None
    side: str
    lineup_status: PlayerLineupStatus
    batting_order: int | None = None
    position: str | None = None


@dataclass(frozen=True)
class TeamLineup:
    team_id: int | None
    team_name: str | None
    side: str
    status: GameLineupStatus
    starters: tuple[LineupPlayer, ...] = ()
    bench: tuple[LineupPlayer, ...] = ()
    concerns: tuple[str, ...] = ()

    def player_status(self, player_id: int | None) -> LineupPlayer:
        if player_id is None:
            return LineupPlayer(
                player_id=None,
                player_name=None,
                team_id=self.team_id,
                team_name=self.team_name,
                side=self.side,
                lineup_status=PlayerLineupStatus.UNKNOWN,
            )

        if self.status == GameLineupStatus.NOT_POSTED:
            return LineupPlayer(
                player_id=player_id,
                player_name=None,
                team_id=self.team_id,
                team_name=self.team_name,
                side=self.side,
                lineup_status=PlayerLineupStatus.UNKNOWN,
            )

        for player in self.starters:
            if player.player_id == player_id:
                return player

        for player in self.bench:
            if player.player_id == player_id:
                return player

        if self.status in {
            GameLineupStatus.CONFIRMED,
            GameLineupStatus.UPDATED,
        }:
            lineup_status = PlayerLineupStatus.NOT_LISTED
        elif self.status == GameLineupStatus.NOT_POSTED:
            lineup_status = PlayerLineupStatus.UNKNOWN
        else:
            lineup_status = PlayerLineupStatus.UNKNOWN

        return LineupPlayer(
            player_id=player_id,
            player_name=None,
            team_id=self.team_id,
            team_name=self.team_name,
            side=self.side,
            lineup_status=lineup_status,
        )


@dataclass(frozen=True)
class GameLineupState:
    game_id: int | None
    away_team: str | None
    home_team: str | None
    status: GameLineupStatus
    source: str
    retrieved_at: datetime
    game_status: str | None = None
    source_timestamp: str | None = None
    away_lineup: TeamLineup | None = None
    home_lineup: TeamLineup | None = None
    concerns: tuple[str, ...] = ()
    previous_signature: tuple | None = None
    signature: tuple | None = None
    stale_after_seconds: int = 600

    @property
    def freshness_seconds(self) -> float:
        return max(
            0.0,
            (datetime.now(UTC) - self.retrieved_at).total_seconds(),
        )

    @property
    def is_stale(self) -> bool:
        return self.freshness_seconds > self.stale_after_seconds

    def team_lineup(self, team_id: int | None) -> TeamLineup | None:
        for lineup in (self.away_lineup, self.home_lineup):
            if lineup and lineup.team_id == team_id:
                return lineup
        return None


def unknown_lineup_state(
    game_id: int | None,
    concern: str,
    *,
    source: str = "mlb_statsapi_feed_live",
) -> GameLineupState:
    now = datetime.now(UTC)
    return GameLineupState(
        game_id=game_id,
        away_team=None,
        home_team=None,
        status=GameLineupStatus.UNKNOWN,
        source=source,
        retrieved_at=now,
        concerns=(concern,),
    )

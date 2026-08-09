"""Recommendation Episode lifecycle management."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ModelVersion, Recommendation
from app.models.recommendation_episode import (
    RecommendationEpisode,
    RecommendationEpisodeClosureReason,
    RecommendationEpisodeStatus,
    RecommendationStream,
)
from app.services.prediction_snapshot_service import PredictionSnapshot


LOGGER = logging.getLogger(__name__)

PASS_RECOMMENDATIONS = {"PASS", "NO PLAY", "NO_PLAY", "NONE"}
TOTAL_MARKETS = {"TOTAL", "TOTALS", "GAME_TOTAL", "GAME_TOTALS"}


@dataclass(frozen=True, slots=True)
class EpisodeLifecycleResult:
    action: str
    stream_id: UUID | None
    episode_id: UUID | None


class RecommendationEpisodeService:
    """Attaches immutable snapshots to evolving recommendation episodes."""

    def process_snapshot(
        self,
        *,
        session: Session,
        model_version: ModelVersion,
        recommendation: Recommendation,
        snapshot: PredictionSnapshot,
        pregame_eligible: bool = True,
    ) -> EpisodeLifecycleResult:
        if not pregame_eligible:
            LOGGER.info("Episode skipped: ineligible snapshot")
            return EpisodeLifecycleResult("skipped_ineligible", None, None)

        stream = self._get_or_create_stream(session, model_version, snapshot)
        active = self._active_episode(session, stream.id)
        actionable = _is_actionable(snapshot.prediction.recommendation)

        if not actionable:
            if active is None:
                LOGGER.info("Episode skipped: pass without active episode")
                return EpisodeLifecycleResult("pass_no_active", stream.id, None)
            self._withdraw_episode(active, snapshot.run.build_timestamp)
            session.flush()
            recommendation.recommendation_episode_id = active.id
            LOGGER.info("Episode withdrawn")
            LOGGER.info("Snapshot attached")
            return EpisodeLifecycleResult("withdrawn", stream.id, active.id)

        selection = _episode_selection(snapshot)
        selection_side = snapshot.identity.selection_side or ""
        market_line = _decimal_or_none(snapshot.market.market_line)

        if active is None:
            episode = self._create_episode(
                session,
                stream,
                selection=selection,
                selection_side=selection_side,
                market_line=market_line,
                opened_at=snapshot.run.build_timestamp,
            )
            recommendation.recommendation_episode_id = episode.id
            LOGGER.info("Episode created")
            LOGGER.info("Snapshot attached")
            return EpisodeLifecycleResult("created", stream.id, episode.id)

        if _same_action(active, selection, selection_side):
            active.market_line = market_line
            recommendation.recommendation_episode_id = active.id
            LOGGER.info("Episode updated")
            LOGGER.info("Snapshot attached")
            return EpisodeLifecycleResult("attached", stream.id, active.id)

        self._supersede_episode(active, snapshot.run.build_timestamp)
        session.flush()
        episode = self._create_episode(
            session,
            stream,
            selection=selection,
            selection_side=selection_side,
            market_line=market_line,
            opened_at=snapshot.run.build_timestamp,
        )
        active.superseded_by_episode_id = episode.id
        recommendation.recommendation_episode_id = episode.id
        LOGGER.info("Episode superseded")
        LOGGER.info("Episode created")
        LOGGER.info("Snapshot attached")
        return EpisodeLifecycleResult("superseded", stream.id, episode.id)

    def _get_or_create_stream(
        self,
        session: Session,
        model_version: ModelVersion,
        snapshot: PredictionSnapshot,
    ) -> RecommendationStream:
        provider = _provider(snapshot)
        existing = session.execute(
            select(RecommendationStream).where(
                RecommendationStream.sport == snapshot.identity.sport.upper(),
                RecommendationStream.league_code == snapshot.identity.league.upper(),
                RecommendationStream.provider == provider,
                RecommendationStream.provider_game_id == snapshot.identity.provider_game_id,
                RecommendationStream.market == snapshot.identity.market.upper(),
                RecommendationStream.model_version == model_version.version,
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.scheduled_start_at is None:
                existing.scheduled_start_at = snapshot.identity.scheduled_start_at_prediction
            return existing

        stream = RecommendationStream(
            sport=snapshot.identity.sport.upper(),
            league_code=snapshot.identity.league.upper(),
            provider=provider,
            provider_game_id=snapshot.identity.provider_game_id,
            market=snapshot.identity.market.upper(),
            model_version=model_version.version,
            model_version_id=model_version.id,
            scheduled_start_at=snapshot.identity.scheduled_start_at_prediction,
        )
        session.add(stream)
        session.flush()
        return stream

    def _active_episode(
        self,
        session: Session,
        stream_id: UUID,
    ) -> RecommendationEpisode | None:
        return session.execute(
            select(RecommendationEpisode).where(
                RecommendationEpisode.recommendation_stream_id == stream_id,
                RecommendationEpisode.status == RecommendationEpisodeStatus.ACTIVE.value,
            ).with_for_update()
        ).scalar_one_or_none()

    def _create_episode(
        self,
        session: Session,
        stream: RecommendationStream,
        *,
        selection: str,
        selection_side: str,
        market_line: Decimal | None,
        opened_at: datetime,
    ) -> RecommendationEpisode:
        episode = RecommendationEpisode(
            stream=stream,
            selection=selection,
            selection_side=selection_side,
            market_line=market_line,
            status=RecommendationEpisodeStatus.ACTIVE.value,
            opened_at=opened_at,
        )
        session.add(episode)
        session.flush()
        return episode

    @staticmethod
    def _supersede_episode(
        episode: RecommendationEpisode,
        closed_at: datetime,
    ) -> None:
        episode.status = RecommendationEpisodeStatus.SUPERSEDED.value
        episode.closed_at = closed_at
        episode.closure_reason = RecommendationEpisodeClosureReason.SELECTION_CHANGED.value

    @staticmethod
    def _withdraw_episode(
        episode: RecommendationEpisode,
        closed_at: datetime,
    ) -> None:
        episode.status = RecommendationEpisodeStatus.WITHDRAWN.value
        episode.closed_at = closed_at
        episode.closure_reason = (
            RecommendationEpisodeClosureReason.RECOMMENDATION_WITHDRAWN_PASS.value
        )


def _is_actionable(value: str | None) -> bool:
    normalized = _normalize(value)
    return bool(normalized and normalized not in PASS_RECOMMENDATIONS)


def _same_action(
    episode: RecommendationEpisode,
    selection: str,
    selection_side: str,
) -> bool:
    return (
        _normalize(episode.selection) == _normalize(selection)
        and _normalize(episode.selection_side) == _normalize(selection_side)
    )


def _episode_selection(snapshot: PredictionSnapshot) -> str:
    selection = _normalize(snapshot.identity.selection)
    if _normalize(snapshot.identity.market) not in TOTAL_MARKETS:
        return selection
    first_token = selection.split(" ", 1)[0] if selection else ""
    if first_token in {"OVER", "UNDER"}:
        return first_token
    return selection


def _provider(snapshot: PredictionSnapshot) -> str:
    components_provider = _nested_text(snapshot.components, ("identity", "provider"))
    if components_provider:
        return components_provider
    if snapshot.identity.league.upper() == "MLB":
        return "mlb_stats_api"
    return snapshot.run.source


def _nested_text(value: Any, path: tuple[str, ...]) -> str | None:
    current = value
    for key in path:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    normalized = str(current or "").strip()
    return normalized or None


def _decimal_or_none(value: float | None) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _normalize(value: object) -> str:
    return " ".join(str(value or "").strip().upper().split())

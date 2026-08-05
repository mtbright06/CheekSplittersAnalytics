"""
SharpStack persistence models.

Importing this package registers every ORM model with Base.metadata.
"""

from app.models.active_recommendation_slot import ActiveRecommendationSlot
from app.models.game import Game
from app.models.game_result import GameResult
from app.models.legacy_recommendation_settlement import LegacyRecommendationSettlement
from app.models.league import League
from app.models.model_run import ModelRun
from app.models.model_version import ModelVersion
from app.models.recommendation import Recommendation
from app.models.recommendation_activation_event import RecommendationActivationEvent
from app.models.recommendation_episode import (
    CanonicalRecommendationGrade,
    RecommendationEpisode,
    RecommendationEpisodeClosureReason,
    RecommendationEpisodeStatus,
    RecommendationStream,
)
from app.models.recommendation_grade import RecommendationGrade
from app.models.reference_price import ReferencePrice
from app.models.team import Team

__all__ = [
    "ActiveRecommendationSlot",
    "Game",
    "GameResult",
    "LegacyRecommendationSettlement",
    "League",
    "ModelRun",
    "ModelVersion",
    "Recommendation",
    "RecommendationActivationEvent",
    "CanonicalRecommendationGrade",
    "RecommendationEpisode",
    "RecommendationEpisodeClosureReason",
    "RecommendationEpisodeStatus",
    "RecommendationStream",
    "RecommendationGrade",
    "ReferencePrice",
    "Team",
]

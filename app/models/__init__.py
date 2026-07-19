"""
SharpStack persistence models.

Importing this package registers every ORM model with Base.metadata.
"""

from app.models.game import Game
from app.models.league import League
from app.models.model_run import ModelRun
from app.models.model_version import ModelVersion
from app.models.recommendation import Recommendation
from app.models.team import Team

__all__ = [
    "Game",
    "League",
    "ModelRun",
    "ModelVersion",
    "Recommendation",
    "Team",
]

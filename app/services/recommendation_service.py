from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Iterable, Sequence
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.database.session import SessionLocal
from app.models import (
    Game,
    League,
    ModelRun,
    ModelVersion,
    Recommendation,
    Team,
)


class RecommendationServiceError(RuntimeError):
    """Base error for recommendation persistence failures."""


class RecommendationValidationError(RecommendationServiceError):
    """Raised when input data is invalid before database work begins."""


@dataclass(frozen=True, slots=True)
class TeamInput:
    code: str
    name: str
    city: str | None = None
    external_team_id: str | None = None

    def normalized_code(self) -> str:
        return self.code.strip().upper()

    def normalized_name(self) -> str:
        return self.name.strip()


@dataclass(frozen=True, slots=True)
class GameInput:
    league_code: str
    league_name: str
    sport: str
    external_game_id: str
    scheduled_start: datetime
    home_team: TeamInput
    away_team: TeamInput
    league_country: str | None = None
    status: str = "scheduled"
    venue: str | None = None

    def normalized_league_code(self) -> str:
        return self.league_code.strip().upper()


@dataclass(frozen=True, slots=True)
class ModelIdentity:
    model_name: str
    version: str
    git_commit: str | None = None
    description: str | None = None


@dataclass(frozen=True, slots=True)
class RecommendationInput:
    market_type: str
    selection: str
    projection: Decimal | int | float | str
    confidence: Decimal | int | float | str
    market_line: Decimal | int | float | str | None = None
    edge: Decimal | int | float | str | None = None
    components: dict[str, Any] = field(default_factory=dict)
    explanation: str | None = None
    source: str = "sharpstack"
    recommendation_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class SavedRecommendation:
    recommendation_id: UUID
    game_id: UUID
    model_run_id: UUID
    market_type: str
    selection: str
    projection: Decimal
    confidence: Decimal


@dataclass(frozen=True, slots=True)
class SavedRecommendationBatch:
    model_run_id: UUID
    model_version_id: UUID
    game_id: UUID
    recommendation_ids: tuple[UUID, ...]
    recommendation_count: int
    started_at: datetime
    completed_at: datetime
    status: str


class RecommendationService:
    """
    Persists SharpStack model runs and recommendations.

    The prediction engine should not import this service or SQLAlchemy models.
    An integration layer may convert engine results into the input dataclasses
    defined in this module and call this service afterward.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session] = SessionLocal,
    ) -> None:
        self._session_factory = session_factory

    def save_batch(
        self,
        *,
        game: GameInput,
        model: ModelIdentity,
        recommendations: Sequence[RecommendationInput],
        run_label: str | None = None,
        run_metadata: dict[str, Any] | None = None,
        run_notes: str | None = None,
        run_source: str = "sharpstack",
        started_at: datetime | None = None,
    ) -> SavedRecommendationBatch:
        """
        Save a complete model run and its recommendations atomically.

        All records commit together. If any operation fails, the transaction
        rolls back and no partial recommendation batch remains.
        """

        self._validate_game(game)
        self._validate_model(model)
        self._validate_recommendations(recommendations)

        normalized_started_at = self._ensure_aware_datetime(
            started_at or datetime.now(UTC)
        )

        session = self._session_factory()
        model_run: ModelRun | None = None

        try:
            league = self._get_or_create_league(
                session=session,
                game_input=game,
            )

            home_team = self._get_or_create_team(
                session=session,
                league=league,
                team_input=game.home_team,
            )

            away_team = self._get_or_create_team(
                session=session,
                league=league,
                team_input=game.away_team,
            )

            if home_team.id == away_team.id:
                raise RecommendationValidationError(
                    "Home and away teams must be different."
                )

            game_record = self._get_or_create_game(
                session=session,
                league=league,
                home_team=home_team,
                away_team=away_team,
                game_input=game,
            )

            model_version = self._get_or_create_model_version(
                session=session,
                model=model,
            )

            model_run = ModelRun(
                model_version_id=model_version.id,
                started_at=normalized_started_at,
                completed_at=None,
                status="running",
                source=self._clean_required(run_source, "run_source"),
                run_label=self._clean_optional(run_label),
                notes=self._clean_optional(run_notes),
                run_metadata=dict(run_metadata or {}),
            )

            session.add(model_run)
            session.flush()

            saved_recommendations: list[Recommendation] = []

            for recommendation_input in recommendations:
                recommendation = self._build_recommendation(
                    game_record=game_record,
                    model_version=model_version,
                    model_run=model_run,
                    recommendation_input=recommendation_input,
                )

                session.add(recommendation)
                saved_recommendations.append(recommendation)

            session.flush()

            completed_at = datetime.now(UTC)
            model_run.completed_at = completed_at
            model_run.status = "completed"

            session.commit()

            return SavedRecommendationBatch(
                model_run_id=model_run.id,
                model_version_id=model_version.id,
                game_id=game_record.id,
                recommendation_ids=tuple(
                    recommendation.id
                    for recommendation in saved_recommendations
                ),
                recommendation_count=len(saved_recommendations),
                started_at=model_run.started_at,
                completed_at=completed_at,
                status=model_run.status,
            )

        except RecommendationServiceError:
            session.rollback()
            raise

        except SQLAlchemyError as exc:
            session.rollback()

            raise RecommendationServiceError(
                "Database operation failed while saving recommendations."
            ) from exc

        except Exception as exc:
            session.rollback()

            raise RecommendationServiceError(
                "Unexpected failure while saving recommendations."
            ) from exc

        finally:
            session.close()

    def save_one(
        self,
        *,
        game: GameInput,
        model: ModelIdentity,
        recommendation: RecommendationInput,
        run_label: str | None = None,
        run_metadata: dict[str, Any] | None = None,
        run_notes: str | None = None,
        run_source: str = "sharpstack",
        started_at: datetime | None = None,
    ) -> SavedRecommendationBatch:
        """Convenience wrapper for saving a single recommendation."""

        return self.save_batch(
            game=game,
            model=model,
            recommendations=[recommendation],
            run_label=run_label,
            run_metadata=run_metadata,
            run_notes=run_notes,
            run_source=run_source,
            started_at=started_at,
        )

    def _get_or_create_league(
        self,
        *,
        session: Session,
        game_input: GameInput,
    ) -> League:
        league_code = game_input.normalized_league_code()

        statement = select(League).where(
            League.code == league_code
        )

        league = session.execute(statement).scalar_one_or_none()

        if league is not None:
            changed = False

            league_name = self._clean_required(
                game_input.league_name,
                "league_name",
            )

            sport = self._clean_required(
                game_input.sport,
                "sport",
            )

            country = self._clean_optional(
                game_input.league_country
            )

            if league.name != league_name:
                league.name = league_name
                changed = True

            if league.sport != sport:
                league.sport = sport
                changed = True

            if country is not None and league.country != country:
                league.country = country
                changed = True

            if changed:
                session.flush()

            return league

        league = League(
            code=league_code,
            name=self._clean_required(
                game_input.league_name,
                "league_name",
            ),
            sport=self._clean_required(
                game_input.sport,
                "sport",
            ),
            country=self._clean_optional(
                game_input.league_country
            ),
        )

        session.add(league)
        session.flush()

        return league

    def _get_or_create_team(
        self,
        *,
        session: Session,
        league: League,
        team_input: TeamInput,
    ) -> Team:
        team_code = team_input.normalized_code()
        external_team_id = self._clean_optional(
            team_input.external_team_id
        )

        team: Team | None = None

        if external_team_id is not None:
            statement = select(Team).where(
                Team.league_id == league.id,
                Team.external_team_id == external_team_id,
            )

            team = session.execute(
                statement
            ).scalar_one_or_none()

        if team is None:
            statement = select(Team).where(
                Team.league_id == league.id,
                Team.code == team_code,
            )

            team = session.execute(
                statement
            ).scalar_one_or_none()

        if team is not None:
            team.name = self._clean_required(
                team_input.name,
                "team.name",
            )
            team.city = self._clean_optional(team_input.city)

            if external_team_id is not None:
                team.external_team_id = external_team_id

            session.flush()
            return team

        team = Team(
            league_id=league.id,
            code=team_code,
            name=self._clean_required(
                team_input.name,
                "team.name",
            ),
            city=self._clean_optional(team_input.city),
            external_team_id=external_team_id,
        )

        session.add(team)
        session.flush()

        return team

    def _get_or_create_game(
        self,
        *,
        session: Session,
        league: League,
        home_team: Team,
        away_team: Team,
        game_input: GameInput,
    ) -> Game:
        external_game_id = self._clean_required(
            game_input.external_game_id,
            "external_game_id",
        )

        statement = select(Game).where(
            Game.league_id == league.id,
            Game.external_game_id == external_game_id,
        )

        game_record = session.execute(
            statement
        ).scalar_one_or_none()

        scheduled_start = self._ensure_aware_datetime(
            game_input.scheduled_start
        )

        if game_record is not None:
            game_record.scheduled_start = scheduled_start
            game_record.home_team_id = home_team.id
            game_record.away_team_id = away_team.id
            game_record.status = self._clean_required(
                game_input.status,
                "game.status",
            )
            game_record.venue = self._clean_optional(
                game_input.venue
            )

            session.flush()
            return game_record

        game_record = Game(
            league_id=league.id,
            external_game_id=external_game_id,
            scheduled_start=scheduled_start,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            status=self._clean_required(
                game_input.status,
                "game.status",
            ),
            venue=self._clean_optional(game_input.venue),
        )

        session.add(game_record)
        session.flush()

        return game_record

    def _get_or_create_model_version(
        self,
        *,
        session: Session,
        model: ModelIdentity,
    ) -> ModelVersion:
        model_name = self._clean_required(
            model.model_name,
            "model_name",
        )

        version = self._clean_required(
            model.version,
            "model.version",
        )

        git_commit = self._clean_optional(
            model.git_commit
        ) or self._resolve_git_commit()

        statement = select(ModelVersion).where(
            ModelVersion.model_name == model_name,
            ModelVersion.version == version,
            ModelVersion.git_commit == git_commit,
        )

        model_version = session.execute(
            statement
        ).scalar_one_or_none()

        if model_version is not None:
            description = self._clean_optional(
                model.description
            )

            if (
                description is not None
                and model_version.description != description
            ):
                model_version.description = description
                session.flush()

            return model_version

        model_version = ModelVersion(
            model_name=model_name,
            version=version,
            git_commit=git_commit,
            description=self._clean_optional(
                model.description
            ),
        )

        session.add(model_version)
        session.flush()

        return model_version

    def _build_recommendation(
        self,
        *,
        game_record: Game,
        model_version: ModelVersion,
        model_run: ModelRun,
        recommendation_input: RecommendationInput,
    ) -> Recommendation:
        confidence = self._to_decimal(
            recommendation_input.confidence,
            "confidence",
        )

        if confidence < Decimal("0") or confidence > Decimal("1"):
            raise RecommendationValidationError(
                "confidence must be between 0 and 1."
            )

        recommendation_time = (
            self._ensure_aware_datetime(
                recommendation_input.recommendation_time
            )
            if recommendation_input.recommendation_time is not None
            else datetime.now(UTC)
        )

        return Recommendation(
            game_id=game_record.id,
            model_version_id=model_version.id,
            model_run_id=model_run.id,
            market_type=self._clean_required(
                recommendation_input.market_type,
                "market_type",
            ).upper(),
            selection=self._clean_required(
                recommendation_input.selection,
                "selection",
            ).upper(),
            market_line=self._to_optional_decimal(
                recommendation_input.market_line,
                "market_line",
            ),
            projection=self._to_decimal(
                recommendation_input.projection,
                "projection",
            ),
            edge=self._to_optional_decimal(
                recommendation_input.edge,
                "edge",
            ),
            confidence=confidence,
            components=dict(
                recommendation_input.components
            ),
            explanation=self._clean_optional(
                recommendation_input.explanation
            ),
            source=self._clean_required(
                recommendation_input.source,
                "recommendation.source",
            ),
            recommendation_time=recommendation_time,
        )

    @staticmethod
    def _validate_game(game: GameInput) -> None:
        if not game.league_code.strip():
            raise RecommendationValidationError(
                "league_code is required."
            )

        if not game.external_game_id.strip():
            raise RecommendationValidationError(
                "external_game_id is required."
            )

        if (
            game.home_team.normalized_code()
            == game.away_team.normalized_code()
        ):
            raise RecommendationValidationError(
                "Home and away team codes must be different."
            )

    @staticmethod
    def _validate_model(model: ModelIdentity) -> None:
        if not model.model_name.strip():
            raise RecommendationValidationError(
                "model_name is required."
            )

        if not model.version.strip():
            raise RecommendationValidationError(
                "model version is required."
            )

    @staticmethod
    def _validate_recommendations(
        recommendations: Sequence[RecommendationInput],
    ) -> None:
        if not recommendations:
            raise RecommendationValidationError(
                "At least one recommendation is required."
            )

    @staticmethod
    def _clean_required(
        value: str,
        field_name: str,
    ) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise RecommendationValidationError(
                f"{field_name} is required."
            )

        return cleaned

    @staticmethod
    def _clean_optional(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None

    @staticmethod
    def _ensure_aware_datetime(
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)

        return value.astimezone(UTC)

    @staticmethod
    def _to_decimal(
        value: Decimal | int | float | str,
        field_name: str,
    ) -> Decimal:
        try:
            return Decimal(str(value))
        except Exception as exc:
            raise RecommendationValidationError(
                f"{field_name} must be numeric."
            ) from exc

    @classmethod
    def _to_optional_decimal(
        cls,
        value: Decimal | int | float | str | None,
        field_name: str,
    ) -> Decimal | None:
        if value is None:
            return None

        return cls._to_decimal(
            value,
            field_name,
        )

    @staticmethod
    def _resolve_git_commit() -> str:
        """
        Resolve the current Git commit without adding GitPython.

        Falls back to 'unknown' when running outside a Git worktree.
        """

        try:
            result = subprocess.run(
                [
                    "git",
                    "rev-parse",
                    "--short=12",
                    "HEAD",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )

            commit = result.stdout.strip()

            return commit or "unknown"

        except (
            FileNotFoundError,
            subprocess.CalledProcessError,
            subprocess.TimeoutExpired,
        ):
            return "unknown"

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.database.session import SessionLocal
from app.models import Game, ModelRun, Recommendation
from app.services.recommendation_service import (
    GameInput,
    ModelIdentity,
    RecommendationInput,
    RecommendationService,
    RecommendationServiceError,
    TeamInput,
)


def main() -> int:
    print()
    print("=" * 72)
    print("SharpStack Recommendation Service Integration Test")
    print("=" * 72)
    print()

    unique_suffix = uuid4().hex[:8]
    external_game_id = f"sharpstack-service-test-{unique_suffix}"

    scheduled_start = (
        datetime.now(UTC)
        + timedelta(days=1)
    ).replace(
        hour=23,
        minute=10,
        second=0,
        microsecond=0,
    )

    game_input = GameInput(
        league_code="MLB",
        league_name="Major League Baseball",
        sport="baseball",
        league_country="United States",
        external_game_id=external_game_id,
        scheduled_start=scheduled_start,
        home_team=TeamInput(
            code="HOU",
            name="Houston Astros",
            city="Houston",
            external_team_id="117",
        ),
        away_team=TeamInput(
            code="SEA",
            name="Seattle Mariners",
            city="Seattle",
            external_team_id="136",
        ),
        status="scheduled",
        venue="Daikin Park",
    )

    model_identity = ModelIdentity(
        model_name="mlb_totals",
        version="0.3.7",
        description=(
            "SharpStack MLB totals model with starter "
            "and bullpen projections."
        ),
    )

    recommendation_inputs = [
        RecommendationInput(
            market_type="total",
            selection="over",
            market_line=Decimal("8.5"),
            projection=Decimal("9.26"),
            edge=Decimal("0.76"),
            confidence=Decimal("0.81"),
            components={
                "starter_total": 8.69,
                "bullpen_adjustment": 0.57,
                "projected_total": 9.26,
            },
            explanation=(
                "Projected total exceeds the market line "
                "with a positive bullpen adjustment."
            ),
            source="integration_test",
        ),
        RecommendationInput(
            market_type="team_total",
            selection="hou_over",
            market_line=Decimal("4.5"),
            projection=Decimal("5.12"),
            edge=Decimal("0.62"),
            confidence=Decimal("0.73"),
            components={
                "offense_projection": 4.71,
                "bullpen_adjustment": 0.41,
                "projected_team_total": 5.12,
            },
            explanation=(
                "Houston team-total projection exceeds "
                "the current market line."
            ),
            source="integration_test",
        ),
    ]

    service = RecommendationService()

    try:
        saved_batch = service.save_batch(
            game=game_input,
            model=model_identity,
            recommendations=recommendation_inputs,
            run_label="Drop 3B Integration Test",
            run_notes=(
                "Verifies atomic persistence of one model "
                "run and two recommendations."
            ),
            run_metadata={
                "test": True,
                "external_game_id": external_game_id,
                "recommendation_count": 2,
            },
            run_source="integration_test",
        )

        print("Save operation: SUCCESS")
        print()
        print(f"Model run ID:          {saved_batch.model_run_id}")
        print(f"Model version ID:      {saved_batch.model_version_id}")
        print(f"Game ID:               {saved_batch.game_id}")
        print(f"Recommendations saved: {saved_batch.recommendation_count}")
        print(f"Status:                {saved_batch.status}")
        print()

        verification_session = SessionLocal()

        try:
            statement = (
                select(ModelRun)
                .options(
                    selectinload(ModelRun.model_version),
                    selectinload(ModelRun.recommendations),
                )
                .where(
                    ModelRun.id
                    == saved_batch.model_run_id
                )
            )

            stored_run = verification_session.execute(
                statement
            ).scalar_one()

            stored_game = verification_session.execute(
                select(Game).where(
                    Game.id == saved_batch.game_id
                )
            ).scalar_one()

            stored_recommendations = (
                verification_session.execute(
                    select(Recommendation)
                    .where(
                        Recommendation.model_run_id
                        == stored_run.id
                    )
                    .order_by(
                        Recommendation.created_at.asc()
                    )
                )
                .scalars()
                .all()
            )

            recommendation_count = (
                verification_session.execute(
                    select(
                        func.count(Recommendation.id)
                    ).where(
                        Recommendation.model_run_id
                        == stored_run.id
                    )
                )
                .scalar_one()
            )

            assert stored_run.status == "completed"
            assert stored_run.completed_at is not None
            assert stored_run.model_version is not None
            assert (
                stored_run.model_version.model_name
                == "mlb_totals"
            )
            assert (
                stored_run.model_version.version
                == "0.3.7"
            )
            assert (
                stored_game.external_game_id
                == external_game_id
            )
            assert recommendation_count == 2
            assert len(stored_recommendations) == 2
            assert all(
                recommendation.model_run_id
                == stored_run.id
                for recommendation
                in stored_recommendations
            )

            print("Read-back verification: SUCCESS")
            print()
            print(
                f"Model:    "
                f"{stored_run.model_version.model_name}"
            )
            print(
                f"Version:  "
                f"{stored_run.model_version.version}"
            )
            print(
                f"Git:      "
                f"{stored_run.model_version.git_commit}"
            )
            print(
                f"Game:     SEA @ HOU"
            )
            print(
                f"Start:    "
                f"{stored_game.scheduled_start.isoformat()}"
            )
            print()

            print("Stored recommendations:")
            print("-" * 72)

            for recommendation in stored_recommendations:
                market_line = (
                    str(recommendation.market_line)
                    if recommendation.market_line
                    is not None
                    else "-"
                )

                edge = (
                    str(recommendation.edge)
                    if recommendation.edge is not None
                    else "-"
                )

                confidence_percent = (
                    recommendation.confidence
                    * Decimal("100")
                )

                print(
                    f"{recommendation.market_type:<12} "
                    f"{recommendation.selection:<12} "
                    f"Line {market_line:<7} "
                    f"Projection "
                    f"{recommendation.projection:<7} "
                    f"Edge {edge:<7} "
                    f"Confidence "
                    f"{confidence_percent:.1f}%"
                )

            print("-" * 72)
            print()
            print(
                "SharpStack successfully persisted and "
                "retrieved a model run."
            )

            return 0

        finally:
            verification_session.close()

    except (
        RecommendationServiceError,
        SQLAlchemyError,
        AssertionError,
    ) as exc:
        print("Integration test: FAILED")
        print()
        print(f"{type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

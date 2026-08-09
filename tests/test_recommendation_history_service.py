from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.recommendation_history_service import (
    ModelRunHistoryFilters,
    RecommendationHistoryFilters,
    RecommendationHistoryService,
    RecommendationHistoryValidationError,
)


def build_service_with_rows(rows: list[tuple]) -> tuple[
    RecommendationHistoryService,
    MagicMock,
]:
    session = MagicMock()
    session.execute.return_value.all.return_value = rows

    session_factory = MagicMock(return_value=session)

    service = RecommendationHistoryService(
        session_factory=session_factory
    )

    return service, session


def test_extracts_history_item_and_latest_grade() -> None:
    recommendation_id = uuid4()
    game_id = uuid4()
    model_run_id = uuid4()
    model_version_id = uuid4()
    grade_id = uuid4()

    now = datetime.now(UTC)

    recommendation = SimpleNamespace(
        id=recommendation_id,
        model_run_id=model_run_id,
        recommendation_time=now,
        market_type="MONEYLINE",
        selection="HOU",
        market_line=None,
        projection=Decimal("0.612"),
        edge=Decimal("0.073"),
        confidence=Decimal("0.74000"),
        components={
            "tier": "lean",
            "hammer_score": "68.2",
            "signal_combination": "MLB + FIRST5",
            "real_market_loaded": True,
        },
        explanation="Signals agree.",
        source="sharpstack",
    )

    game = SimpleNamespace(
        id=game_id,
        external_game_id="824414",
        scheduled_start=now + timedelta(hours=2),
        status="scheduled",
    )

    league = SimpleNamespace(
        code="MLB",
        name="Major League Baseball",
        sport="baseball",
    )

    model_version = SimpleNamespace(
        id=model_version_id,
        model_name="mlb_decision_builder",
        version="0.5.0",
        git_commit="51953fe",
    )

    model_run = SimpleNamespace(
        id=model_run_id,
        run_label="Morning Run",
        source="sharpstack",
    )

    grade = SimpleNamespace(
        id=grade_id,
        outcome="WIN",
        american_odds=125,
        stake_units=Decimal("1.000"),
        profit_units=Decimal("1.2500"),
        actual_home_score=Decimal("5"),
        actual_away_score=Decimal("3"),
        graded_at=now + timedelta(hours=6),
        source="manual",
        notes=None,
        grade_metadata={"verified": True},
    )

    service, session = build_service_with_rows(
        [
            (
                recommendation,
                game,
                league,
                model_version,
                model_run,
                grade,
            )
        ]
    )

    results = service.list_recommendations()

    assert len(results) == 1

    item = results[0]

    assert item.recommendation_id == recommendation_id
    assert item.game_id == game_id
    assert item.model_run_id == model_run_id
    assert item.league_code == "MLB"
    assert item.market_type == "MONEYLINE"
    assert item.tier == "LEAN"
    assert item.hammer_score == Decimal("68.2")
    assert item.signal_combination == "MLB + FIRST5"
    assert item.real_market_loaded is True

    assert item.latest_grade is not None
    assert item.latest_grade.grade_id == grade_id
    assert item.latest_grade.outcome == "WIN"
    assert item.latest_grade.profit_units == Decimal("1.2500")
    assert item.latest_grade.grade_metadata == {
        "verified": True
    }

    session.close.assert_called_once()


def test_ungraded_recommendation_returns_no_grade() -> None:
    now = datetime.now(UTC)

    recommendation = SimpleNamespace(
        id=uuid4(),
        model_run_id=None,
        recommendation_time=now,
        market_type="TOTAL",
        selection="OVER",
        market_line=Decimal("8.5"),
        projection=Decimal("9.1"),
        edge=Decimal("0.6"),
        confidence=Decimal("0.70000"),
        components={
            "recommendation": "WATCH",
            "hammer": 61.5,
            "real_market_loaded": "false",
        },
        explanation=None,
        source="sharpstack",
    )

    game = SimpleNamespace(
        id=uuid4(),
        external_game_id="test-game",
        scheduled_start=now,
        status="scheduled",
    )

    league = SimpleNamespace(
        code="MLB",
        name="Major League Baseball",
        sport="baseball",
    )

    model_version = SimpleNamespace(
        id=uuid4(),
        model_name="mlb_totals",
        version="0.1.0",
        git_commit="unknown",
    )

    service, _ = build_service_with_rows(
        [
            (
                recommendation,
                game,
                league,
                model_version,
                None,
                None,
            )
        ]
    )

    item = service.list_recommendations()[0]

    assert item.model_run_id is None
    assert item.run_label is None
    assert item.latest_grade is None
    assert item.tier == "WATCH"
    assert item.hammer_score == Decimal("61.5")
    assert item.real_market_loaded is False


def test_filter_normalization() -> None:
    now = datetime.now(UTC)

    normalized = (
        RecommendationHistoryService
        ._normalize_recommendation_filters(
            RecommendationHistoryFilters(
                start_time=now,
                end_time=now + timedelta(days=1),
                league_code=" mlb ",
                sport=" baseball ",
                market_type=" moneyline ",
                selection=" hou ",
                tier=" lean ",
                model_name=" decision_builder ",
                model_version=" 0.5.0 ",
                outcome=" win ",
                graded=True,
                minimum_confidence="0.60",
                maximum_confidence="0.85",
                minimum_hammer="55",
                maximum_hammer="75",
            )
        )
    )

    assert normalized.league_code == "MLB"
    assert normalized.sport == "BASEBALL"
    assert normalized.market_type == "MONEYLINE"
    assert normalized.selection == "HOU"
    assert normalized.tier == "LEAN"
    assert normalized.model_name == "DECISION_BUILDER"
    assert normalized.model_version == "0.5.0"
    assert normalized.outcome == "WIN"
    assert normalized.minimum_confidence == Decimal("0.60")
    assert normalized.maximum_confidence == Decimal("0.85")
    assert normalized.minimum_hammer == Decimal("55")
    assert normalized.maximum_hammer == Decimal("75")


@pytest.mark.parametrize(
    ("filters", "message"),
    [
        (
            RecommendationHistoryFilters(
                outcome="pending"
            ),
            "outcome must be",
        ),
        (
            RecommendationHistoryFilters(
                minimum_confidence="1.1"
            ),
            "minimum_confidence must be between",
        ),
        (
            RecommendationHistoryFilters(
                minimum_confidence="0.8",
                maximum_confidence="0.7",
            ),
            "maximum_confidence must be greater",
        ),
        (
            RecommendationHistoryFilters(
                minimum_hammer="70",
                maximum_hammer="60",
            ),
            "maximum_hammer must be greater",
        ),
        (
            RecommendationHistoryFilters(
                start_time=datetime.now(UTC),
                end_time=datetime.now(UTC)
                - timedelta(days=1),
            ),
            "end_time must be later",
        ),
    ],
)
def test_invalid_recommendation_filters(
    filters: RecommendationHistoryFilters,
    message: str,
) -> None:
    with pytest.raises(
        RecommendationHistoryValidationError,
        match=message,
    ):
        (
            RecommendationHistoryService
            ._normalize_recommendation_filters(filters)
        )


def test_naive_filter_datetime_is_rejected() -> None:
    with pytest.raises(
        RecommendationHistoryValidationError,
        match="timezone information",
    ):
        (
            RecommendationHistoryService
            ._normalize_recommendation_filters(
                RecommendationHistoryFilters(
                    start_time=datetime.now()
                )
            )
        )


@pytest.mark.parametrize(
    ("limit", "offset"),
    [
        (0, 0),
        (1001, 0),
        (100, -1),
        (True, 0),
        (100, False),
    ],
)
def test_invalid_pagination(
    limit: int,
    offset: int,
) -> None:
    with pytest.raises(
        RecommendationHistoryValidationError
    ):
        RecommendationHistoryService._validate_pagination(
            limit=limit,
            offset=offset,
        )


def test_lists_model_runs_as_dtos() -> None:
    now = datetime.now(UTC)
    model_run_id = uuid4()
    model_version_id = uuid4()

    model_run = SimpleNamespace(
        id=model_run_id,
        model_version_id=model_version_id,
        started_at=now,
        completed_at=now + timedelta(minutes=2),
        status="completed",
        source="sharpstack",
        run_label="Morning",
        notes=None,
        run_metadata={"games": 16},
    )

    model_version = SimpleNamespace(
        id=model_version_id,
        model_name="mlb_decision_builder",
        version="0.5.0",
        git_commit="51953fe",
    )

    service, session = build_service_with_rows(
        [(model_run, model_version)]
    )

    results = service.list_model_runs(
        filters=ModelRunHistoryFilters(
            model_name="mlb_decision_builder",
            status="completed",
        )
    )

    assert len(results) == 1

    item = results[0]

    assert item.model_run_id == model_run_id
    assert item.model_version_id == model_version_id
    assert item.model_name == "mlb_decision_builder"
    assert item.status == "completed"
    assert item.run_metadata == {"games": 16}

    session.close.assert_called_once()

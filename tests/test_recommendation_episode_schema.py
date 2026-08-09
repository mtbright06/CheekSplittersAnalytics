from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import UniqueConstraint, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.models import (
    CanonicalRecommendationGrade,
    RecommendationEpisode,
    RecommendationEpisodeStatus,
    RecommendationStream,
)
from app.models.recommendation_episode import (
    episode_identity_key,
    stream_identity_key,
)


NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def session_factory(*tables):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine, tables=list(tables))
    return sessionmaker(bind=engine)()


def stream(**overrides):
    data = {
        "sport": "BASEBALL",
        "league_code": "MLB",
        "provider": "mlb_stats_api",
        "provider_game_id": "824646",
        "market": "TOTALS",
        "model_version": "1.0.0",
        "scheduled_start_at": NOW,
    }
    data.update(overrides)
    return RecommendationStream(**data)


def episode(stream_row, **overrides):
    data = {
        "stream": stream_row,
        "selection": "OVER 9.5",
        "selection_side": "",
        "market_line": Decimal("9.5"),
        "status": RecommendationEpisodeStatus.ACTIVE.value,
        "opened_at": NOW,
    }
    data.update(overrides)
    return RecommendationEpisode(**data)


def test_duplicate_stream_identities_are_rejected():
    session = session_factory(RecommendationStream.__table__)
    session.add_all([stream(), stream()])

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return

    raise AssertionError("Duplicate stream identity was accepted.")


def test_selection_is_not_part_of_stream_identity():
    first = stream_identity_key(
        sport="BASEBALL",
        league_code="MLB",
        provider="mlb_stats_api",
        provider_game_id="824646",
        market="MONEYLINE",
        model_version="1.0.0",
    )
    second = stream_identity_key(
        sport="BASEBALL",
        league_code="MLB",
        provider="mlb_stats_api",
        provider_game_id="824646",
        market="MONEYLINE",
        model_version="1.0.0",
    )

    assert first == second


def test_only_one_active_episode_exists_per_stream():
    session = session_factory(
        RecommendationStream.__table__,
        RecommendationEpisode.__table__,
    )
    row = stream()
    session.add(row)
    session.flush()
    session.add_all([
        episode(row, selection="OVER 9.5"),
        episode(row, selection="UNDER 9.5", opened_at=NOW.replace(minute=1)),
    ])

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return

    raise AssertionError("Two active episodes for one stream were accepted.")


def test_market_line_change_stays_within_episode_identity():
    session = session_factory(
        RecommendationStream.__table__,
        RecommendationEpisode.__table__,
    )
    row = stream()
    session.add(row)
    session.flush()
    session.add_all([
        episode(
            row,
            market_line=Decimal("9.5"),
            status=RecommendationEpisodeStatus.ACTIVE.value,
        ),
    ])
    session.commit()

    stored = session.query(RecommendationEpisode).one()

    assert stored.market_line == Decimal("9.500")


def test_same_selection_side_and_open_time_rejects_second_episode_even_with_new_line():
    session = session_factory(
        RecommendationStream.__table__,
        RecommendationEpisode.__table__,
    )
    row = stream()
    session.add(row)
    session.flush()
    session.add_all([
        episode(
            row,
            status=RecommendationEpisodeStatus.SUPERSEDED.value,
            market_line=Decimal("8.5"),
            closed_at=NOW.replace(minute=1),
        ),
        episode(
            row,
            status=RecommendationEpisodeStatus.SUPERSEDED.value,
            market_line=Decimal("9.0"),
            closed_at=NOW.replace(minute=2),
        ),
    ])

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return

    raise AssertionError("Market line incorrectly distinguished episode identity.")


def test_over_and_under_remain_distinct_episode_identities():
    session = session_factory(
        RecommendationStream.__table__,
        RecommendationEpisode.__table__,
    )
    row = stream()
    session.add(row)
    session.flush()
    session.add_all([
        episode(
            row,
            selection="OVER 9.5",
            status=RecommendationEpisodeStatus.SUPERSEDED.value,
            closed_at=NOW.replace(minute=1),
        ),
        episode(
            row,
            selection="UNDER 9.5",
            status=RecommendationEpisodeStatus.SUPERSEDED.value,
            closed_at=NOW.replace(minute=2),
        ),
    ])
    session.commit()

    assert session.query(RecommendationEpisode).count() == 2


def test_invalid_state_values_are_rejected():
    session = session_factory(
        RecommendationStream.__table__,
        RecommendationEpisode.__table__,
    )
    row = stream()
    session.add(row)
    session.flush()
    session.add(episode(row, status="OBSERVED"))

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return

    raise AssertionError("Invalid episode status was accepted.")


def test_canonical_snapshot_relationship_is_valid():
    fk_targets = {
        next(iter(fk.column.table.name for fk in column.foreign_keys))
        for column in RecommendationEpisode.__table__.columns
        if column.name == "canonical_snapshot_id"
    }

    assert fk_targets == {"recommendations"}


def test_one_canonical_grade_exists_per_episode():
    unique_constraints = {
        constraint.name: tuple(column.name for column in constraint.columns)
        for constraint in CanonicalRecommendationGrade.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert unique_constraints["uq_canonical_recommendation_grades_episode"] == (
        "recommendation_episode_id",
    )


def test_retry_safe_identifiers_are_deterministic():
    stream_key = stream_identity_key(
        sport="baseball",
        league_code="mlb",
        provider="mlb_stats_api",
        provider_game_id="824646",
        market="totals",
        model_version="1.0.0",
    )

    first = episode_identity_key(
        stream_identity=stream_key,
        selection="over 9.50",
        selection_side=None,
        opened_at=NOW,
    )
    second = episode_identity_key(
        stream_identity=stream_key,
        selection="OVER 9.50",
        selection_side="",
        opened_at=NOW,
    )

    assert first == second

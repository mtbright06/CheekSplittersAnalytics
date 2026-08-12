from datetime import UTC, datetime

from dashboard.kbo_freshness import evaluate_kbo_card_freshness


def _card(
    *,
    generated_at="2026-08-11T11:15:00",
    game_dates=None,
):
    return {
        "sport": "KBO",
        "generated_at": generated_at,
        "games": [
            {"game_date": value}
            for value in game_dates or []
        ],
    }


def test_current_kst_game_date_is_accepted():
    freshness = evaluate_kbo_card_freshness(
        _card(game_dates=["2026-08-12"]),
        now=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        schedule_games=[{"game_date": "2026-08-12"}],
    )

    assert freshness.status == "CURRENT"
    assert freshness.expected_game_date == "2026-08-12"


def test_previous_date_card_is_marked_stale():
    freshness = evaluate_kbo_card_freshness(
        _card(game_dates=["2026-08-11"]),
        now=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        schedule_games=[{"game_date": "2026-08-12"}],
    )

    assert freshness.status == "STALE"
    assert freshness.last_successful_build == "2026-08-11T11:15:00"


def test_fresh_empty_card_with_scheduled_games_is_unavailable():
    freshness = evaluate_kbo_card_freshness(
        _card(game_dates=[]),
        now=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        schedule_games=[{"game_date": "2026-08-12"}],
    )

    assert freshness.status == "UNAVAILABLE"
    assert freshness.source_game_count == 1


def test_genuine_no_game_day_accepts_empty_card():
    freshness = evaluate_kbo_card_freshness(
        _card(game_dates=[]),
        now=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        schedule_games=[],
    )

    assert freshness.status == "CURRENT"
    assert freshness.source_game_count == 0


def test_stale_artifact_remains_readable_but_flagged():
    freshness = evaluate_kbo_card_freshness(
        _card(
            generated_at="2026-08-10T20:00:00",
            game_dates=["2026-08-10"],
        ),
        now=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        schedule_games=[{"game_date": "2026-08-12"}],
    )

    assert freshness.status == "STALE"
    assert freshness.card_game_dates == ("2026-08-10",)


def test_us_kst_date_boundary_uses_source_game_date_truth():
    freshness = evaluate_kbo_card_freshness(
        _card(
            generated_at="2026-08-11T11:15:00",
            game_dates=["2026-08-12"],
        ),
        now=datetime(2026, 8, 11, 15, 15, tzinfo=UTC),
        schedule_games=[{"game_date": "2026-08-12"}],
    )

    assert freshness.status == "CURRENT"
    assert freshness.expected_game_date == "2026-08-12"


def test_malformed_generated_at_is_flagged_safely():
    freshness = evaluate_kbo_card_freshness(
        _card(
            generated_at="not-a-date",
            game_dates=["2026-08-12"],
        ),
        now=datetime(2026, 8, 11, 15, 0, tzinfo=UTC),
        schedule_games=[{"game_date": "2026-08-12"}],
    )

    assert freshness.status == "STALE"

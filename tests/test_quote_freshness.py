from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from engine.adapters.mlb_decision_adapter import adapt_decision
from engine.mlb.game_builder import build_mlb_card, quote_to_dict
from engine.odds.best_line import (
    enrich_quote,
    quote_to_dict as best_line_quote_to_dict,
    select_best_quote,
)
from engine.odds.quote_utils import quote_freshness
from engine.odds.reference_price_policy import ReferencePriceResult
from engine.odds.the_odds_api_provider import TheOddsApiProvider
from engine.decision.decision_builder import extract_mlb_market


NOW = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


def quote(*, odds, updated_at):
    return {
        "provider": "the_odds_api",
        "sportsbook": "FanDuel",
        "league": "MLB",
        "market": "Moneyline",
        "selection": "Home Club",
        "away_team": "Away Club",
        "home_team": "Home Club",
        "american_odds": odds,
        "event_id": "event-1",
        "commence_time": "2026-07-25T20:00:00Z",
        "last_updated": updated_at,
    }


def test_quote_freshness_classifies_valid_and_invalid_timestamps():
    assert quote_freshness(
        "2026-07-25T11:50:00Z", now=NOW
    ).status == "FRESH"
    assert quote_freshness(
        "2026-07-25T11:30:00Z", now=NOW
    ).status == "STALE"
    assert quote_freshness(
        "2026-07-25T12:01:00Z", now=NOW
    ).status == "FUTURE_TIMESTAMP"
    assert quote_freshness(
        "2026-07-25T07:50:00-04:00", now=NOW
    ).status == "FRESH"
    assert quote_freshness(
        "2026-07-25T11:50:00", now=NOW
    ).status == "NAIVE_TIMESTAMP"
    assert quote_freshness(None, now=NOW).status == "MISSING_TIMESTAMP"
    assert quote_freshness("not-a-date", now=NOW).status == "MALFORMED_TIMESTAMP"


def test_fresh_selection_preserves_its_own_freshness_metadata():
    fresh = quote(odds=-110, updated_at="2026-07-25T11:50:00Z")
    stale = quote(odds=120, updated_at="2026-07-25T11:00:00Z")

    with patch("engine.odds.best_line.quote_freshness") as freshness:
        freshness.side_effect = lambda updated_at, **kwargs: quote_freshness(
            updated_at, now=NOW, **kwargs
        )
        selected = select_best_quote([stale, fresh])

    assert selected["american_odds"] == -110
    assert selected["freshness_status"] == "FRESH"
    assert selected["quote_updated_at_utc"] == "2026-07-25T11:50:00+00:00"
    assert selected["quote_age_minutes"] == 10.0
    assert quote_to_dict(selected)["freshness_status"] == "FRESH"
    serialized = best_line_quote_to_dict(
        SimpleNamespace(**selected)
    )
    assert serialized["american_odds"] == -110
    assert serialized["sportsbook"] == "FanDuel"
    assert serialized["freshness_status"] == "FRESH"
    assert serialized["stale"] is False


def test_stale_fallback_requires_explicit_opt_in():
    stale = quote(odds=120, updated_at="2026-07-25T11:00:00Z")

    with patch("engine.odds.best_line.quote_freshness") as freshness:
        freshness.side_effect = lambda updated_at, **kwargs: quote_freshness(
            updated_at, now=NOW, **kwargs
        )
        assert select_best_quote([stale]) is None
        selected = select_best_quote([stale], allow_stale=True)

    assert selected["freshness_status"] == "STALE"
    assert selected["stale"] is True


def test_future_and_invalid_quotes_are_never_selected():
    future = quote(odds=120, updated_at="2026-07-25T12:01:00Z")
    malformed = quote(odds=110, updated_at="bad-date")

    with patch("engine.odds.best_line.quote_freshness") as freshness:
        freshness.side_effect = lambda updated_at, **kwargs: quote_freshness(
            updated_at, now=NOW, **kwargs
        )
        assert select_best_quote([future, malformed]) is None
        assert select_best_quote([future, malformed], allow_stale=True) is None


def test_odds_api_normalization_preserves_the_provider_timestamp():
    provider = object.__new__(TheOddsApiProvider)
    provider.provider_name = "the_odds_api"
    quotes = provider._normalize_moneylines(
        events=[
            {
                "id": "event-1",
                "away_team": "Away Club",
                "home_team": "Home Club",
                "commence_time": "2026-07-25T20:00:00Z",
                "bookmakers": [
                    {
                        "title": "FanDuel",
                        "last_update": "2026-07-25T11:45:00Z",
                        "markets": [
                            {
                                "key": "h2h",
                                "outcomes": [
                                    {"name": "Away Club", "price": 110},
                                    {"name": "Home Club", "price": -130},
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        league="MLB",
    )

    assert [item.last_updated for item in quotes] == [
        "2026-07-25T11:45:00Z",
        "2026-07-25T11:45:00Z",
    ]


class LockedReferenceResolver:
    def resolve_quote(self, selected_quote, league):
        return ReferencePriceResult(
            "LOCKED",
            {
                "reference_price": selected_quote["american_odds"],
                "reference_implied_probability": selected_quote["implied_probability"],
                "reference_book": selected_quote["sportsbook"],
                "reference_captured_at": selected_quote["last_updated"],
                "reference_minutes_before_start": 100.0,
                "reference_status": "LOCKED",
                "reference_policy_version": "test",
                "provider_event_id": selected_quote["event_id"],
                "scheduled_start_utc": selected_quote["commence_time"],
                "slate_date": "2026-07-25",
            },
        )


def test_mlb_card_artifact_timestamp_follows_the_selected_quote():
    updated_at = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    quotes = [
        {
            **quote(odds=115, updated_at=updated_at),
            "selection": "Away Club",
        },
        {
            **quote(odds=-135, updated_at=updated_at),
            "selection": "Home Club",
        },
    ]
    raw_games = [
        {
            "gamePk": 1,
            "gameDate": "2026-07-25T20:00:00Z",
            "status": {"detailedState": "Scheduled"},
            "teams": {
                "away": {"team": {"id": 1, "name": "Away Club"}},
                "home": {"team": {"id": 2, "name": "Home Club"}},
            },
        }
    ]

    profile = {"runs_per_game": 4.5, "ops": 0.7}
    pitcher = {"name": "Starter", "era": 3.5, "whip": 1.2}

    with (
        patch("engine.mlb.game_builder.fetch_market_quotes", return_value=(quotes, [])),
        patch("engine.mlb.game_builder.fetch_team_batting_stats", return_value=profile),
        patch("engine.mlb.game_builder.fetch_bullpen_profile", return_value={}),
        patch("engine.mlb.game_builder.fetch_pitcher_stats", return_value=pitcher),
        patch("engine.mlb.game_builder.build_totals_projection", return_value={}),
    ):
        card = build_mlb_card(
            raw_games,
            reference_price_resolver=LockedReferenceResolver(),
        )

    odds = card["games"][0]["odds"]
    assert odds["freshness_status"] == "FRESH"
    assert odds["american_odds"] == -135
    assert odds["quote_updated_at_utc"] == updated_at
    assert datetime.fromisoformat(card["generated_at"]) >= datetime.fromisoformat(updated_at)


def test_decision_market_keeps_the_locked_ssrp_quote_coherent():
    market = extract_mlb_market(
        {
            "odds": {
                "selection": "Washington Nationals",
                "event_id": "event-1",
                "sportsbook": "LowVig",
                "american_odds": -147,
                "book_probability": 0.595142,
                "quote_updated_at_utc": "2026-07-25T12:56:23+00:00",
                "freshness_status": "STALE",
                "freshness_reason": "Quote age exceeds 20 minutes.",
                "quote_age_minutes": 41.0,
            },
            "market_edge": {
                "selection": "Washington Nationals",
                "provider_event_id": "event-1",
                "reference_status": "LOCKED",
                "american_odds": -134,
                "reference_implied_probability": 0.57265,
                "book_probability": 57.265,
                "sportsbook": "FanDuel",
                "reference_captured_at": "2026-07-25T03:01:00+00:00",
                "edge": 2.63,
            },
            "model": {"recommendation": "👀 LEAN"},
        },
        "Washington Nationals",
    )

    assert market["book_odds"] == -134
    assert market["book_raw_implied_probability"] == 0.57265
    assert market["book_no_vig_probability"] == 0.57265
    assert market["sportsbook"] == "FanDuel"
    assert market["market_updated_at"] == "2026-07-25T03:01:00+00:00"
    assert market["quote_source"] == "sharpstack_reference_price"
    assert market["quote_identity"] == (
        "sharpstack_reference_price:event-1:Washington Nationals:FanDuel:-134"
    )
    # Current-quote freshness remains diagnostic metadata, never a substitute
    # for the locked SSRP probability or sportsbook.
    assert market["current_freshness_status"] == "STALE"


def test_decision_adapter_receives_the_same_ssrp_price_and_probability():
    recommendation = adapt_decision(
        {
            "game_pk": 1,
            "matchup": "Washington Nationals @ Example Club",
            "selected_team": "Washington Nationals",
            "real_market_loaded": True,
            "book_odds": -134,
            "sportsbook": "FanDuel",
            "market_probability": 0.57265,
            "market_no_vig_probability": 0.57265,
            "market_updated_at": "2026-07-25T03:01:00+00:00",
            "market_edge_pct": 2.63,
            "model_probability": 0.599,
            "model_recommendation": "👀 LEAN",
            "recommendation": "👀 LEAN",
        }
    )

    assert recommendation.market_probability == 0.57265
    assert recommendation.market_quote.sportsbook == "FanDuel"
    assert recommendation.market_quote.odds == -134
    assert recommendation.market_quote.implied_probability == 0.57265
    assert recommendation.market_quote.updated_at == "2026-07-25T03:01:00+00:00"

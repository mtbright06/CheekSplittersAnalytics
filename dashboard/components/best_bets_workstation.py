from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from components.badges import recommendation_badge_html
from components.registry.registry_cards import american, percent, signed_percent
from components.status_pill import status_pill_html

EASTERN = ZoneInfo("America/New_York")


def render_best_bets_workstation(
    registry: dict,
    recommendations: list[dict],
    play_of_day: dict | None = None,
) -> list[dict]:
    """Render the Best Bets operational card using existing registry rows."""
    summary = _summary_from_registry(registry, recommendations)
    st.markdown(
        _today_card_hero_html(summary, registry.get("generated_at")),
        unsafe_allow_html=True,
    )

    if play_of_day:
        st.markdown(
            _top_play_banner_html(play_of_day),
            unsafe_allow_html=True,
        )

    league, market = _render_filters(recommendations)
    filtered = filter_recommendations(recommendations, league, market)

    if not filtered:
        st.info("No qualifying plays match the selected filters.")
        return []

    st.markdown("<div class='best-bets-list'>", unsafe_allow_html=True)
    for index, item in enumerate(filtered, start=1):
        st.markdown(
            _recommendation_row_html(item, index),
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)
    return filtered


def filter_recommendations(
    recommendations: list[dict],
    league: str,
    market: str,
) -> list[dict]:
    return [
        item
        for item in recommendations
        if _matches_filter(item.get("league"), league)
        and _matches_filter(item.get("market"), market)
        and item.get(
            "actionable",
            item.get("recommendation") in {"HAMMER", "BET", "LEAN"},
        )
    ]


def _render_filters(recommendations: list[dict]) -> tuple[str, str]:
    leagues = _available_values(recommendations, "league", ["MLB", "KBO"])
    markets = _available_values(
        recommendations,
        "market",
        ["moneyline", "totals", "props"],
    )

    st.markdown("<div class='best-bets-filters'>", unsafe_allow_html=True)
    league_col, market_col = st.columns(2, gap="small")
    with league_col:
        league = st.radio(
            "League",
            leagues,
            horizontal=True,
            key="best_bets_workstation_league",
        )
    with market_col:
        market_label = st.radio(
            "Market",
            [_market_label(value) for value in markets],
            horizontal=True,
            key="best_bets_workstation_market",
        )
    st.markdown("</div>", unsafe_allow_html=True)

    return league, _market_value(market_label)


def _today_card_hero_html(summary: dict, generated_at: Any) -> str:
    updated = _display_datetime(generated_at)
    stats = [
        ("League", _league_summary(summary.get("leagues"))),
        ("Recommendations", summary.get("recommendations", 0)),
        ("Strong Bets", summary.get("strong_bets", 0)),
        ("Playable", summary.get("playable", 0)),
        ("Leans", summary.get("leans", 0)),
    ]
    if updated:
        stats.append(("Updated", updated))

    stat_html = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(str(value))}</strong></div>"
        for label, value in stats
    )
    return (
        "<section class='best-bets-hero'>"
        "<span>Today's Card</span>"
        f"<div class='best-bets-hero-stats'>{stat_html}</div>"
        "</section>"
    )


def _summary_from_registry(registry: dict, recommendations: list[dict]) -> dict:
    summary = dict(registry.get("summary", {}))
    labels = [
        str(item.get("recommendation") or "").upper()
        for item in recommendations
        if item.get("actionable", True)
    ]
    summary["strong_bets"] = sum(
        "STRONG" in label or label in {"BET", "HAMMER"}
        for label in labels
    )
    summary["playable"] = sum("PLAYABLE" in label for label in labels)
    summary["leans"] = sum("LEAN" in label for label in labels)
    return summary


def _top_play_banner_html(play_data: dict) -> str:
    recommendation = play_data.get("recommendation")
    if not _is_valid_top_play(recommendation):
        reason = play_data.get("reason") or "No eligible pregame Top Play is available."
        return (
            "<div class='best-bets-top-play best-bets-top-play--empty'>"
            "<span>Today's Top Play</span>"
            f"<strong>{escape(str(reason))}</strong>"
            "</div>"
        )

    quote = recommendation.get("market_quote") or {}
    edge = _top_play_edge(recommendation)
    details = [
        recommendation.get("recommendation"),
        f"Hammer {number_value(recommendation.get('hammer_score'))}",
        f"Edge {edge}" if edge != "N/A" else None,
        f"Best Price {american(quote.get('odds'))}",
    ]
    details_html = " &bull; ".join(
        escape(str(detail))
        for detail in details
        if detail and str(detail) != "Best Price N/A"
    )
    return (
        "<div class='best-bets-top-play'>"
        "<span>Today's Top Play</span>"
        "<strong>"
        f"{escape(str(recommendation.get('selection') or 'Unavailable'))}"
        f" <em>&mdash;</em> {escape(str(recommendation.get('matchup') or ''))}"
        "</strong>"
        f"<small>{details_html}</small>"
        "</div>"
    )


def _recommendation_row_html(item: dict, rank: int) -> str:
    quote = item.get("market_quote") or {}
    recommendation = item.get("recommendation") or "PASS"
    market_status = "REAL MARKET" if item.get("real_market_loaded") else "MODEL ONLY"
    rows = [
        ("Current Odds", _odds_or_line(item, quote)),
        ("Edge", _edge(item)),
        ("Hammer Confidence", _confidence(item)),
    ]
    rows_html = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in rows
        if value != "N/A"
    )
    explanation = _quick_explanation(item)

    return (
        "<article class='best-bets-row'>"
        "<div class='best-bets-rank'>"
        f"{rank}"
        "</div>"
        "<div class='best-bets-main'>"
        "<div class='best-bets-title-row'>"
        "<div>"
        f"<strong>{escape(str(item.get('selection') or 'Unavailable'))}</strong>"
        f"<span>{escape(str(item.get('matchup') or ''))}</span>"
        "</div>"
        f"{recommendation_badge_html(recommendation, fallback_stars=item.get('stars') or '')}"
        "</div>"
        "<div class='best-bets-meta-row'>"
        f"<span>{escape(str(item.get('league') or ''))}</span>"
        f"<span>{escape(_market_label(item.get('market')))}</span>"
        f"{status_pill_html(market_status)}"
        "</div>"
        "</div>"
        f"<div class='best-bets-values'>{rows_html}</div>"
        f"<div class='best-bets-explanation'>{escape(explanation)}</div>"
        "</article>"
    )


def _quick_explanation(item: dict) -> str:
    reasons = item.get("reasons") or []
    if reasons:
        return str(reasons[0])
    selection = item.get("selection") or "this play"
    edge = _edge(item)
    confidence = _confidence(item)
    if edge != "N/A":
        return f"SharpStack sees value on {selection} with {edge} edge."
    if confidence != "N/A":
        return f"SharpStack rates {selection} at {confidence} confidence."
    return "No supporting explanation is available."


def _available_values(
    recommendations: list[dict],
    key: str,
    preferred: list[str],
) -> list[str]:
    values = {str(item.get(key)) for item in recommendations if item.get(key)}
    ordered = [value for value in preferred if value in values or value == "props"]
    return ordered or preferred


def _matches_filter(value: Any, selected: str) -> bool:
    return str(value or "").lower() == str(selected or "").lower()


def _market_label(value: Any) -> str:
    labels = {
        "moneyline": "Moneyline",
        "totals": "Totals",
        "props": "Props",
    }
    return labels.get(str(value or "").lower(), str(value or "Market").title())


def _market_value(label: str) -> str:
    return str(label or "").lower()


def _odds_or_line(item: dict, quote: dict) -> str:
    if item.get("market") == "totals" and quote.get("line") is not None:
        return str(quote.get("line"))
    return american(quote.get("odds"))


def _edge(item: dict) -> str:
    if item.get("edge_pct") is not None:
        return signed_percent(item.get("edge_pct"))
    if item.get("market_edge") is not None:
        return signed_percent(item.get("market_edge"))
    return "N/A"


def _top_play_edge(item: dict) -> str:
    source_signals = item.get("source_signals") or {}
    if source_signals.get("totals_edge_runs") is not None:
        try:
            return f"{float(source_signals.get('totals_edge_runs')):+.2f}"
        except (TypeError, ValueError):
            return "N/A"
    return _edge(item)


def _confidence(item: dict) -> str:
    if item.get("hammer_confidence") is not None:
        return str(item.get("hammer_confidence"))
    if item.get("confidence") is not None:
        return str(item.get("confidence"))
    if item.get("model_probability") is not None:
        return percent(item.get("model_probability"))
    if item.get("hammer_score") is not None:
        return f"{float(item.get('hammer_score')):.1f}"
    return "N/A"


def number_value(value: Any) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "N/A"


def _is_valid_top_play(recommendation: Any) -> bool:
    if not isinstance(recommendation, dict):
        return False
    return (
        recommendation.get("actionable") is True
        and recommendation.get("pregame_eligible", True) is True
        and str(
            recommendation.get("pregame_eligibility_reason")
            or "UNVERIFIED"
        )
        == "GAME_NOT_STARTED"
        and str(recommendation.get("status") or "pregame").lower() == "pregame"
    )


def _league_summary(leagues: Any) -> str:
    if isinstance(leagues, list) and leagues:
        if "MLB" in leagues:
            return "MLB"
        return str(leagues[0])
    return "All"


def _display_datetime(value: Any) -> str:
    if not value:
        return ""
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=EASTERN)
    localized = parsed.astimezone(EASTERN)
    return localized.strftime("%I:%M %p").lstrip("0")

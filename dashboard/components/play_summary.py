import streamlit as st

from components.badges import (
    market_value_badge_html,
    recommendation_badge_html,
)
from components.progress import render_progress_bar
from components.value_meter import render_value_meter


def render_play_summary(
    game,
    *,
    hammer_score=None,
):
    matchup = game["matchup"]
    model = game["model"]
    odds = game["odds"]

    play = model.get("play") or "No Play"
    market = model.get("market") or "Market"
    recommendation = model.get("recommendation") or "PASS"
    sport = str(game.get("sport") or "").lower()
    confidence = model.get("confidence")
    book_probability = odds.get("book_probability")
    moneyline = odds.get("moneyline")
    market_loaded = bool(odds.get("real_market_loaded")) or (
        book_probability is not None
        and moneyline is not None
    )
    state = play_summary_state(
        market_loaded=market_loaded,
        stale=bool(odds.get("stale")),
        recommendation=recommendation if sport == "kbo" else None,
        freshness_status=(
            odds.get("freshness_status")
            if sport == "mlb"
            else None
        ),
    )
    edge = model.get("edge")
    edge_text = f"{float(edge):.2f}%" if edge is not None else "Unavailable"
    book_text = (
        f"{_percent(book_probability):.1f}%"
        if book_probability is not None
        else "Unavailable"
    )
    confidence_text = (
        f"{float(confidence):.1f}/100"
        if confidence is not None
        else "Unavailable"
    )
    odds_text = str(moneyline) if moneyline is not None else "Unavailable"
    reference_price = odds.get("reference_price")
    reference_text = (
        str(reference_price)
        if reference_price is not None
        else "Unavailable"
    )
    value_label = model.get("market_value_label") or "VALUE UNAVAILABLE"
    value_tone = model.get("market_value_tone") or "unavailable"

    if sport == "mlb":
        heading = "Model Prediction · Projected Winner"
        title = play
        subtitle = market
    else:
        heading = "KBO Model Recommendation"
        title = play
        subtitle = market

    html = "".join(
        [
            "<div class='play-hero'><div>",
            f"<div class='small-label'>{heading}</div>",
            f"<div class='play-title'>{title}</div>",
            f"<div class='muted'>{subtitle}</div>",
            "</div><div class='play-hero-metrics'>",
            (
                f"<div><span>Model Win %</span><strong>{_model_probability_text(model.get('model_probability'))}</strong></div>"
                if sport == "mlb"
                else f"<div><span>Edge</span><strong>{edge_text}</strong></div>"
            ),
            (
                f"<div><span>Model Confidence</span><strong>{confidence_text}</strong></div>"
                if sport == "mlb"
                else f"<div><span>Book</span><strong>{book_text}</strong></div>"
            ),
            (
                f"<div><span>Current Odds</span><strong>{odds_text}</strong></div>"
                if sport == "mlb"
                else f"<div><span>Model Strength</span><strong>{confidence_text}</strong></div>"
            ),
            "</div></div><div class='play-hero-footer'>",
            (
                "<div class='conviction-value-panel'>"
                "<div class='conviction-value-block'>"
                "<span class='small-label'>Model Conviction</span>"
                + recommendation_badge_html(recommendation)
                + "</div><div class='conviction-value-divider'></div>"
                "<div class='conviction-value-block'>"
                "<span class='small-label'>Market Value</span>"
                + market_value_badge_html(value_label, value_tone)
                + f"<span class='market-context'>{state['badge']} · Current odds: {odds_text} · Reference price: {reference_text}</span>"
                + "</div></div>"
                if sport == "mlb"
                else recommendation_badge_html(
                    recommendation,
                    model_only=not market_loaded,
                )
                + f"<span class='small-label'>{state['badge']}</span>"
                + f"<span class='muted'>{matchup['away']} @ {matchup['home']} · {state['market_status']}</span>"
            ),
            "</div>",
        ]
    )

    st.markdown(html, unsafe_allow_html=True)

    # MLB market comparison is a diagnostic, so it belongs in the
    # SharpStack Intelligence accordion. KBO keeps its model-only assessment
    # in the summary until a real market is available.
    if sport != "mlb":
        render_value_meter(game)
    if confidence is not None and sport != "mlb":
        render_progress_bar(
            "Model Strength" if sport == "kbo" else "Confidence",
            confidence,
        )


def _percent(value):
    number = float(value)
    return number * 100 if abs(number) <= 1 else number


def _model_probability_text(value):
    if value is None:
        return "Unavailable"
    return f"{_percent(value):.1f}%"


def play_summary_state(
    *,
    market_loaded: bool,
    stale: bool,
    recommendation: str | None = None,
    freshness_status: str | None = None,
) -> dict[str, str]:
    if freshness_status in {
        "MISSING_TIMESTAMP",
        "MALFORMED_TIMESTAMP",
        "NAIVE_TIMESTAMP",
        "FUTURE_TIMESTAMP",
    }:
        return {
            "heading": "Model Preference",
            "badge": "MARKET TIMESTAMP INVALID",
            "market_status": "Market timestamp unavailable or invalid",
        }

    if not market_loaded:
        return {
            "heading": "Model Preference",
            "badge": "MODEL ONLY",
            "market_status": (
                "Market unavailable · Odds unavailable"
                if recommendation not in (None, "❌ NO PLAY", "NO PLAY", "PASS")
                else "No bet recommended · Market unavailable · Odds unavailable"
            ),
        }

    if stale:
        return {
            "heading": "Recommended Play",
            "badge": "STALE MARKET",
            "market_status": "Stale market price",
        }

    return {
        "heading": "Recommended Play",
        "badge": "MARKET READY",
        "market_status": "Market price loaded",
    }

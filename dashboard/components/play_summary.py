import streamlit as st

from components.badges import play_grade, play_badge_class
from components.progress import render_progress_bar
from components.value_meter import render_value_meter


def render_play_summary(game):
    matchup = game["matchup"]
    model = game["model"]
    odds = game["odds"]

    play = model.get("play") or "No Play"
    market = model.get("market") or "Market"
    edge = model.get("edge")
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
    )
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

    html = (
        "<div class='play-hero'>"
        "<div>"
        f"<div class='small-label'>{state['heading']}</div>"
        f"<div class='play-title'>🔥 {play} {market}</div>"
        f"<div class='muted'>{matchup['away']} @ {matchup['home']}</div>"
        "</div>"
        "<div class='play-hero-metrics'>"
        f"<div><span>Edge</span><strong>{edge_text}</strong></div>"
        f"<div><span>Book</span><strong>{book_text}</strong></div>"
        f"<div><span>Confidence</span><strong>{confidence_text}</strong></div>"
        "</div>"
        "</div>"
        "<div class='play-hero-footer'>"
        f"<span class='{play_badge_class(edge)}'>{state['badge']}</span>"
        f"<span class='muted'>{market} · {state['market_status']} · Odds: {odds_text}</span>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)

    render_value_meter(game)
    if confidence is not None:
        render_progress_bar("Confidence", confidence)


def _percent(value):
    number = float(value)
    return number * 100 if abs(number) <= 1 else number


def play_summary_state(*, market_loaded: bool, stale: bool) -> dict[str, str]:
    if not market_loaded:
        return {
            "heading": "Model Preference",
            "badge": "MODEL ONLY",
            "market_status": "No bet recommended - market unavailable",
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

import streamlit as st

from components.badges import recommendation_badge_html
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
        recommendation=recommendation if sport == "kbo" else None,
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
    hammer_text = (
        f"{float(hammer_score):.1f}"
        if hammer_score is not None
        else "Unavailable"
    )

    if sport == "mlb":
        heading = "MLB Model Recommendation"
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
            f"<div><span>Edge</span><strong>{edge_text}</strong></div>",
            f"<div><span>{'Book Win %' if sport == 'mlb' else 'Book'}</span><strong>{book_text}</strong></div>",
            f"<div><span>{'Model Confidence' if sport == 'mlb' else 'Model Strength'}</span><strong>{confidence_text}</strong></div>",
            (
                f"<div><span>Hammer Score</span><strong>{hammer_text}</strong></div>"
                if sport == "mlb"
                else ""
            ),
            "</div></div><div class='play-hero-footer'>",
            recommendation_badge_html(
                recommendation,
                model_only=sport == "kbo" and not market_loaded,
            ),
            f"<span class='small-label'>{state['badge']}</span>",
            (
                f"<span class='muted'>{market} · {state['market_status']} · Odds: {odds_text}</span>"
                if sport == "mlb"
                else f"<span class='muted'>{matchup['away']} @ {matchup['home']} · {state['market_status']}</span>"
            ),
            "</div>",
        ]
    )

    st.markdown(html, unsafe_allow_html=True)

    render_value_meter(game)
    if confidence is not None:
        render_progress_bar(
            "Model Strength" if sport == "kbo" else "Confidence",
            confidence,
        )


def _percent(value):
    number = float(value)
    return number * 100 if abs(number) <= 1 else number


def play_summary_state(
    *,
    market_loaded: bool,
    stale: bool,
    recommendation: str | None = None,
) -> dict[str, str]:
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

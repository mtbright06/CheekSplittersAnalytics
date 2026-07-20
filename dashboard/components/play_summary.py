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
    confidence = model.get("confidence") or 0

    html = (
        "<div class='play-hero'>"
        "<div>"
        "<div class='small-label'>Recommended Play</div>"
        f"<div class='play-title'>🔥 {play} {market}</div>"
        f"<div class='muted'>{matchup['away']} @ {matchup['home']}</div>"
        "</div>"
        "<div class='play-hero-metrics'>"
        f"<div><span>Edge</span><strong>{float(edge or 0):.2f}%</strong></div>"
        f"<div><span>Book</span><strong>{float(odds.get('book_probability') or 0) * 100:.1f}%</strong></div>"
        f"<div><span>Confidence</span><strong>{float(confidence or 0):.1f}/100</strong></div>"
        "</div>"
        "</div>"
        "<div class='play-hero-footer'>"
        f"<span class='{play_badge_class(edge)}'>{play_grade(edge)}</span>"
        f"<span class='muted'>{market} · Odds: {odds.get('moneyline')}</span>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)

    render_value_meter(game)
    render_progress_bar("Confidence", confidence)

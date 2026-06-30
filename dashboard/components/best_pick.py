import streamlit as st

from components.badges import play_badge_class, play_grade
from components.logos import team_logo_html
from components.progress import render_progress_bar
from components.team_colors import team_color
from components.value_meter import render_value_meter


def render_best_pick(game):
    matchup = game["matchup"]
    model = game["model"]

    play = model.get("play") or "No Play"
    market = model.get("market") or "Market"
    edge = model.get("edge") or 0
    confidence = model.get("confidence") or 0

    accent = team_color(play)

    html = (
        f"<div class='daily-lock-card' style='border-left:7px solid {accent};'>"
        "<div class='daily-lock-layout'>"
        "<div class='daily-lock-logo-wrap'>"
        f"{team_logo_html(play, sport='kbo')}"
        "</div>"
        "<div class='daily-lock-content'>"
        "<div class='daily-lock-kicker'>🍑 Splitter Pick of the Day</div>"
        f"<div class='daily-lock-title'>{play}</div>"
        f"<div class='daily-lock-market'>{market}</div>"
        f"<div class='daily-lock-subtitle'>{matchup['away']} @ {matchup['home']}</div>"
        "<div class='daily-lock-grid'>"
        f"<div><span>Edge</span><strong>{edge:.1f}%</strong></div>"
        f"<div><span>Confidence</span><strong>{confidence}/100</strong></div>"
        f"<div><span>Grade</span><strong>{play_grade(edge)}</strong></div>"
        "</div>"
        f"<div style='margin-top:14px;'><span class='{play_badge_class(edge)}'>{play_grade(edge)}</span></div>"
        "</div>"
        "</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)

    render_value_meter(game)
    render_progress_bar("Confidence", confidence)

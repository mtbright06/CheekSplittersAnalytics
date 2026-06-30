import streamlit as st

from components.badges import play_badge_class, play_grade
from components.logos import team_logo_html
from components.team_colors import team_color


def render_compact_pick(game):
    matchup = game.get("matchup", {})
    model = game.get("model", {})
    odds = game.get("odds", {})
    sport = game.get("sport", "kbo").lower()

    play = model.get("play") or "No Play"
    market = model.get("market") or "Market"
    edge = model.get("edge") or 0
    confidence = model.get("confidence") or 0

    accent = team_color(play)

    html = (
        f"<div class='compact-pick' style='border-left:6px solid {accent};'>"
        "<div class='compact-logo'>"
        f"{team_logo_html(play, sport=sport)}"
        "</div>"
        "<div class='compact-body'>"
        f"<div class='compact-title'>{play}</div>"
        f"<div class='compact-subtitle'>{market} · {matchup.get('away')} @ {matchup.get('home')}</div>"
        f"<span class='{play_badge_class(edge)}'>{play_grade(edge)}</span>"
        "</div>"
        "<div class='compact-metrics'>"
        f"<div><span>Edge</span><strong>{edge:.1f}%</strong></div>"
        f"<div><span>Conf</span><strong>{confidence}</strong></div>"
        f"<div><span>Odds</span><strong>{odds.get('moneyline') or 'N/A'}</strong></div>"
        "</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)

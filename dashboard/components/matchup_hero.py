import streamlit as st

from components.logos import team_logo_html
from components.team_colors import team_color


def render_team_block(team_name, label, sport="kbo"):
    color = team_color(team_name)

    html = (
        f"<div class='matchup-team-block' style='border-left:7px solid {color};'>"
        f"<div class='matchup-logo-wrap'>{team_logo_html(team_name, sport)}</div>"
        "<div>"
        f"<div class='matchup-side-label'>{label}</div>"
        f"<div class='matchup-team-name'>{team_name}</div>"
        "</div>"
        "</div>"
    )

    st.markdown(html, unsafe_allow_html=True)


def render_matchup_hero(matchup, sport="kbo"):
    away = matchup["away"]
    home = matchup["home"]

    st.markdown("<div class='matchup-hero'>", unsafe_allow_html=True)

    left, middle, right = st.columns([5, 1, 5])

    with left:
        render_team_block(away, "Away", sport)

    with middle:
        st.markdown("<div class='matchup-vs'>@</div>", unsafe_allow_html=True)

    with right:
        render_team_block(home, "Home", sport)

    st.markdown("</div>", unsafe_allow_html=True)

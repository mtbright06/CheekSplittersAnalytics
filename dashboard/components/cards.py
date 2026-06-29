import streamlit as st

from components.badges import play_badge_class, play_grade
from components.commentary import splitter_commentary
from components.logos import matchup_title_html
from components.pitcher_grade import (
    grade_pitcher,
    grade_icon,
    grade_color,
    pitcher_tags,
)
from components.play_summary import render_play_summary
from components.progress import render_score_bar


def stat(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def is_pending_pitcher(pitcher):
    name = pitcher.get("name")
    return not name or name == "Unknown Starter"


def display_pitcher_name(pitcher):
    if is_pending_pitcher(pitcher):
        return "Starter Pending"
    return pitcher.get("name")


def pitcher_line(pitcher):
    if is_pending_pitcher(pitcher):
        return "Awaiting official starter confirmation"

    pieces = []

    if pitcher.get("throws"):
        pieces.append(f"{pitcher.get('throws')}HP")
    if pitcher.get("record"):
        pieces.append(pitcher.get("record"))
    if pitcher.get("era") is not None:
        pieces.append(f"{pitcher.get('era'):.2f} ERA")
    if pitcher.get("whip") is not None:
        pieces.append(f"{pitcher.get('whip'):.2f} WHIP")

    return " | ".join(pieces) if pieces else "Profile data limited"


def pitcher_grade_html(pitcher):
    if is_pending_pitcher(pitcher):
        return '<span class="pitcher-grade pending-grade">⏳ PENDING</span>'

    grade = grade_pitcher(pitcher)
    color = grade_color(grade)
    icon = grade_icon(grade)

    return (
        f'<span class="pitcher-grade" '
        f'style="background:{color}22; border-color:{color}; color:{color};">'
        f'{icon} {grade}</span>'
    )


def pitcher_tags_html(pitcher):
    if is_pending_pitcher(pitcher):
        return '<span class="mini-tag">Awaiting lineup data</span>'

    tags = pitcher_tags(pitcher)

    if not tags:
        return '<span class="mini-tag">Neutral profile</span>'

    html = []

    for text, kind in tags:
        css = "mini-good" if kind == "good" else "mini-bad"
        html.append(f'<span class="mini-tag {css}">{text}</span>')

    return " ".join(html)


def render_pitcher_card(title, pitcher):
    name = display_pitcher_name(pitcher)
    line = pitcher_line(pitcher)
    grade = pitcher_grade_html(pitcher)
    tags = pitcher_tags_html(pitcher)

    pitcher_html = (
        "<div class='pitcher-box'>"
        f"<div class='small-label'>{title}</div>"
        f"<div class='pitcher-name'>{name}</div>"
        f"<div class='muted'>{line}</div>"
        "<div style='margin-top: 10px;'>"
        f"{grade}"
        "</div>"
        f"<div class='pitcher-tags'>{tags}</div>"
        "</div>"
    )

    st.markdown(pitcher_html, unsafe_allow_html=True)

    cols = st.columns(4)
    cols[0].metric("IP", stat(pitcher.get("ip")))
    cols[1].metric("SO", stat(pitcher.get("so")))
    cols[2].metric("BB", stat(pitcher.get("bb")))
    cols[3].metric("HR", stat(pitcher.get("hr_allowed")))

    cols = st.columns(3)
    cols[0].metric("K/9", stat(pitcher.get("k_rate")))
    cols[1].metric("BB/9", stat(pitcher.get("bb_rate")))
    cols[2].metric("HR/9", stat(pitcher.get("hr9")))


def render_signals(signals):
    if not signals:
        st.markdown(
            '<div class="muted">No signals available.</div>',
            unsafe_allow_html=True,
        )
        return

    max_value = max(
        [abs(float(signal.get("value") or 0)) for signal in signals] + [1]
    )

    for signal in signals:
        render_score_bar(
            signal.get("name"),
            signal.get("value") or 0,
            max_value=max_value,
        )


def render_reasons(reasons):
    if not reasons:
        st.markdown(
            '<div class="muted">No reasons available.</div>',
            unsafe_allow_html=True,
        )
        return

    for reason in reasons:
        st.markdown(
            f"<div class='reason'>✅ {reason}</div>",
            unsafe_allow_html=True,
        )


def render_game(game):
    matchup = game["matchup"]

    st.markdown("<div class='sharp-card'>", unsafe_allow_html=True)

    st.markdown(
        matchup_title_html(matchup["away"], matchup["home"], sport="kbo"),
        unsafe_allow_html=True,
    )

    render_play_summary(game)

    st.markdown(
        f"<div class='splitter-comment'>{splitter_commentary(game)}</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    pitching = game["pitching"]
    left, right = st.columns(2)

    with left:
        render_pitcher_card(f"{matchup['away']} Starter", pitching["away"])

    with right:
        render_pitcher_card(f"{matchup['home']} Starter", pitching["home"])

    st.markdown("---")

    model = game["model"]
    signal_col, reason_col = st.columns(2)

    with signal_col:
        st.markdown("#### Model Signals")
        render_signals(model.get("signals", []))

    with reason_col:
        st.markdown("#### Why We Like It")
        render_reasons(model.get("reasons", []))

    st.markdown("</div>", unsafe_allow_html=True)


grade_label = play_grade
badge_class = play_badge_class

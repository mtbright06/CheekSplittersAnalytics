import streamlit as st

from components.pitcher_grade import (
    grade_pitcher,
    grade_icon,
    grade_color,
    pitcher_tags,
)


def grade_label(edge):
    if edge is None:
        return "NO DATA"
    if edge >= 10:
        return "CHEEK RIPPER 🔥"
    if edge >= 7:
        return "STRONG PLAY"
    if edge >= 5:
        return "PLAYABLE"
    if edge >= 2:
        return "LEAN"
    return "PASS"


def badge_class(edge):
    if edge is None:
        return "badge"
    if edge >= 7:
        return "badge badge-green"
    if edge >= 2:
        return "badge badge-gold"
    return "badge"


def stat(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def display_pitcher_name(pitcher):
    name = pitcher.get("name")

    if not name or name == "Unknown Starter":
        return "Starter Pending"

    return name


def pitcher_line(pitcher):
    name = display_pitcher_name(pitcher)

    if name == "Starter Pending":
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

    if pieces:
        return f"{name} ({' | '.join(pieces)})"

    return name


def render_pitcher_grade(pitcher):
    if not pitcher.get("name") or pitcher.get("name") == "Unknown Starter":
        return """
        <span class="pitcher-grade pending-grade">
            ⏳ PENDING
        </span>
        """

    grade = grade_pitcher(pitcher)
    color = grade_color(grade)
    icon = grade_icon(grade)

    return f"""
    <span class="pitcher-grade"
          style="background:{color}22; border-color:{color}; color:{color};">
        {icon} {grade}
    </span>
    """


def render_pitcher_tags(pitcher):
    if not pitcher.get("name") or pitcher.get("name") == "Unknown Starter":
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

    st.markdown(
        f"""
        <div class="pitcher-box">
            <div class="small-label">{title}</div>
            <div class="pitcher-name">
                {name}
            </div>
            <div class="muted">{pitcher_line(pitcher)}</div>
            <div style="margin-top: 10px;">
                {render_pitcher_grade(pitcher)}
            </div>
            <div class="pitcher-tags">
                {render_pitcher_tags(pitcher)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    for signal in signals:
        st.markdown(
            f"""
            <div class="signal-row">
                <span>{signal.get("name")}</span>
                <strong>{signal.get("value")}</strong>
            </div>
            """,
            unsafe_allow_html=True,
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
            f'<div class="reason">✅ {reason}</div>',
            unsafe_allow_html=True,
        )


def render_game(game):
    matchup = game["matchup"]
    model = game["model"]
    pitching = game["pitching"]
    odds = game["odds"]

    edge = model.get("edge")
    confidence = model.get("confidence")

    st.markdown('<div class="sharp-card">', unsafe_allow_html=True)

    top = st.columns([3, 1, 1, 1])
    top[0].markdown(f"### {matchup['away']} @ {matchup['home']}")
    top[1].metric("Play", model.get("play"))
    top[2].metric("Edge", f"{edge}%")
    top[3].metric("Confidence", f"{confidence}/100")

    st.markdown(
        f"""
        <span class="{badge_class(edge)}">{grade_label(edge)}</span>
        <span class="muted">&nbsp; {model.get('market')} · Odds: {odds.get('moneyline')} · Book: {odds.get('book_probability')}%</span>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    left, right = st.columns(2)

    with left:
        render_pitcher_card(f"{matchup['away']} Starter", pitching["away"])

    with right:
        render_pitcher_card(f"{matchup['home']} Starter", pitching["home"])

    st.markdown("---")

    signal_col, reason_col = st.columns(2)

    with signal_col:
        st.markdown("#### Model Signals")
        render_signals(model.get("signals", []))

    with reason_col:
        st.markdown("#### Why We Like It")
        render_reasons(model.get("reasons", []))

    st.markdown("</div>", unsafe_allow_html=True)

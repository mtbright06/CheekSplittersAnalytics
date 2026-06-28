import streamlit as st


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


def pitcher_tag(label, value, kind):
    if value is None:
        return ""

    good = False
    bad = False

    if kind == "era":
        good = value <= 3.75
        bad = value >= 5.00
    elif kind == "whip":
        good = value <= 1.25
        bad = value >= 1.45
    elif kind == "k9":
        good = value >= 8.5
        bad = value <= 5.5
    elif kind == "bb9":
        good = value <= 2.5
        bad = value >= 4.0
    elif kind == "hr9":
        good = value <= 0.8
        bad = value >= 1.4

    css = "mini-tag"
    if good:
        css += " mini-good"
    elif bad:
        css += " mini-bad"

    return f'<span class="{css}">{label}: {stat(value)}</span>'


def pitcher_insights(pitcher):
    tags = [
        pitcher_tag("ERA", pitcher.get("era"), "era"),
        pitcher_tag("WHIP", pitcher.get("whip"), "whip"),
        pitcher_tag("K/9", pitcher.get("k_rate"), "k9"),
        pitcher_tag("BB/9", pitcher.get("bb_rate"), "bb9"),
        pitcher_tag("HR/9", pitcher.get("hr9"), "hr9"),
    ]

    tags = [tag for tag in tags if tag]

    if not tags:
        return '<span class="mini-tag">No profile data</span>'

    return " ".join(tags)


def pitcher_line(pitcher):
    name = pitcher.get("name") or "Unknown Starter"
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


def render_pitcher_card(title, pitcher):
    st.markdown(
        f"""
        <div class="pitcher-box">
            <div class="small-label">{title}</div>
            <div class="pitcher-name">{pitcher.get("name") or "Unknown Starter"}</div>
            <div class="muted">{pitcher_line(pitcher)}</div>
            <div class="pitcher-tags">{pitcher_insights(pitcher)}</div>
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
        st.markdown('<div class="muted">No signals available.</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="muted">No reasons available.</div>', unsafe_allow_html=True)
        return

    for reason in reasons:
        st.markdown(f'<div class="reason">✅ {reason}</div>', unsafe_allow_html=True)


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

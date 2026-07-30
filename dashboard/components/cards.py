import streamlit as st
from components.explorer import render_recommendation_explorer
from components.badges import play_badge_class, play_grade
from components.commentary import splitter_commentary
from components.matchup_hero import render_matchup_hero
from components.mlb.workstation import render_mlb_workstation_game
from components.pitcher_grade import (
    grade_pitcher,
    grade_icon,
    grade_color,
    pitcher_tags,
)
from components.play_summary import render_play_summary
from components.progress import render_score_bar
from models import game


def stat(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def is_pending_pitcher(pitcher):
    name = pitcher.get("name")
    return not name or name == "Unknown Starter"


def is_unconfirmed_pitching_data(pitcher):
    return (
        is_pending_pitcher(pitcher)
        and any(
            pitcher.get(key) is not None
            for key in ("era", "whip", "ip", "so", "bb", "hr_allowed")
        )
    )


def display_pitcher_name(pitcher):
    if is_unconfirmed_pitching_data(pitcher):
        return "Unconfirmed Pitching Data"

    if is_pending_pitcher(pitcher):
        return "Starter Pending"
    return pitcher.get("name")


def pitcher_line(pitcher):
    if is_unconfirmed_pitching_data(pitcher):
        return "Starter identity unavailable; pitching data is not confirmed starter data"

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
    if is_unconfirmed_pitching_data(pitcher):
        return '<span class="pitcher-grade pending-grade">DATA UNCONFIRMED</span>'

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
    if is_unconfirmed_pitching_data(pitcher):
        return '<span class="mini-tag">Starter identity unavailable</span>'

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

    cols = st.columns(4, gap="small")
    cols[0].metric("IP", stat(pitcher.get("ip")))
    cols[1].metric("SO", stat(pitcher.get("so")))
    cols[2].metric("BB", stat(pitcher.get("bb")))
    cols[3].metric("HR", stat(pitcher.get("hr_allowed")))

    cols = st.columns(3, gap="small")
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


def render_confidence_breakdown(breakdown):
    st.markdown("#### Confidence Breakdown")

    if not isinstance(breakdown, dict) or not breakdown:
        st.markdown(
            '<div class="muted">Confidence inputs are unavailable.</div>',
            unsafe_allow_html=True,
        )
        return

    columns = st.columns(len(breakdown))

    for column, (name, value) in zip(columns, breakdown.items()):
        label = name.replace("_", " ").title()
        try:
            display = f"{float(value):+.1f}"
        except (TypeError, ValueError):
            display = stat(value)
        column.metric(label, display)


def render_bullpen_details(game):
    teams = game.get("teams", {})
    away = teams.get("away", {})
    home = teams.get("home", {})
    away_bullpen = away.get("bullpen", {})
    home_bullpen = home.get("bullpen", {})

    if not isinstance(away_bullpen, dict) and not isinstance(home_bullpen, dict):
        return

    st.markdown("#### Bullpen Details")
    away_column, home_column = st.columns(2)

    for column, team, bullpen in (
        (away_column, game["matchup"].get("away", "Away"), away_bullpen),
        (home_column, game["matchup"].get("home", "Home"), home_bullpen),
    ):
        bullpen = bullpen if isinstance(bullpen, dict) else {}
        with column:
            st.markdown(f"**{team}**")
            metrics = st.columns(3)
            metrics[0].metric("ERA", stat(bullpen.get("era")))
            metrics[1].metric("WHIP", stat(bullpen.get("whip")))
            metrics[2].metric("Last 7 ERA", stat(bullpen.get("last7_era")))
            st.caption(
                " · ".join(
                    [
                        f"Availability: {bullpen.get('availability_status') or 'Unavailable'}",
                        f"Source: {bullpen.get('source_quality') or bullpen.get('data_source') or 'Unavailable'}",
                    ]
                )
            )


def render_intelligence_details(game):
    matchup = game["matchup"]
    pitching = game["pitching"]
    model = game["model"]

    st.markdown("#### Pitching")
    left, right = st.columns(2)

    sport = game.get("sport", "").lower()
    away_title = _pitching_title(matchup["away"], pitching["away"], sport)
    home_title = _pitching_title(matchup["home"], pitching["home"], sport)

    with left:
        render_pitcher_card(away_title, pitching["away"])

    with right:
        render_pitcher_card(home_title, pitching["home"])

    if sport == "mlb":
        st.markdown("---")
        render_bullpen_details(game)

    st.markdown("---")
    signal_col, reason_col = st.columns(2)

    with signal_col:
        st.markdown("#### Model Signals")
        render_signals(model.get("signals", []))

    with reason_col:
        st.markdown("#### Why We Like It")
        render_reasons(model.get("reasons", []))
        render_confidence_breakdown(model.get("confidence_breakdown"))


def _pitching_title(team_name, pitcher, sport):
    if sport == "kbo" and is_unconfirmed_pitching_data(pitcher):
        return f"{team_name} Pitching Data"

    return f"{team_name} Starter"


def render_game(
    game,
    *,
    hammer_score=None,
):
    matchup = game["matchup"]
    sport = game.get("sport", "kbo").lower()

    if sport == "mlb":
        render_mlb_workstation_game(game)
        return

    else:
        render_matchup_hero(matchup, sport=sport)
        render_play_summary(game)

    st.markdown(
        f"<div class='splitter-comment'>{splitter_commentary(game)}</div>",
        unsafe_allow_html=True,
    )

    render_recommendation_explorer(
        game,
        details_renderer=render_intelligence_details,
    )


grade_label = play_grade
badge_class = play_badge_class

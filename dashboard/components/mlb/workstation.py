from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st

from components.badges import recommendation_badge_html
from components.logos import team_logo_html
from components.team_colors import team_color

EASTERN = ZoneInfo("America/New_York")


def render_mlb_workstation_header(card: dict) -> None:
    games = card.get("games", [])
    slate_date = _slate_date(games)
    freshness = _display_datetime(card.get("generated_at"))

    left, right = st.columns([1, 0.28], gap="small")

    with left:
        parts = ["<div class='mlb-workstation-toolbar'>"]
        parts.append("<strong>MLB Full Slate</strong>")
        if slate_date:
            parts.append(f"<span>{slate_date}</span>")
        if freshness:
            parts.append(f"<span class='mlb-fresh-dot'></span><span>Data as of {freshness}</span>")
        parts.append("</div>")
        st.markdown("".join(parts), unsafe_allow_html=True)

    with right:
        if st.button("Refresh", key="mlb_full_slate_refresh"):
            st.rerun()


def render_mlb_workstation_game(game: dict) -> None:
    matchup = game.get("matchup", {})
    model = game.get("model", {})
    totals = game.get("totals_model", {})

    away = matchup.get("away", "Away")
    home = matchup.get("home", "Home")
    projected = model.get("play") or "Unavailable"

    st.markdown(
        _matchup_banner_html(
            away=away,
            home=home,
            venue=game.get("venue"),
            start=game.get("commence_time"),
            projected=projected,
            confidence=model.get("confidence"),
            market_edge=model.get("edge"),
        ),
        unsafe_allow_html=True,
    )

    moneyline_col, totals_col = st.columns(2, gap="small")

    with moneyline_col:
        st.markdown(_moneyline_panel_html(game), unsafe_allow_html=True)

    with totals_col:
        st.markdown(_totals_panel_html(game), unsafe_allow_html=True)

    render_analytics_workspace(game)


def render_analytics_workspace(game: dict) -> None:
    workspaces = _analytics_workspaces()
    key = f"mlb_analytics_workspace_{game.get('game_id') or 'active'}"
    if key not in st.session_state:
        st.session_state[key] = None

    st.markdown("<div class='mlb-analytics-controls'>", unsafe_allow_html=True)
    columns = st.columns(len(workspaces), gap="small")
    for column, (workspace, subtitle) in zip(columns, workspaces.items()):
        active = st.session_state[key] == workspace
        with column:
            if st.button(
                f"{workspace} · {subtitle}",
                key=f"{key}_{workspace.lower().replace(' ', '_')}",
                width="stretch",
                type="primary" if active else "secondary",
            ):
                st.session_state[key] = None if active else workspace

    st.markdown("</div>", unsafe_allow_html=True)

    active_workspace = st.session_state.get(key)
    if active_workspace:
        _render_workspace_content(game, active_workspace)


def _analytics_workspaces() -> dict[str, str]:
    return {
        "Pitchers": "Starting",
        "Bullpen": "Relievers",
        "Decision": "Builder",
        "Model View": "Components",
        "Weather": "Conditions",
    }


def _render_workspace_content(game: dict, workspace: str) -> None:
    st.markdown(
        f"<section class='mlb-workstation-card mlb-analytics-workspace'><h4>{escape(workspace)}</h4>",
        unsafe_allow_html=True,
    )

    if workspace == "Pitchers":
        _render_pitchers_workspace(game)
    elif workspace == "Bullpen":
        _render_bullpens_workspace(game)
    elif workspace == "Decision":
        _render_decision_workspace(game)
    elif workspace == "Model View":
        _render_model_drivers_workspace(game)
    elif workspace == "Weather":
        _empty_workspace("Weather inputs are not available for this matchup.")

    st.markdown("</section>", unsafe_allow_html=True)


def _render_pitchers_workspace(game: dict) -> None:
    pitching = game.get("pitching")
    matchup = game.get("matchup", {})
    if not isinstance(pitching, dict):
        _empty_workspace("Starting pitcher data is not available for this matchup.")
        return

    away_pitcher = pitching.get("away")
    home_pitcher = pitching.get("home")
    if not isinstance(away_pitcher, dict) and not isinstance(home_pitcher, dict):
        _empty_workspace("Starting pitcher data is not available for this matchup.")
        return

    from components.cards import render_pitcher_card

    left, right = st.columns(2, gap="medium")
    with left:
        if isinstance(away_pitcher, dict):
            render_pitcher_card(f"{matchup.get('away', 'Away')} Starter", away_pitcher)
        else:
            _empty_workspace("Away starter data is unavailable.")
    with right:
        if isinstance(home_pitcher, dict):
            render_pitcher_card(f"{matchup.get('home', 'Home')} Starter", home_pitcher)
        else:
            _empty_workspace("Home starter data is unavailable.")


def _render_bullpens_workspace(game: dict) -> None:
    teams = game.get("teams", {})
    away = teams.get("away", {}) if isinstance(teams, dict) else {}
    home = teams.get("home", {}) if isinstance(teams, dict) else {}
    away_bullpen = away.get("bullpen", {}) if isinstance(away, dict) else {}
    home_bullpen = home.get("bullpen", {}) if isinstance(home, dict) else {}

    if not isinstance(away_bullpen, dict) and not isinstance(home_bullpen, dict):
        _empty_workspace("Bullpen details are not available for this matchup.")
        return
    if not away_bullpen and not home_bullpen:
        _empty_workspace("Bullpen details are not available for this matchup.")
        return

    from components.cards import render_bullpen_details

    render_bullpen_details(game)


def _render_decision_workspace(game: dict) -> None:
    from components.explorer.recommendation_explorer import _render_decision

    _render_decision(game)


def _render_model_drivers_workspace(game: dict) -> None:
    model = game.get("model", {})
    if not isinstance(model, dict):
        _empty_workspace("Model driver details are not available for this matchup.")
        return

    from components.cards import (
        render_confidence_breakdown,
        render_reasons,
        render_signals,
    )

    left, right = st.columns(2, gap="medium")
    with left:
        st.markdown("#### Model Signals")
        render_signals(model.get("signals", []))
    with right:
        st.markdown("#### Why We Like It")
        render_reasons(model.get("reasons", []))
        render_confidence_breakdown(model.get("confidence_breakdown"))


def _empty_workspace(message: str) -> None:
    st.markdown(
        f"<div class='mlb-analytics-empty'>{escape(message)}</div>",
        unsafe_allow_html=True,
    )


def _matchup_banner_html(
    *,
    away: str,
    home: str,
    venue: Any,
    start: Any,
    projected: str,
    confidence: Any,
    market_edge: Any,
) -> str:
    return (
        "<section class='mlb-workstation-card mlb-matchup-workstation'>"
        "<div class='mlb-matchup-row'>"
        f"{_team_html(away, 'Away', align='left')}"
        "<div class='mlb-matchup-center'>"
        "<div class='mlb-matchup-at'>@</div>"
        f"{_optional_div('mlb-matchup-time', _display_time(start))}"
        f"{_optional_div('mlb-matchup-venue', venue)}"
        "</div>"
        f"{_team_html(home, 'Home', align='right')}"
        "</div>"
        "<div class='mlb-decision-summary'>"
        "<div class='mlb-decision-kicker'>SharpStack Decision</div>"
        "<div class='mlb-decision-object'>"
        f"<strong class='mlb-decision-pick'>{escape(str(projected))}</strong>"
        "<div class='mlb-decision-strength'>"
        f"{_decision_item('Confidence', _confidence(confidence))}"
        f"{_decision_item('Market Edge', _percent(market_edge, signed=True), tone='positive')}"
        "</div>"
        "</div>"
        "</div>"
        "</section>"
    )


def _team_html(team: str, label: str, *, align: str) -> str:
    color = team_color(team)
    return (
        f"<div class='mlb-matchup-team mlb-matchup-team--{align}' style='--team-accent:{color};'>"
        f"<div class='mlb-team-logo'>{team_logo_html(team, 'mlb')}</div>"
        "<div class='mlb-team-copy'>"
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(str(team))}</strong>"
        "</div>"
        "</div>"
    )


def _moneyline_panel_html(game: dict) -> str:
    model = game.get("model", {})
    odds = game.get("odds", {})
    recommendation = model.get("recommendation") or "PASS"
    current_odds = _odds_text(odds.get("moneyline") or odds.get("american_odds"))
    fair_price = _odds_text(odds.get("reference_price"))
    edge = _percent(model.get("edge"), signed=True)
    book_probability = _percent(odds.get("book_probability"))
    model_probability = _percent(model.get("model_probability"))
    status = odds.get("market_status") or odds.get("freshness_status")

    rows = [
        ("Fair Price", fair_price),
        ("Market Edge", edge),
        ("Market Status", status),
    ]
    explanation = _moneyline_explanation(model, odds)

    return _market_panel_html(
        title="Moneyline",
        recommendation=recommendation,
        primary_label=model.get("play") or "Selection",
        primary_value=current_odds,
        probability_pair=("Book Probability", book_probability, "Model Win Probability", model_probability),
        rows=rows,
        explanation=explanation,
        tone="moneyline",
    )


def _totals_panel_html(game: dict) -> str:
    totals = game.get("totals_model", {})
    recommendation = totals.get("recommendation") or "PASS"
    selection = _totals_selection(totals)
    rows = [
        ("Projected Total", _number(totals.get("projected_total"))),
        ("Market Total", _number(totals.get("market_total"))),
        ("Edge", _number(totals.get("edge"), signed=True)),
        ("Confidence", _confidence(totals.get("confidence"))),
    ]
    explanation = _totals_explanation(totals)

    return _market_panel_html(
        title="Totals",
        recommendation=recommendation,
        primary_label=selection,
        primary_value=_number(totals.get("market_total")),
        probability_pair=None,
        rows=rows,
        explanation=explanation,
        tone="totals",
    )


def _market_panel_html(
    *,
    title: str,
    recommendation: str,
    primary_label: Any,
    primary_value: Any,
    probability_pair: tuple[str, Any, str, Any] | None,
    rows: list[tuple[str, Any]],
    explanation: str | None,
    tone: str,
) -> str:
    rendered_rows = "".join(
        _summary_row_html(label, value)
        for label, value in rows
        if _is_available(value)
    )
    probability_html = (
        _probability_pair_html(*probability_pair)
        if probability_pair and (
            _is_available(probability_pair[1]) or _is_available(probability_pair[3])
        )
        else ""
    )
    explanation_html = (
        f"<div class='mlb-market-explanation'>{explanation}</div>"
        if explanation
        else ""
    )
    return (
        f"<section class='mlb-workstation-card mlb-market-panel mlb-market-panel--{tone}'>"
        "<div class='mlb-market-heading'>"
        f"<h3>{escape(title)}</h3>"
        f"{recommendation_badge_html(recommendation)}"
        "</div>"
        f"{_primary_market_line_html(primary_label, primary_value)}"
        f"{probability_html}"
        f"<div class='mlb-market-summary'>{rendered_rows}</div>"
        f"{explanation_html}"
        "</section>"
    )


def _primary_market_line_html(label: Any, value: Any) -> str:
    if not _is_available(label) and not _is_available(value):
        return ""
    return (
        "<div class='mlb-market-primary'>"
        f"<strong>{escape(str(label))}</strong>"
        f"<span>{escape(str(value))}</span>"
        "</div>"
    )


def _probability_pair_html(
    left_label: str,
    left_value: Any,
    right_label: str,
    right_value: Any,
) -> str:
    return (
        "<div class='mlb-probability-pair'>"
        f"{_probability_cell_html(left_label, left_value)}"
        f"{_probability_cell_html(right_label, right_value)}"
        "</div>"
    )


def _probability_cell_html(label: str, value: Any) -> str:
    if not _is_available(value):
        return ""
    return (
        "<div>"
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(str(value))}</strong>"
        "</div>"
    )


def _summary_row_html(label: str, value: Any) -> str:
    return (
        "<div class='mlb-summary-row'>"
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(str(value))}</strong>"
        "</div>"
    )


def _is_available(value: Any) -> bool:
    return value not in (None, "", "N/A", "Unavailable")


def _moneyline_explanation(model: dict, odds: dict) -> str | None:
    probability = _percent(model.get("model_probability"))
    edge = _percent(model.get("edge"), signed=True)
    play = model.get("play")
    status = odds.get("market_status") or odds.get("freshness_status")
    pieces = []
    if play and probability != "Unavailable":
        pieces.append(
            f"Model projects {escape(str(play))} at "
            f"<strong class='mlb-explanation-accent'>{escape(probability)}</strong>."
        )
    if edge != "Unavailable":
        pieces.append(
            f"Edge: <strong class='mlb-explanation-accent'>{escape(edge)}</strong>."
        )
    if status:
        pieces.append(f"Status: {escape(str(status))}.")
    return " ".join(pieces[:2]) or None


def _totals_explanation(totals: dict) -> str | None:
    projected = _number(totals.get("projected_total"))
    market = _number(totals.get("market_total"))
    edge = _number(totals.get("edge"), signed=True)
    if projected != "Unavailable" and market != "Unavailable":
        return (
            f"Projected total: <strong>{escape(projected)}</strong> vs market "
            f"{escape(market)}. Edge: "
            f"<strong class='mlb-explanation-accent'>{escape(edge)}</strong>."
        )
    reasons = totals.get("reasons")
    if isinstance(reasons, list) and reasons:
        return escape(str(reasons[0]))
    return None


def _totals_selection(totals: dict) -> str:
    selection = totals.get("selection")
    market_total = _number(totals.get("market_total"))
    if _is_available(selection) and _is_available(market_total):
        return f"{selection} {market_total}"
    if _is_available(selection):
        return str(selection)
    return "Selection"


def _decision_item(
    label: str,
    value: Any,
    *,
    primary: bool = False,
    tone: str | None = None,
) -> str:
    primary_class = " mlb-decision-item--primary" if primary else ""
    tone_class = f" mlb-decision-item--{tone}" if tone else ""
    return (
        f"<div class='mlb-decision-item{primary_class}{tone_class}'>"
        f"<span>{escape(label)}</span>"
        f"<strong>{escape(str(value))}</strong>"
        "</div>"
    )


def _optional_div(css_class: str, value: Any) -> str:
    if value in (None, ""):
        return ""
    return f"<div class='{css_class}'>{escape(str(value))}</div>"


def _display_datetime(value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if not parsed:
        return None
    parsed = parsed.astimezone(EASTERN) if parsed.tzinfo else parsed
    return f"{_date_label(parsed)} {_time_label(parsed)}"


def _display_time(value: Any) -> str | None:
    parsed = _parse_datetime(value)
    if not parsed:
        return None
    parsed = parsed.astimezone(EASTERN) if parsed.tzinfo else parsed
    return f"{_time_label(parsed)} ET"


def _slate_date(games: list[dict]) -> str | None:
    for game in games:
        parsed = _parse_datetime(game.get("commence_time"))
        if parsed:
            parsed = parsed.astimezone(EASTERN) if parsed.tzinfo else parsed
            return _date_label(parsed)
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _date_label(value: datetime) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def _time_label(value: datetime) -> str:
    hour = value.hour % 12 or 12
    return f"{hour}:{value.minute:02d} {value.strftime('%p')}"


def _percent(value: Any, *, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unavailable"
    if abs(number) <= 1:
        number *= 100
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:.1f}%"


def _confidence(value: Any) -> str:
    try:
        return f"{float(value):.1f} / 100"
    except (TypeError, ValueError):
        return "Unavailable"


def _number(value: Any, *, signed: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unavailable"
    prefix = "+" if signed and number > 0 else ""
    return f"{prefix}{number:.2f}"


def _odds_text(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "Unavailable"
    return f"{number:+.0f}"

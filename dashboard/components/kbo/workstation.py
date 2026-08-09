from __future__ import annotations

import html
from typing import Any

import streamlit as st

from components.badges import recommendation_badge_html
from components.logos import team_logo_html
from components.status_pill import status_pill_html


def _safe(value: Any, default: str = "N/A") -> str:
    if value in (None, "", "None"):
        return default

    return str(value)


def _esc(value: Any, default: str = "N/A") -> str:
    return html.escape(_safe(value, default))


def _number(value: Any, decimals: int = 1, default: str = "N/A") -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return default


def _probability(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/A"

    if abs(number) <= 1:
        number *= 100

    return f"{number:.1f}%"


def _odds(value: Any) -> str:
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        return "Unavailable"

    return f"+{number}" if number > 0 else str(number)


def _signed_percent(value: Any) -> tuple[str, bool]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—", False

    return f"{number:+.1f}%", number > 0


def _market_status(odds: dict) -> str:
    if odds.get("real_market_loaded"):
        return "REAL MARKET"

    return "MODEL ONLY"


def _pitcher_line(pitcher: dict) -> str:
    pieces = []

    if pitcher.get("record"):
        pieces.append(str(pitcher.get("record")))

    if pitcher.get("era") is not None:
        pieces.append(f"{_number(pitcher.get('era'), 2)} ERA")

    if pitcher.get("whip") is not None:
        pieces.append(f"{_number(pitcher.get('whip'), 2)} WHIP")

    if pitcher.get("throws"):
        pieces.append(f"{pitcher.get('throws')}HP")

    return " · ".join(pieces) if pieces else "Starter data limited"


def _metric(label: str, value: Any, *, tone: str = "", quiet: bool = False) -> str:
    tone_class = f" kbo-workstation-metric--{tone}" if tone else ""
    quiet_class = " kbo-workstation-metric--quiet" if quiet else ""

    return (
        f"<div class='kbo-workstation-metric{tone_class}{quiet_class}'>"
        f"<span>{html.escape(label)}</span>"
        f"<strong>{_esc(value)}</strong>"
        "</div>"
    )


def _decision_metrics(
    *,
    reliability: Any,
    model_strength: Any,
    odds_value: str,
    edge_value: str,
    edge_positive: bool,
    market_missing: bool,
) -> str:
    metrics = [
        _metric("Model Strength", _number(model_strength), tone="success"),
        _metric("Reliability", _number(reliability)),
    ]

    if market_missing:
        metrics.append(
            _metric("Market Data", "Unavailable", quiet=True)
        )
    else:
        metrics.extend(
            [
                _metric("Odds", odds_value),
                _metric(
                    "Edge",
                    edge_value,
                    tone="success" if edge_positive else "",
                ),
            ]
        )

    return "".join(metrics)


def _signal_items(
    signals: list[dict],
    inactive_components: list[dict] | None = None,
) -> str:
    inactive_components = inactive_components or []
    inactive_names = {
        str(component.get("name") or "")
        for component in inactive_components
        if isinstance(component, dict)
    }
    active_signals = [
        signal
        for signal in signals
        if signal.get("name") not in inactive_names
    ]

    if not active_signals and not inactive_components:
        return "<div class='kbo-workstation-muted'>No model signals available.</div>"

    items = []

    for signal in active_signals[:4]:
        name = signal.get("name")
        value = signal.get("value")

        items.append(
            "<div class='kbo-workstation-signal'>"
            f"<span>{_esc(name)}</span>"
            f"<strong>{_number(value, 2)}</strong>"
            "<small>Contribution</small>"
            "</div>"
        )

    for component in inactive_components:
        if not isinstance(component, dict):
            continue

        items.append(
            "<div class='kbo-workstation-signal kbo-workstation-signal--inactive'>"
            f"<span>{_esc(component.get('name'))}</span>"
            "<strong>Not modeled</strong>"
            f"<small>{_esc(component.get('reason'), 'Inactive')}</small>"
            "</div>"
        )

    return "".join(items)


def _reliability_items(breakdown: dict) -> str:
    if not isinstance(breakdown, dict):
        return ""

    concerns = []

    for label, key in [
        ("Starter identity", "starter_identity"),
        ("Starter stats", "starter_stats"),
        ("Offense data", "offense"),
        ("Schedule mapping", "schedule_mapping"),
        ("Provider quality", "provider_quality"),
    ]:
        try:
            value = float(breakdown.get(key) or 0)
        except (TypeError, ValueError):
            value = 0.0

        if value < 0:
            concerns.append(f"{label} {value:.0f}")

    if not concerns:
        return _metric("Reliability Concerns", "None")

    return _metric("Reliability Concerns", ", ".join(concerns), quiet=True)


def _reason_items(reasons: list[Any]) -> str:
    if not reasons:
        return "<div class='kbo-workstation-muted'>No supporting reasons available.</div>"

    return "".join(
        f"<li>{_esc(reason)}</li>"
        for reason in reasons[:5]
        if reason
    )


def kbo_workstation_html(game: dict) -> str:
    matchup = game.get("matchup", {})
    model = game.get("model", {})
    odds = game.get("odds", {})
    pitching = game.get("pitching", {})
    teams = game.get("teams", {})

    away = _safe(matchup.get("away"), "Away")
    home = _safe(matchup.get("home"), "Home")
    play = _safe(model.get("play"), "No Play")
    recommendation = _safe(model.get("recommendation"), "PASS")
    status = _market_status(odds)
    market = _safe(model.get("market") or odds.get("market"), "Moneyline")
    time = _safe(game.get("start_time"), "Time TBD")
    venue = _safe(game.get("venue"), "Venue TBD")
    reliability = (
        model.get("model_reliability")
        if model.get("model_reliability") is not None
        else model.get("confidence")
    )
    model_strength = (
        model.get("model_strength")
        if model.get("model_strength") is not None
        else model.get("model_probability")
    )
    edge = model.get("edge")
    moneyline = odds.get("moneyline") or odds.get("american_odds")
    sportsbook = _safe(odds.get("sportsbook"), "Unavailable")
    quotes_compared = odds.get("quotes_compared")
    confidence_breakdown = model.get("confidence_breakdown", {})
    confidence_basis = (
        confidence_breakdown.get("basis")
        if isinstance(confidence_breakdown, dict)
        else None
    )
    market_source = (
        sportsbook
        if odds.get("real_market_loaded")
        else "Model-only"
    )

    away_pitcher = pitching.get("away", {}) or {}
    home_pitcher = pitching.get("home", {}) or {}
    away_team = teams.get("away", {}) if isinstance(teams, dict) else {}
    away_offense = (
        away_team.get("offense", {})
        if isinstance(away_team, dict)
        else {}
    )
    offense_source = away_offense.get("offense_source") or "Unknown"

    edge_value, edge_positive = _signed_percent(edge)
    odds_value = _odds(moneyline)
    market_missing = not odds.get("real_market_loaded")

    return (
        "<section class='kbo-workstation-card'>"
        "<div class='kbo-workstation-matchup'>"
        "<div class='kbo-workstation-team'>"
        f"<div class='kbo-workstation-logo'>{team_logo_html(away, 'kbo')}</div>"
        "<div>"
        "<div class='kbo-workstation-side'>Away</div>"
        f"<div class='kbo-workstation-team-name'>{_esc(away)}</div>"
        "</div>"
        "</div>"
        "<div class='kbo-workstation-center'>"
        "<div class='kbo-workstation-at'>@</div>"
        f"<div class='kbo-workstation-time'>{_esc(time)}</div>"
        f"<div class='kbo-workstation-venue'>{_esc(venue)}</div>"
        "</div>"
        "<div class='kbo-workstation-team kbo-workstation-team--right'>"
        f"<div class='kbo-workstation-logo'>{team_logo_html(home, 'kbo')}</div>"
        "<div>"
        "<div class='kbo-workstation-side'>Home</div>"
        f"<div class='kbo-workstation-team-name'>{_esc(home)}</div>"
        "</div>"
        "</div>"
        "</div>"
        "<div class='kbo-workstation-decision'>"
        "<div class='kbo-workstation-decision-main'>"
        f"<div class='kbo-workstation-label'>SharpStack Recommendation · {_esc(play)}</div>"
        "<div class='kbo-workstation-badges'>"
        f"{recommendation_badge_html(recommendation, model_only=not odds.get('real_market_loaded'))}"
        f"{status_pill_html(status)}"
        f"<span class='kbo-workstation-market'>{_esc(market)}</span>"
        "</div>"
        "</div>"
        "<div class='kbo-workstation-decision-metrics'>"
        f"{_decision_metrics(reliability=reliability, model_strength=model_strength, odds_value=odds_value, edge_value=edge_value, edge_positive=edge_positive, market_missing=market_missing)}"
        "</div>"
        "</div>"
        "<div class='kbo-workstation-panels'>"
        "<div class='kbo-workstation-panel'>"
        "<div class='kbo-workstation-panel-title'>Model Snapshot</div>"
        "<div class='kbo-workstation-grid'>"
        f"{_metric('Market', market)}"
        f"{_metric('Source', market_source, quiet=market_missing)}"
        f"{_metric('Offense Data', offense_source, quiet=offense_source != 'LIVE_TEAM_SPLITS')}"
        f"{_metric('Quotes', _number(quotes_compared, 0, '0'), quiet=market_missing)}"
        f"{_metric('Basis', confidence_basis or 'Ordinal model score')}"
        f"{_reliability_items(confidence_breakdown)}"
        "</div>"
        "<div class='kbo-workstation-signals'>"
        f"{_signal_items(model.get('signals', []), model.get('inactive_components', []))}"
        "</div>"
        "</div>"
        "<div class='kbo-workstation-panel'>"
        "<div class='kbo-workstation-panel-title'>Pitching Snapshot</div>"
        "<div class='kbo-workstation-pitchers'>"
        "<div>"
        "<span>Away Starter</span>"
        f"<strong>{_esc(away_pitcher.get('name'), 'Starter Pending')}</strong>"
        f"<small>{_esc(_pitcher_line(away_pitcher))}</small>"
        "</div>"
        "<div>"
        "<span>Home Starter</span>"
        f"<strong>{_esc(home_pitcher.get('name'), 'Starter Pending')}</strong>"
        f"<small>{_esc(_pitcher_line(home_pitcher))}</small>"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
        "<div class='kbo-workstation-reasons'>"
        "<div class='kbo-workstation-panel-title'>Supporting Reasons</div>"
        f"<ul>{_reason_items(model.get('reasons', []))}</ul>"
        "</div>"
        "</section>"
    )


def render_kbo_workstation(game: dict) -> None:
    st.markdown(
        kbo_workstation_html(game),
        unsafe_allow_html=True,
    )

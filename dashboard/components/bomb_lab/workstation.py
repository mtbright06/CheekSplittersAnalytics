from __future__ import annotations

import html
from datetime import datetime
from typing import Any


import streamlit as st

from components.badges import recommendation_badge_html
from components.logos import team_logo_html
from components.status_pill import status_pill_html


def _safe(value: Any, default: str = "Unavailable") -> str:
    if value in (None, "", "None", "N/A"):
        return default

    return str(value)


def _esc(value: Any, default: str = "Unavailable") -> str:
    return html.escape(_safe(value, default))


def _number(value: Any, decimals: int = 1, default: str = "—") -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return default


def _pct(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"

    if abs(number) <= 1:
        number *= 100

    return f"{number:.1f}%"


def _time(value: Any) -> str:
    text = _safe(value, "")
    if not text:
        return "Time TBD"

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text

    return parsed.strftime("%I:%M %p ET").lstrip("0")


def _side_label(side: Any) -> str:
    side_text = str(side or "ANY").upper()

    if side_text == "L":
        return "Left-handed bats"
    if side_text == "R":
        return "Right-handed bats"
    if side_text == "BOTH":
        return "Both sides"

    return "Any side"


def _bomb_recommendation(score: Any, tier: Any) -> str:
    label = str(tier or "").upper()

    if label and label != "PASS":
        return label

    try:
        number = float(score)
    except (TypeError, ValueError):
        return "PASS"

    if number >= 90:
        return "🔥 STRONG PLAY"
    if number >= 82:
        return "🔥 STRONG PLAY"
    if number >= 75:
        return "✅ PLAYABLE"
    if number >= 68:
        return "👀 LEAN"
    return "PASS"


def _market_status(item: dict) -> str:
    if item.get("sportsbook") or item.get("odds") or item.get("best_price"):
        return "REAL MARKET"

    return "MODEL ONLY"


def _metric(label: str, value: Any, *, tone: str = "", quiet: bool = False) -> str:
    tone_class = f" bomb-workstation-metric--{tone}" if tone else ""
    quiet_class = " bomb-workstation-metric--quiet" if quiet else ""

    return (
        f"<div class='bomb-workstation-metric{tone_class}{quiet_class}'>"
        f"<span>{html.escape(label)}</span>"
        f"<strong>{_esc(value, '—')}</strong>"
        "</div>"
    )


def _hitter_meta(top_hitter: dict) -> str:
    pieces = []

    if top_hitter.get("bat_side"):
        pieces.append(f"{top_hitter.get('bat_side')}HB")

    if top_hitter.get("target_score") is not None:
        pieces.append(f"Target Score: {_number(top_hitter.get('target_score'))}")

    if top_hitter.get("hr") is not None:
        pieces.append(f"Season HR: {_safe(top_hitter.get('hr'))}")

    return " · ".join(pieces)


def _summary_metrics(item: dict, top_hitter: dict) -> str:
    sportsbook = item.get("sportsbook") or item.get("book")
    metrics = [
        _metric("Bomb Score", _number(item.get("bomb_score")), tone="success"),
        _metric(
            "Reliability",
            _number(
                item.get("bomb_reliability")
                or item.get("reliability")
                or item.get("sample_confidence"),
                0,
            ),
        ),
    ]

    if top_hitter:
        metrics.append(_metric("Recommended Batter", top_hitter.get("name")))

    if sportsbook:
        metrics.append(_metric("Sportsbook", sportsbook))

    return "".join(metrics)


def _supporting_metrics(item: dict) -> str:
    fields = [
        ("Pitcher Risk", _number(item.get("pitcher_risk"))),
        ("Recent Risk", _number(item.get("recent_risk"))),
        ("Season Risk", _number(item.get("season_risk"))),
        ("Park Score", _number(item.get("park_score"))),
        ("Park Factor", _number(item.get("park_factor"), 2)),
        ("Recent Barrel", _pct(item.get("recent_barrel_pct"))),
        ("Recent Hard Hit", _pct(item.get("recent_hard_hit_pct"))),
        ("Recent HR/BBE", _pct(item.get("recent_hr_per_bbe"))),
        ("Recent BBE", item.get("recent_batted_balls")),
    ]

    rows = "".join(
        _metric(label, value)
        for label, value in fields
        if value not in (None, "", "Unavailable", "—")
    )

    if not rows:
        return "<div class='bomb-workstation-muted'>No supporting metrics loaded.</div>"

    return f"<div class='bomb-workstation-grid bomb-workstation-grid--metrics'>{rows}</div>"


def _reason_items(reasons: list[Any]) -> str:
    items = [reason for reason in reasons[:5] if reason]

    if not items:
        return "<div class='bomb-workstation-muted'>No supporting factors loaded.</div>"

    return "".join(f"<li>{_esc(reason)}</li>" for reason in items)


def bomb_workstation_card_html(
    item: dict,
    *,
    selected_hitter_index: int = 0,
    card_key: str = "bomb-card",
) -> str:
    top_hitters = item.get("top_hitters") or []
    if selected_hitter_index < 0 or selected_hitter_index >= len(top_hitters):
        selected_hitter_index = 0

    top_hitter = top_hitters[selected_hitter_index] if top_hitters else {}
    offense = _safe(item.get("opponent"), "Target Offense")
    pitching_team = _safe(item.get("pitching_team"), "Pitching Team")
    pitcher = _safe(item.get("pitcher"), "Pitcher Pending")
    venue = _safe(item.get("venue"), "Venue TBD")
    start_time = _time(item.get("commence_time"))
    score = item.get("bomb_score")
    recommendation = _bomb_recommendation(score, item.get("tier"))
    market_status = _market_status(item)
    selected_batter = _safe(top_hitter.get("name"), "Batter Pending")

    return (
        "<section class='bomb-workstation-card'>"
        "<div class='bomb-workstation-matchup'>"
        "<div class='bomb-workstation-team'>"
        f"<div class='bomb-workstation-logo'>{team_logo_html(offense, 'mlb')}</div>"
        "<div>"
        "<div class='bomb-workstation-side'>Attack</div>"
        f"<div class='bomb-workstation-team-name'>{_esc(offense)}</div>"
        f"<div class='bomb-workstation-subtitle'>{_esc(_side_label(item.get('target_side')))}</div>"
        "</div>"
        "</div>"
        "<div class='bomb-workstation-center'>"
        "<div class='bomb-workstation-at'>vs</div>"
        f"<div class='bomb-workstation-time'>{_esc(start_time)}</div>"
        f"<div class='bomb-workstation-venue'>{_esc(venue)}</div>"
        "</div>"
        "<div class='bomb-workstation-team bomb-workstation-team--right'>"
        f"<div class='bomb-workstation-logo'>{team_logo_html(pitching_team, 'mlb')}</div>"
        "<div>"
        "<div class='bomb-workstation-side'>Pitcher</div>"
        f"<div class='bomb-workstation-team-name'>{_esc(pitching_team)}</div>"
        f"<div class='bomb-workstation-subtitle'>{_esc(pitcher)}</div>"
        "</div>"
        "</div>"
        "</div>"
        "<div class='bomb-workstation-decision'>"
        "<div class='bomb-workstation-decision-main'>"
        "<div class='bomb-workstation-label'>SharpStack Bomb Recommendation</div>"
        "<div class='bomb-workstation-badges'>"
        f"{recommendation_badge_html(recommendation, model_only=market_status == 'MODEL ONLY')}"
        f"{status_pill_html(market_status)}"
        "</div>"
        f"<div class='bomb-workstation-selected'>{_esc(selected_batter)}</div>"
        f"<div class='bomb-workstation-market'>{_esc(_hitter_meta(top_hitter), 'HR target profile')}</div>"
        "</div>"
        "<div class='bomb-workstation-decision-metrics'>"
        f"{_summary_metrics(item, top_hitter)}"
        "</div>"
        "</div>"
        "<div class='bomb-workstation-panels'>"
        "<div class='bomb-workstation-panel'>"
        "<div class='bomb-workstation-panel-title'>Bomb Squad</div>"
        f"{_bomb_squad(item, selected_hitter_index, card_key)}"
        "</div>"
        "<div class='bomb-workstation-panel'>"
        "<div class='bomb-workstation-panel-title'>Supporting Metrics</div>"
        f"{_supporting_metrics(item)}"
        "</div>"
        "</div>"
        "</section>"
    )


def _selected_hitter_for(card_key: str) -> int:
    del card_key
    return 0


def _bomb_squad(item: dict, selected_index: int, card_key: str) -> str:
    del card_key

    hitters = (item.get("top_hitters") or [])[:4]

    if not hitters:
        return "<div class='bomb-workstation-muted'>No Bomb Squad hitters loaded.</div>"

    cards = []

    for index, hitter in enumerate(hitters):
        active = " bomb-squad-card--active" if index == selected_index else ""
        target_score = _number(hitter.get("target_score"), 0)
        home_runs = _safe(hitter.get("hr"), "—")
        bats = (
            f"{hitter.get('bat_side')}HB"
            if hitter.get("bat_side")
            else "Bats TBD"
        )
        stars = _safe(hitter.get("stars"), "")

        cards.append(
            f"<div class='bomb-squad-card{active}'>"
            "<div class='bomb-squad-card-top'>"
            f"<strong>{_esc(hitter.get('name'))}</strong>"
            "<div class='bomb-squad-card-meta'>"
            f"<span>{html.escape(bats)}</span>"
            f"<span>Target {target_score}</span>"
            f"<span>{html.escape(str(home_runs))} HR</span>"
            "</div>"
            "</div>"
            f"<div class='bomb-squad-card-stars'>{html.escape(stars)}</div>"
            "</div>"
        )

    return (
        "<div class='bomb-squad-list'>"
        f"{''.join(cards)}"
        "</div>"
    )

def render_bomb_lab_workstation(
    summary: dict,
    pitchers: list[dict],
    table: list[dict] | None = None,
) -> None:
    del table

    render_bomb_lab_workstation_header(summary)
    render_bomb_lab_workstation_cards(pitchers)


def render_bomb_lab_workstation_header(summary: dict) -> None:
    st.markdown(
        "<div class='bomb-workstation-header'>"
        "<div>"
        "<div class='bomb-workstation-header-kicker'>SharpStack</div>"
        "<h1>Bomb Lab</h1>"
        "<p>Pitcher vulnerabilities and home-run target diagnostics.</p>"
        "</div>"
        "<div class='bomb-workstation-summary'>"
        f"{_metric('Pitchers', _number(summary.get('pitchers_loaded'), 0))}"
        f"{_metric('Elite', _number(summary.get('elite'), 0), tone='success')}"
        f"{_metric('Strong', _number(summary.get('strong'), 0))}"
        f"{_metric('Watch', _number(summary.get('watch'), 0))}"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )


def render_bomb_lab_workstation_cards(pitchers: list[dict]) -> None:
    for index, item in enumerate(pitchers[:20]):
        card_key = f"bomb-{index}"

        st.markdown(
            bomb_workstation_card_html(
                item,
                selected_hitter_index=_selected_hitter_for(card_key),
                card_key=card_key,
            ),
            unsafe_allow_html=True,
        )

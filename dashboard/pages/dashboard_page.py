from __future__ import annotations

import html
import json
from pathlib import Path

import streamlit as st

from components.badges import recommendation_badge_html
from components.cards import render_game
from components.dashboard_metrics import (
    dashboard_metric_values,
)
from components.logos import team_logo_html
from components.page_header import render_compact_header
from components.pipeline_status import render_pipeline_status
from components.mlb.workstation import render_mlb_workstation_header
from components.status_pill import status_pill_html


ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = (
    ROOT
    / "output"
    / "cards"
    / "recommendation_registry.json"
)

DECISION_CARD_PATH = (
    ROOT
    / "output"
    / "cards"
    / "decision_card.json"
)
BOMB_LAB_CARD_PATH = (
    ROOT
    / "output"
    / "cards"
    / "bomb_lab_card.json"
)
FIRST5_CARD_PATH = (
    ROOT
    / "output"
    / "cards"
    / "first5_card.json"
)

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}

    try:
        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return {}


def load_registry() -> dict:
    return load_json(
        REGISTRY_PATH
    )


def recommendation_matches_league(
    recommendation: dict,
    league_filter: str | None,
) -> bool:
    if not league_filter:
        return True

    expected = league_filter.upper()

    league = str(
        recommendation.get("league")
        or ""
    ).upper()

    sport = str(
        recommendation.get("sport")
        or ""
    ).upper()

    return (
        league == expected
        or sport == expected
    )


def render_multi_sport_dashboard(
    card: dict,
):
    registry = load_registry()
    render_command_center(card, registry)


def render_command_center(card: dict, registry: dict):
    summary = registry.get("summary", {})
    bomb_card = load_json(BOMB_LAB_CARD_PATH)
    first5_card = load_json(FIRST5_CARD_PATH)
    metrics = [
        ("MLB Games", _count_games(card, "MLB")),
        ("Actionable Plays", summary.get("actionable", 0)),
        ("KBO Plays", _count_kbo_plays(card, registry)),
        ("Bomb Targets", _bomb_target_count(bomb_card)),
        ("Engine Status", "Online" if card.get("generated_at") else "No Build"),
        ("Last Build", _display_datetime(card.get("generated_at"))),
    ]

    render_compact_header(
        "⌂",
        "SharpStack Command Center",
        "System summary and top workstation previews.",
        metrics,
    )

    columns = st.columns(4, gap="small")
    previews = [
        _mlb_preview(card, registry),
        _totals_preview(registry),
        _kbo_preview(card, registry),
        _first5_preview(first5_card),
    ]

    for index, (column, preview) in enumerate(zip(columns, previews)):
        with column:
            st.markdown(
                _command_preview_html(preview),
                unsafe_allow_html=True,
            )
            if st.button(
                "View →",
                key=(
                    "command_center_view_"
                    f"{index}_{preview['title'].lower().replace(' ', '_')}"
                ),
                width="stretch",
            ):
                st.session_state.page = preview["route"]
                st.rerun()

    _render_bomb_parlay(bomb_card)

    with st.expander(
        "Data Pipeline",
        expanded=False,
    ):
        render_pipeline_status(card)


def _count_games(card: dict, league: str) -> int:
    expected = league.upper()
    return sum(
        1
        for game in card.get("games", [])
        if str(game.get("sport") or "").upper() == expected
    )


def _count_kbo_plays(card: dict, registry: dict) -> int:
    registry_count = sum(
        1
        for item in registry.get("recommendations", [])
        if recommendation_matches_league(item, "KBO")
        and item.get("actionable", False)
    )
    if registry_count:
        return registry_count
    return sum(
        1
        for game in card.get("games", [])
        if str(game.get("sport") or "").upper() == "KBO"
        and str(game.get("model", {}).get("recommendation") or "").upper()
        not in {"", "PASS"}
    )


def _bomb_target_count(bomb_card: dict) -> int:
    table = bomb_card.get("table")
    if isinstance(table, list):
        return len(table)
    pitchers = bomb_card.get("pitchers")
    if isinstance(pitchers, list):
        return len(pitchers)
    return 0


def _first5_preview(first5_card: dict) -> dict:
    item = _top_first5_item(first5_card)
    selection = _first5_selection(item)
    return {
        "title": "First 5",
        "route": "First 5",
        "primary": selection or "No First 5 recommendation",
        "secondary": item.get("matchup") or "No First 5 matchup loaded",
        "badge": recommendation_badge_html(
            (
                item.get("recommendation_tier")
                or item.get("f5_ml", {}).get("recommendation_tier")
                or "LEAN"
            )
            if selection
            else "PASS"
        ),
        "logo": (
            team_logo_html(selection, "mlb")
            if selection and not selection.startswith(("OVER", "UNDER"))
            else ""
        ),
        "metrics": [
            ("Strength", _number(item.get("model_strength"))),
            (
                "Reliability",
                _number(
                    item.get(
                        "reliability",
                        item.get("confidence"),
                    )
                ),
            ),
        ],
    }


def _registry_top(
    registry: dict,
    *,
    league: str,
    market: str | None = None,
) -> dict:
    rows = [
        item
        for item in registry.get("recommendations", [])
        if recommendation_matches_league(item, league)
        and (market is None or str(item.get("market") or "").lower() == market)
    ]
    return rows[0] if rows else {}


def _mlb_preview(card: dict, registry: dict) -> dict:
    item = _registry_top(registry, league="MLB", market="moneyline")
    game = _top_game(card, "MLB")
    selection = item.get("selection") or _game_selection(game)
    return {
        "title": "MLB",
        "route": "MLB",
        "primary": selection or "No MLB recommendation",
        "secondary": item.get("matchup") or _game_matchup(game),
        "badge": recommendation_badge_html(
            item.get("recommendation") or _game_recommendation(game)
        ),
        "logo": team_logo_html(selection, "mlb") if selection else "",
        "metrics": [("Hammer", _number(item.get("hammer_score")))],
    }


def _totals_preview(registry: dict) -> dict:
    item = _registry_top(registry, league="MLB", market="totals")
    return {
        "title": "Totals",
        "route": "MLB",
        "primary": item.get("selection") or "No totals recommendation",
        "secondary": item.get("matchup") or "MLB Totals Board",
        "badge": recommendation_badge_html(item.get("recommendation") or "PASS"),
        "logo": "",
        "metrics": [
            ("Confidence", item.get("confidence") or "N/A"),
            ("Hammer", _number(item.get("hammer_score"))),
        ],
    }


def _kbo_preview(card: dict, registry: dict) -> dict:
    item = _registry_top(registry, league="KBO")
    game = _top_game(card, "KBO")
    model = game.get("model", {}) if game else {}
    odds = game.get("odds", {}) if game else {}
    selection = item.get("selection") or model.get("play")
    market_status = (
        item.get("market_status")
        or ("REAL MARKET" if item.get("real_market_loaded") else None)
        or odds.get("market_status")
        or ("MODEL ONLY" if game else "NO PLAY")
    )
    return {
        "title": "KBO",
        "route": "KBO",
        "primary": selection or "No KBO recommendation",
        "secondary": item.get("matchup") or _game_matchup(game),
        "badge": recommendation_badge_html(
            item.get("recommendation") or model.get("recommendation") or "PASS"
        ),
        "logo": team_logo_html(selection, "kbo") if selection else "",
        "status": status_pill_html(market_status),
        "metrics": [],
    }


def _top_game(card: dict, league: str) -> dict:
    games = [
        game
        for game in card.get("games", [])
        if str(game.get("sport") or "").upper() == league.upper()
    ]
    if not games:
        return {}
    if league.upper() == "MLB":
        return rank_mlb_games_by_prediction(games)[0]
    return rank_games_by_confidence(games)[0]


def _top_first5_item(first5_card: dict) -> dict:
    games = first5_card.get("games")
    if not isinstance(games, list):
        return {}
    for game in games:
        if _first5_selection(game):
            return game
    if games:
        return games[0]
    return {}


def _first5_selection(item: dict) -> str:
    moneyline = item.get("f5_ml", {}) if isinstance(item, dict) else {}
    total = item.get("f5_total", {}) if isinstance(item, dict) else {}
    if (
        isinstance(moneyline, dict)
        and moneyline.get("lean")
        and moneyline.get("lean") != "PASS"
    ):
        return str(moneyline.get("lean"))
    if (
        isinstance(total, dict)
        and total.get("lean")
        and total.get("lean") != "PASS"
    ):
        line = total.get("model_line")
        if line is not None:
            return f"{total.get('lean')} {line}"
        return str(total.get("lean"))
    return ""


def _render_bomb_parlay(bomb_card: dict) -> None:
    hitters = _bomb_parlay_hitters(bomb_card)
    complete = len(hitters) == 3
    st.markdown(
        _bomb_parlay_html(hitters, complete),
        unsafe_allow_html=True,
    )
    if st.button(
        "View Bomb Lab →",
        key="command_center_view_bomb_lab_parlay",
        width="stretch",
    ):
        st.session_state.page = "Bomb Lab"
        st.rerun()


def _bomb_parlay_hitters(bomb_card: dict) -> list[dict]:
    pitchers = bomb_card.get("pitchers")
    if not isinstance(pitchers, list):
        return []

    selected = []
    teams = set()
    for pitcher in pitchers:
        hitters = pitcher.get("top_hitters")
        if not isinstance(hitters, list) or not hitters:
            continue
        hitter = hitters[0]
        team = hitter.get("team") or pitcher.get("opponent")
        if not team or team in teams:
            continue
        teams.add(team)
        selected.append(
            {
                "name": hitter.get("name"),
                "team": team,
                "handedness": hitter.get("bat_side"),
                "target_score": hitter.get("target_score"),
                "hr": hitter.get("hr"),
            }
        )
        if len(selected) == 3:
            break
    return selected


def _bomb_parlay_html(hitters: list[dict], complete: bool) -> str:
    message = (
        "Top hitter from each of the top three distinct attacking teams."
        if complete
        else "Incomplete: fewer than three eligible attacking teams are available."
    )
    rows = "".join(_bomb_parlay_row_html(hitter) for hitter in hitters)
    if not rows:
        rows = "<div class='command-parlay-empty'>No Bomb Lab hitters available.</div>"
    return (
        "<section class='command-parlay-card'>"
        "<div class='command-parlay-heading'>"
        "<div><span>Bomb Lab</span><strong>💣 3-Man Bomb Parlay</strong></div>"
        f"{status_pill_html('COMPLETE' if complete else 'INCOMPLETE')}"
        "</div>"
        f"<p>{html.escape(message)}</p>"
        f"<div class='command-parlay-grid'>{rows}</div>"
        "</section>"
    )


def _bomb_parlay_row_html(hitter: dict) -> str:
    return (
        "<div class='command-parlay-row'>"
        f"<strong>{html.escape(str(hitter.get('name') or 'Unknown Hitter'))}</strong>"
        f"<span>{html.escape(str(hitter.get('team') or 'N/A'))}</span>"
        f"<span>{html.escape(str(hitter.get('handedness') or 'N/A'))}</span>"
        f"<span>{html.escape(_number(hitter.get('target_score')))}</span>"
        f"<span>{html.escape(str(hitter.get('hr') if hitter.get('hr') is not None else 'N/A'))}</span>"
        "</div>"
    )


def _game_selection(game: dict) -> str:
    return str(game.get("model", {}).get("play") or "")


def _game_recommendation(game: dict) -> str:
    return str(game.get("model", {}).get("recommendation") or "PASS")


def _game_matchup(game: dict) -> str:
    matchup = game.get("matchup", {}) if game else {}
    away = matchup.get("away")
    home = matchup.get("home")
    if away and home:
        return f"{away} @ {home}"
    return "No matchup loaded"


def _number(value, decimals: int = 1) -> str:
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def _display_datetime(value) -> str:
    if not value:
        return "N/A"
    return (
        str(value)
        .replace("T", " ")
        .replace("+00:00", " UTC")
        .replace("Z", " UTC")[:20]
    )


def _command_preview_html(preview: dict) -> str:
    logo = preview.get("logo") or "<div class='command-preview-logo-empty'></div>"
    status = preview.get("status") or ""
    metrics = "".join(
        (
            "<div class='command-preview-metric'>"
            f"<span>{html.escape(str(label))}</span>"
            f"<strong>{html.escape(str(value))}</strong>"
            "</div>"
        )
        for label, value in preview.get("metrics", [])
    )
    return (
        "<section class='command-preview-card'>"
        "<div class='command-preview-top'>"
        f"<div class='command-preview-logo'>{logo}</div>"
        "<div class='command-preview-copy'>"
        f"<span>{html.escape(str(preview.get('title') or 'Preview'))}</span>"
        f"<strong>{html.escape(str(preview.get('primary') or 'Unavailable'))}</strong>"
        f"<small>{html.escape(str(preview.get('secondary') or ''))}</small>"
        "</div>"
        "</div>"
        "<div class='command-preview-badges'>"
        f"{preview.get('badge') or ''}{status}"
        "</div>"
        f"<div class='command-preview-metrics'>{metrics}</div>"
        "</section>"
    )


def render_single_sport_header(
    card: dict,
    league: str,
):
    league_upper = league.upper()

    if league_upper == "MLB":
        render_mlb_workstation_header(card)

        return

    league_icons = {
        "MLB": "⚾",
        "KBO": "🇰🇷",
    }

    icon = league_icons.get(
        league_upper,
        "🏟️",
    )

    render_compact_header(
        icon,
        league_upper,
        (
            "Ranked by projected win probability. Winner ranking reflects the "
            "model's game prediction. Betting recommendations also account for "
            "price and value."
            if league_upper == "MLB"
            else "Ranked by model confidence."
        ),
        dashboard_metric_values(card),
    )

    with st.expander(
        "Pipeline status",
        expanded=False,
    ):
        render_pipeline_status(
            card
        )


def render_mlb_totals_board(
    games: list[dict],
):
    totals_games = [
        game
        for game in games
        if game.get(
            "totals_model"
        )
    ]

    if not totals_games:
        st.info(
            "No MLB totals projections are available."
        )
        return

    st.markdown(
        (
            '<div style="'
            'font-size:1.3rem;'
            'font-weight:850;'
            'margin:0.65rem 0 0.55rem 0;'
            '">'
            '📊 MLB Totals Board'
            '</div>'
        ),
        unsafe_allow_html=True,
    )

    st.caption(
        "Totals follow the canonical MLB card artifact order."
    )

    for game in totals_games:
        totals = game.get(
            "totals_model",
            {},
        )

        betting = totals.get(
            "betting_recommendation",
            {},
        )

        matchup = game.get(
            "matchup",
            {},
        )

        away = matchup.get(
            "away",
            "Away",
        )
        home = matchup.get(
            "home",
            "Home",
        )

        recommendation = (
            betting.get("recommendation")
            or totals.get("recommendation")
            or "PASS"
        )

        selection = (
            betting.get("selection")
            or totals.get("selection")
            or "N/A"
        )

        score = (
            betting.get(
                "recommendation_score"
            )
            or totals.get(
                "recommendation_score"
            )
            or 0
        )

        stars = (
            betting.get("stars")
            or totals.get("stars")
            or ""
        )

        market_total = totals.get(
            "market_total"
        )

        projected_total = totals.get(
            "projected_total"
        )

        edge = totals.get(
            "edge",
            totals.get(
                "absolute_edge"
            ),
        )

        actionable = bool(
            betting.get(
                "actionable",
                totals.get(
                    "actionable",
                    False,
                ),
            )
        )

        status_label = (
            "ACTIONABLE"
            if actionable
            else recommendation
        )

        card_html = (
            '<div style="'
            'display:grid;'
            'grid-template-columns:minmax(240px,2fr) '
            'repeat(5,minmax(85px,0.65fr));'
            'gap:0.7rem;'
            'align-items:center;'
            'padding:0.8rem 0.95rem;'
            'margin-bottom:0.55rem;'
            'border:1px solid rgba(255,255,255,0.11);'
            'border-radius:0.85rem;'
            'background:rgba(255,255,255,0.025);'
            '">'
            '<div>'
            '<div style="'
            'font-size:0.68rem;'
            'font-weight:850;'
            'letter-spacing:0.08em;'
            'opacity:0.65;'
            '">'
            f'{status_label} · {stars}'
            '</div>'
            '<div style="'
            'font-size:1rem;'
            'font-weight:800;'
            'margin-top:0.15rem;'
            '">'
            f'{away} @ {home}'
            '</div>'
            '</div>'
            f'{_totals_metric("Play", selection)}'
            f'{_totals_metric("Market", market_total)}'
            f'{_totals_metric("Model", projected_total)}'
            f'{_totals_metric("Edge", edge)}'
            f'{_totals_metric("Score", score)}'
            '</div>'
        )

        st.markdown(
            card_html,
            unsafe_allow_html=True,
        )


def _totals_metric(
    label,
    value,
):
    if isinstance(
        value,
        float,
    ):
        display = f"{value:.2f}"
    else:
        display = str(
            value
            if value is not None
            else "N/A"
        )

    return (
        '<div>'
        '<div style="'
        'font-size:0.65rem;'
        'font-weight:800;'
        'letter-spacing:0.07em;'
        'text-transform:uppercase;'
        'opacity:0.58;'
        '">'
        f'{label}'
        '</div>'
        '<div style="'
        'font-size:0.95rem;'
        'font-weight:850;'
        'margin-top:0.1rem;'
        '">'
        f'{display}'
        '</div>'
        '</div>'
    )


def game_confidence(game: dict) -> float:
    try:
        return float(
            game.get("model", {}).get("confidence")
        )
    except (TypeError, ValueError):
        return float("-inf")


def game_model_win_probability(game: dict) -> float:
    """Return the model prediction value used solely for MLB slate display."""
    try:
        return float(
            game.get("model", {}).get("model_probability")
        )
    except (TypeError, ValueError):
        return float("-inf")


def rank_games_by_confidence(
    games: list[dict],
) -> list[dict]:
    """Use the same display ordering for MLB and KBO without mutating cards."""
    return sorted(
        games,
        key=game_confidence,
        reverse=True,
    )


def rank_mlb_games_by_prediction(
    games: list[dict],
) -> list[dict]:
    """Order MLB slate by prediction, independent of market-value outputs."""
    return sorted(
        games,
        key=lambda game: (
            -game_model_win_probability(game),
            -game_confidence(game),
        ),
    )


def decision_hammer_scores() -> dict[str, float]:
    decision_card = load_json(DECISION_CARD_PATH)

    return {
        str(decision.get("game_pk")): decision.get("hammer_score")
        for decision in decision_card.get("decisions", [])
        if isinstance(decision, dict)
        and decision.get("game_pk") is not None
    }


def render_single_sport_dashboard(
    card: dict,
):
    games = card.get(
        "games",
        [],
    )

    league = str(
        card.get("sport")
        or ""
    ).upper()

    render_single_sport_header(
        card,
        league,
    )

    if not games:
        st.info(
            "No games are currently available."
        )
        return

    ranked_games = (
        rank_mlb_games_by_prediction(games)
        if league == "MLB"
        else rank_games_by_confidence(games)
    )
    hammer_scores = (
        decision_hammer_scores()
        if league == "MLB"
        else {}
    )

    def render_ranked_slate():
        if league != "MLB":
            st.markdown(
                (
                    '<div style="'
                    'font-size:1.3rem;'
                    'font-weight:850;'
                    'margin:0.65rem 0 0.55rem 0;'
                    '">'
                    f'{league} Full Slate'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

        for index, game in enumerate(
            ranked_games
        ):
            render_game(
                game,
                hammer_score=hammer_scores.get(
                    str(game.get("game_id"))
                ),
            )

            if index < len(
                ranked_games
            ) - 1:
                st.markdown(
                    (
                        '<div style="'
                        'height:1px;'
                        'margin:1rem 0 1.15rem 0;'
                        'background:linear-gradient('
                        '90deg,'
                        'rgba(255,255,255,0),'
                        'rgba(255,255,255,0.22),'
                        'rgba(255,255,255,0)'
                        ');'
                        '"></div>'
                    ),
                    unsafe_allow_html=True,
                )

    if league == "MLB":
        slate_tab, totals_tab = st.tabs(
            [
                "⚾ Full Slate",
                "📊 Totals Board",
            ]
        )

        with slate_tab:
            render_ranked_slate()

        with totals_tab:
            render_mlb_totals_board(ranked_games)
    else:
        render_ranked_slate()

def render_dashboard(
    card: dict,
):
    if card.get("sport") == "MULTI":
        render_multi_sport_dashboard(
            card
        )
    else:
        render_single_sport_dashboard(
            card
        )

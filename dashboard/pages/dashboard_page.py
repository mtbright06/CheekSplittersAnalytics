from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from components.cards import render_game
from components.dashboard_metrics import (
    dashboard_metric_values,
    render_dashboard_metrics,
)
from components.page_header import render_compact_header
from components.pipeline_status import render_pipeline_status
from components.registry.registry_cards import (
    render_registry_card,
)


ROOT = Path(__file__).resolve().parents[2]

REGISTRY_PATH = (
    ROOT
    / "output"
    / "cards"
    / "recommendation_registry.json"
)

ACTIONABLE_TIERS = {
    "HAMMER",
    "BET",
    "LEAN",
}


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


def actionable_recommendations(
    registry: dict,
    league_filter: str | None = None,
) -> list[dict]:
    recommendations = registry.get(
        "recommendations",
        [],
    )

    return [
        recommendation
        for recommendation in recommendations
        if (
            recommendation.get(
                "recommendation"
            )
            in ACTIONABLE_TIERS
            and recommendation_matches_league(
                recommendation,
                league_filter,
            )
        )
    ]


def group_recommendations_by_market(
    recommendations: list[dict],
) -> dict[tuple[str, str], list[dict]]:
    """Keep registry order while separating the Command Board by market."""
    grouped: dict[tuple[str, str], list[dict]] = {}

    for recommendation in recommendations:
        league = str(
            recommendation.get("league")
            or recommendation.get("sport")
            or "OTHER"
        ).upper()
        market = str(
            recommendation.get("market")
            or "OTHER"
        ).lower()

        grouped.setdefault(
            (league, market),
            [],
        ).append(recommendation)

    return grouped


def market_board_title(
    league: str,
    market: str,
) -> str:
    return f"{league} {market.replace('_', ' ').title()}"


def render_canonical_board(
    registry: dict,
    league_filter: str | None = None,
):
    recommendations = (
        actionable_recommendations(
            registry,
            league_filter=league_filter,
        )
    )

    if league_filter:
        title = (
            f"🍑 {league_filter.upper()} "
            "Official Board"
        )
    else:
        title = (
            "🍑 SharpStack Command Board"
        )

    st.markdown(
        f'<div class="section-title">'
        f"{title}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not recommendations:
        if league_filter:
            st.info(
                f"No official {league_filter.upper()} "
                "HAMMER, BET, or LEAN "
                "recommendations are available."
            )
        else:
            st.info(
                "No official HAMMER, BET, or LEAN "
                "recommendations are available."
            )

        return

    grouped = group_recommendations_by_market(
        recommendations
    )

    for (league, market), market_rows in (
        grouped.items()
    ):
        st.markdown(
            f'<div class="sport-section-title">'
            f"{market_board_title(league, market)} Play"
            f"</div>",
            unsafe_allow_html=True,
        )

        render_registry_card(
            market_rows[0],
            1,
        )


def render_dashboard_header(
    card: dict,
    league_filter: str | None = None,
):
    render_dashboard_metrics(
        card
    )

    registry = load_registry()

    with st.expander(
        "Data Pipeline",
        expanded=False,
    ):
        render_pipeline_status(
            card
        )

    render_canonical_board(
        registry,
        league_filter=league_filter,
    )

def render_multi_sport_dashboard(
    card: dict,
):
    render_dashboard_header(
        card,
        league_filter=None,
    )


def render_single_sport_header(
    card: dict,
    league: str,
):
    league_upper = league.upper()

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
        "Ranked by model confidence.",
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


def rank_games_by_confidence(
    games: list[dict],
) -> list[dict]:
    """Use the same display ordering for MLB and KBO without mutating cards."""
    return sorted(
        games,
        key=game_confidence,
        reverse=True,
    )


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

    ranked_games = rank_games_by_confidence(games)

    def render_ranked_slate():
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
                game
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

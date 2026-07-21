from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from components.cards import render_game
from components.dashboard_metrics import render_dashboard_metrics
from components.pipeline_status import render_pipeline_status
from components.registry.play_of_day_card import (
    render_play_of_day,
)
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

PLAY_OF_DAY_PATH = (
    ROOT
    / "output"
    / "cards"
    / "play_of_day.json"
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


def load_play_of_day() -> dict:
    return load_json(
        PLAY_OF_DAY_PATH
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


def group_recommendations_by_league(
    recommendations: list[dict],
) -> dict[str, list[dict]]:
    grouped: dict[
        str,
        list[dict],
    ] = {}

    for recommendation in recommendations:
        league = (
            recommendation.get("league")
            or recommendation.get("sport")
            or "OTHER"
        )

        league = str(
            league
        ).upper()

        grouped.setdefault(
            league,
            [],
        ).append(
            recommendation
        )

    return grouped


def render_global_play_of_day():
    play_of_day = load_play_of_day()

    if not play_of_day:
        st.warning(
            "No Play of the Day artifact was found. "
            "Run the recommendation registry builder."
        )
        return

    render_play_of_day(
        play_of_day
    )


def render_league_play_of_day(
    registry: dict,
    league: str,
):
    recommendations = (
        actionable_recommendations(
            registry,
            league_filter=league,
        )
    )

    if not recommendations:
        st.info(
            f"No Official {league.upper()} "
            "Play of the Day."
        )
        return

    winner = recommendations[0]

    play_of_day = {
        "generated_at": (
            registry.get("generated_at")
        ),
        "eligible_count": len(
            recommendations
        ),
        "reason": (
            f"Highest-ranked actionable "
            f"{league.upper()} recommendation "
            "from the SharpStack registry."
        ),
        "recommendation": winner,
    }

    render_play_of_day(
        play_of_day
    )


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

    grouped = (
        group_recommendations_by_league(
            recommendations
        )
    )

    for league, league_rows in (
        grouped.items()
    ):
        st.markdown(
            f'<div class="sport-section-title">'
            f"{league} Official Picks"
            f"</div>",
            unsafe_allow_html=True,
        )

        for rank, recommendation in enumerate(
            league_rows[:3],
            start=1,
        ):
            render_registry_card(
                recommendation,
                rank,
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

    render_global_play_of_day()

    st.markdown(
        '<div style="height:0.75rem;"></div>',
        unsafe_allow_html=True,
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


def normalize_text(value) -> str:
    return str(
        value or ""
    ).strip().lower()


def game_matchup_text(
    game: dict,
) -> str:
    matchup = game.get(
        "matchup",
        {},
    )

    away = matchup.get(
        "away",
        "",
    )
    home = matchup.get(
        "home",
        "",
    )

    return normalize_text(
        f"{away} @ {home}"
    )


def registry_match_for_game(
    game: dict,
    registry_rows: list[dict],
    league: str,
) -> dict | None:
    game_id = normalize_text(
        game.get("game_id")
    )

    matchup_text = (
        game_matchup_text(
            game
        )
    )

    for row in registry_rows:
        row_league = normalize_text(
            row.get("league")
        )

        if row_league != normalize_text(
            league
        ):
            continue

        event_id = normalize_text(
            row.get("event_id")
        )

        if (
            game_id
            and event_id
            and game_id == event_id
        ):
            return row

        row_matchup = normalize_text(
            row.get("matchup")
        )

        if (
            matchup_text
            and row_matchup
            and matchup_text == row_matchup
        ):
            return row

    return None


def fallback_recommendation_rank(
    game: dict,
) -> int:
    recommendation = normalize_text(
        game.get(
            "model",
            {},
        ).get(
            "recommendation"
        )
    )

    if (
        "hammer" in recommendation
        or "cheek ripper" in recommendation
    ):
        return 5

    if "bet" in recommendation:
        return 4

    if "lean" in recommendation:
        return 3

    if "watch" in recommendation:
        return 2

    if "playable" in recommendation:
        return 1

    return 0


def slate_sort_key(
    game: dict,
    registry_rows: list[dict],
    league: str,
) -> tuple:
    registry_row = (
        registry_match_for_game(
            game,
            registry_rows,
            league,
        )
    )

    if registry_row:
        return (
            1,
            float(
                registry_row.get(
                    "ranking_score"
                )
                or 0
            ),
            float(
                registry_row.get(
                    "hammer_score"
                )
                or 0
            ),
            float(
                registry_row.get(
                    "edge_pct"
                )
                or 0
            ),
        )

    model = game.get(
        "model",
        {},
    )

    return (
        0,
        fallback_recommendation_rank(
            game
        ),
        float(
            model.get(
                "confidence"
            )
            or 0
        ),
        float(
            model.get(
                "edge"
            )
            or 0
        ),
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

    header_html = (
        '<div style="'
        'display:flex;'
        'align-items:flex-end;'
        'justify-content:space-between;'
        'gap:1rem;'
        'margin:0.45rem 0 0.65rem 0;'
        '">'
        '<div>'
        '<div style="'
        'font-size:1.75rem;'
        'font-weight:850;'
        'line-height:1.05;'
        '">'
        f'{icon} {league_upper}'
        '</div>'
        '<div style="'
        'margin-top:0.28rem;'
        'font-size:0.88rem;'
        'opacity:0.68;'
        '">'
        'Ranked strongest to weakest'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(
        header_html,
        unsafe_allow_html=True,
    )

    render_dashboard_metrics(
        card
    )

    with st.expander(
        "Pipeline status",
        expanded=False,
    ):
        render_pipeline_status(
            card
        )


def totals_recommendation_rank(
    recommendation: str,
) -> int:
    value = str(
        recommendation or ""
    ).upper()

    order = {
        "HAMMER": 5,
        "BET": 4,
        "LEAN": 3,
        "WATCH": 2,
        "PASS": 1,
    }

    return order.get(
        value,
        0,
    )


def mlb_totals_sort_key(
    game: dict,
) -> tuple:
    totals = game.get(
        "totals_model",
        {},
    )

    betting = totals.get(
        "betting_recommendation",
        {},
    )

    recommendation = (
        betting.get("recommendation")
        or totals.get("recommendation")
        or "PASS"
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

    score = float(
        betting.get(
            "recommendation_score",
            totals.get(
                "recommendation_score",
                0,
            ),
        )
        or 0
    )

    absolute_edge = float(
        totals.get(
            "absolute_edge",
            0,
        )
        or 0
    )

    return (
        int(actionable),
        totals_recommendation_rank(
            recommendation
        ),
        score,
        absolute_edge,
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

    ranked_totals = sorted(
        totals_games,
        key=mlb_totals_sort_key,
        reverse=True,
    )

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
        "Totals are ranked by actionable status, "
        "recommendation tier, recommendation score, and edge."
    )

    for game in ranked_totals:
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

    registry = load_registry()

    registry_rows = registry.get(
        "recommendations",
        [],
    )

    ranked_games = sorted(
        games,
        key=lambda game: slate_sort_key(
            game,
            registry_rows,
            league,
        ),
        reverse=True,
    )

    def render_ranked_slate():
        st.markdown(
            (
                '<div style="'
                'font-size:1.3rem;'
                'font-weight:850;'
                'margin:0.65rem 0 0.55rem 0;'
                '">'
                f'{league} Ranked Slate'
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
        totals_tab, slate_tab = st.tabs(
            [
                "📊 Totals Board",
                "⚾ Full Slate",
            ]
        )

        with totals_tab:
            render_mlb_totals_board(
                ranked_games
            )

        with slate_tab:
            render_ranked_slate()
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

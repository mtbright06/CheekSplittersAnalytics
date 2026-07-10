from __future__ import annotations

import html

import streamlit as st


def safe(value, default="N/A"):
    if value in [None, "", "None"]:
        return default

    return value


def esc(value, default="N/A"):
    return html.escape(str(safe(value, default)))


def format_number(value, decimals=2, default="N/A"):
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return default


def render_first5_summary(summary):
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Games", summary.get("games_loaded", 0))
    c2.metric("F5 ML Leans", summary.get("f5_ml_leans", 0))
    c3.metric("F5 Total Leans", summary.get("f5_total_leans", 0))
    c4.metric("Top F5 ML", summary.get("top_ml_play", "PASS"))


def render_first5_game_card(game, rank=None):
    away = game.get("away", {})
    home = game.get("home", {})
    f5_ml = game.get("f5_ml", {})
    f5_total = game.get("f5_total", {})

    rank_text = f"#{rank}" if rank is not None else ""

    matchup = esc(game.get("matchup"))
    venue = esc(game.get("venue"))
    grade = esc(game.get("confidence_grade"))
    confidence = format_number(game.get("confidence"), 1)

    away_team = esc(away.get("team"))
    home_team = esc(home.get("team"))
    away_runs = format_number(away.get("projected_f5_runs"), 2)
    home_runs = format_number(home.get("projected_f5_runs"), 2)

    ml_lean = esc(f5_ml.get("lean"))
    ml_margin = format_number(f5_ml.get("projected_margin"), 2)

    total_lean = esc(f5_total.get("lean"))
    model_line = format_number(f5_total.get("model_line"), 1)
    projected_total = format_number(f5_total.get("projected_total"), 2)

    park_factor = format_number(game.get("park_factor"), 3)

    card_html = (
        '<div class="first5-card">'
        '<div class="first5-card-header">'
        '<div>'
        f'<div class="first5-rank">{rank_text}</div>'
        f'<div class="first5-matchup">{matchup}</div>'
        f'<div class="first5-meta">{venue} · Confidence {grade}</div>'
        '</div>'
        '<div class="first5-confidence">'
        '<span>Confidence</span>'
        f'<strong>{confidence}</strong>'
        '</div>'
        '</div>'
        '<div class="first5-projections">'
        '<div>'
        f'<span>{away_team}</span>'
        f'<strong>{away_runs}</strong>'
        '<small>Projected F5 Runs</small>'
        '</div>'
        '<div>'
        f'<span>{home_team}</span>'
        f'<strong>{home_runs}</strong>'
        '<small>Projected F5 Runs</small>'
        '</div>'
        '</div>'
        '<div class="first5-decisions">'
        '<div>'
        '<span>F5 Moneyline</span>'
        f'<strong>{ml_lean}</strong>'
        f'<small>Margin {ml_margin}</small>'
        '</div>'
        '<div>'
        '<span>F5 Total</span>'
        f'<strong>{total_lean} {model_line}</strong>'
        f'<small>Projection {projected_total}</small>'
        '</div>'
        '<div>'
        '<span>Park Factor</span>'
        f'<strong>{park_factor}</strong>'
        '<small>Run environment</small>'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

    reasons = game.get("reasons", [])

    if reasons:
        for reason in reasons:
            st.markdown(
                f"<div class='reason'>⚾ {esc(reason)}</div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("No supporting reasons available for this matchup.")


def render_first5_table(games):
    rows = []

    for game in games:
        away = game.get("away", {})
        home = game.get("home", {})
        f5_ml = game.get("f5_ml", {})
        f5_total = game.get("f5_total", {})

        rows.append(
            {
                "Matchup": game.get("matchup"),
                "F5 ML": f5_ml.get("lean"),
                "Margin": f5_ml.get("projected_margin"),
                "F5 Total": f5_total.get("lean"),
                "Model Line": f5_total.get("model_line"),
                "Projected Total": f5_total.get("projected_total"),
                "Away Runs": away.get("projected_f5_runs"),
                "Home Runs": home.get("projected_f5_runs"),
                "Confidence": game.get("confidence"),
                "Grade": game.get("confidence_grade"),
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
    )

from __future__ import annotations

import html

import streamlit as st


def safe(value, default="N/A"):
    if value in [None, "", "None"]:
        return default
    return value


def esc(value, default="N/A"):
    return html.escape(str(safe(value, default)))


def number(value, decimals=1, default="N/A"):
    try:
        return f"{float(value):.{decimals}f}"
    except (TypeError, ValueError):
        return default


def percent(value, decimals=1, default="N/A"):
    try:
        return f"{float(value) * 100:.{decimals}f}%"
    except (TypeError, ValueError):
        return default


def signed(value, decimals=1, suffix=""):
    try:
        return f"{float(value):+.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"


def american(value):
    try:
        value = int(round(float(value)))

        if value > 0:
            return f"+{value}"

        return str(value)
    except (TypeError, ValueError):
        return "N/A"


def render_market_summary(summary):
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Games", summary.get("games_loaded", 0))
    c2.metric("Model Bets", summary.get("market_bets", 0))
    c3.metric("Market Leans", summary.get("market_leans", 0))
    c4.metric("Top Side", summary.get("top_side", "PASS"))


def render_market_edge_card(game, rank=None):
    away_market = game.get("away_market", {})
    home_market = game.get("home_market", {})
    best = game.get("best_market_side", {})
    total = game.get("f5_total_market", {})
    probabilities = game.get("model_probabilities", {})

    rank_text = f"#{rank}" if rank else ""

    html_block = (
        '<div class="market-edge-card">'
        '<div class="market-edge-header">'
        '<div>'
        f'<div class="market-edge-rank">{esc(rank_text, "")}</div>'
        f'<div class="market-edge-matchup">{esc(game.get("matchup"))}</div>'
        f'<div class="market-edge-venue">{esc(game.get("venue"))}</div>'
        '</div>'
        '<div class="market-edge-score">'
        '<span>Decision</span>'
        f'<strong>{number(game.get("market_decision_score"), 1)}</strong>'
        '</div>'
        '</div>'

        '<div class="market-primary">'
        '<div>'
        '<span>Best F5 Side</span>'
        f'<strong>{esc(best.get("recommendation"))}</strong>'
        f'<small>{esc(best.get("grade"))} grade</small>'
        '</div>'
        '<div>'
        '<span>Model Probability</span>'
        f'<strong>{percent(best.get("model_probability"))}</strong>'
        f'<small>Fair {american(best.get("model_fair_odds"))}</small>'
        '</div>'
        '<div>'
        '<span>Book Probability</span>'
        f'<strong>{percent(best.get("book_no_vig_probability"))}</strong>'
        f'<small>Book {american(best.get("book_odds"))}</small>'
        '</div>'
        '<div>'
        '<span>Market Edge</span>'
        f'<strong>{signed(best.get("edge_pct"), 1, "%")}</strong>'
        f'<small>EV {signed(best.get("expected_value_pct"), 1, "%")}</small>'
        '</div>'
        '</div>'

        '<div class="market-secondary">'
        '<div>'
        '<span>Away Win</span>'
        f'<strong>{percent(probabilities.get("away_win"))}</strong>'
        f'<small>{esc(away_market.get("team"))}</small>'
        '</div>'
        '<div>'
        '<span>F5 Tie</span>'
        f'<strong>{percent(probabilities.get("tie"))}</strong>'
        '<small>Push exposure</small>'
        '</div>'
        '<div>'
        '<span>Home Win</span>'
        f'<strong>{percent(probabilities.get("home_win"))}</strong>'
        f'<small>{esc(home_market.get("team"))}</small>'
        '</div>'
        '<div>'
        '<span>F5 Total</span>'
        f'<strong>{esc(total.get("lean"))}</strong>'
        f'<small>Model {number(total.get("model_total"), 2)} '
        f'vs Book {number(total.get("book_line"), 1)}</small>'
        '</div>'
        '</div>'
        '</div>'
    )

    st.markdown(html_block, unsafe_allow_html=True)

    for reason in game.get("market_reasons", [])[:4]:
        st.markdown(
            f"<div class='reason'>💰 {esc(reason)}</div>",
            unsafe_allow_html=True,
        )


def render_market_table(games):
    rows = []

    for game in games:
        best = game.get("best_market_side", {})
        total = game.get("f5_total_market", {})

        rows.append(
            {
                "Matchup": game.get("matchup"),
                "Recommendation": best.get("recommendation"),
                "Model %": (
                    round(best["model_probability"] * 100, 1)
                    if best.get("model_probability") is not None
                    else None
                ),
                "Book %": (
                    round(best["book_no_vig_probability"] * 100, 1)
                    if best.get("book_no_vig_probability") is not None
                    else None
                ),
                "Book Odds": best.get("book_odds"),
                "Edge %": best.get("edge_pct"),
                "EV %": best.get("expected_value_pct"),
                "Grade": best.get("grade"),
                "F5 Total": total.get("book_line"),
                "Model Total": total.get("model_total"),
                "Total Lean": total.get("lean"),
                "Run Edge": total.get("run_edge"),
            }
        )

    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
    )

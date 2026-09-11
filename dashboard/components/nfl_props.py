from __future__ import annotations

from html import escape
from functools import lru_cache
import base64
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from app.player_assets import get_player_headshot
from components.logos import team_logo_path


@lru_cache(maxsize=1024)
def _local_image_data(path: str, modified: int) -> str:
    file = Path(path)
    mime = {'.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}.get(
        file.suffix.lower(), 'image/png')
    return f'data:{mime};base64,' + base64.b64encode(file.read_bytes()).decode('ascii')


def _identity_image(path, css_class, label):
    if path is None:
        return ''
    try:
        source = _local_image_data(str(path), path.stat().st_mtime_ns)
        return f'<img class="{css_class}" src="{source}" alt="{escape(label, quote=True)}">'
    except OSError:
        return ''


def inject_nfl_props_styles() -> None:
    st.markdown(
        """
        <style>
        .nfl-props-title {display:flex; align-items:center; gap:.7rem; margin:.15rem 0 .9rem}
        .nfl-props-mark {font-size:2rem; line-height:1}
        .nfl-props-title h1 {font-size:1.85rem; margin:0; letter-spacing:0}
        .nfl-props-title p {margin:.12rem 0 0; color:#54b8e8; font-size:.72rem;
            font-weight:700; letter-spacing:.12rem; text-transform:uppercase}
        .nfl-intel-name {font-size:1.15rem; font-weight:750; color:#f3f7fb}
        .nfl-identity {display:flex; align-items:center; gap:12px}
        .nfl-headshot {width:84px; height:80px; object-fit:contain; flex:none}
        [data-testid="stDialog"]:has(.st-key-nfl_intelligence) [role="dialog"] > div:first-of-type {
            height:0; margin:0; overflow:hidden;
        }
        .st-key-nfl_intelligence .nfl-headshot {width:104px; height:100px}
        .st-key-nfl_intelligence .nfl-intel-name {font-size:24px; font-weight:700; line-height:1.2}
        .nfl-team-image {width:26px; height:24px; object-fit:contain; vertical-align:middle}
        .nfl-intel-meta {color:#a9b7c5; margin-top:.18rem}
        .nfl-intel-matchup {color:#d6e4ef; font-weight:650; text-align:right}
        .nfl-intel-source {color:#71879a; font-size:.78rem; text-align:right; margin-top:.2rem}
        .nfl-section-label {font-size:.78rem; color:#8fa3b7; font-weight:700;
            text-transform:uppercase; margin:.45rem 0 .3rem}
        .nfl-compact {font-size:.8rem; color:#d6e4ef; overflow-x:auto}
        .nfl-compact table {width:100%; border-collapse:collapse; margin:0; font-size:inherit}
        .nfl-compact th,.nfl-compact td {padding:6px 5px; border:0;
            border-bottom:1px solid #253443; text-align:right; white-space:nowrap}
        .nfl-compact th {color:#91a6ba; font-weight:500}
        .nfl-compact th:first-child,.nfl-compact td:first-child {text-align:left}
        .nfl-quote {display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 14px;
            padding:8px 0; border-bottom:1px solid #253443}
        .nfl-quote strong {font-size:1.2rem; color:#f3f7fb}
        .nfl-quote small {color:#91a6ba}
        .nfl-HIT {color:#31c77a}.nfl-MISS {color:#ef5b67}.nfl-PUSH {color:#e5b84b}
        .st-key-nfl_intelligence div[data-testid="stVerticalBlock"] {gap:.5rem}
        .st-key-nfl_scanner div[data-testid="stVerticalBlock"] {gap:.25rem}
        .st-key-nfl_scanner button {border-radius:4px; text-align:left; justify-content:flex-start;
            min-height:48px; font-weight:650}
        .nfl-scan {display:flex; gap:20px; align-items:center; min-height:48px;
            border-bottom:1px solid #253443; font-size:.82rem; flex-wrap:wrap}
        .nfl-scan small {display:block; color:#8fa3b7; font-size:.7rem}
        .nfl-scan strong {color:#eef5fa; font-size:1.05rem}
        .nfl-scan .prop {flex:1; min-width:140px}
        .nfl-scan .signal {min-width:42px}
        .nfl-micro {display:flex; gap:3px; align-items:center; height:22px}
        .nfl-micro i {width:5px; height:16px; display:block; background:#8292a3}
        .nfl-micro .HIT {background:#31c77a}.nfl-micro .MISS {background:#ef5b67}
        .nfl-micro .PUSH {background:#e5b84b}
        @media (max-width: 700px) {
            .nfl-props-title h1 {font-size:1.45rem}
            .nfl-intel-matchup,.nfl-intel-source {text-align:left}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_nfl_props_title() -> None:
    st.markdown(
        """<div class="nfl-props-title"><div class="nfl-props-mark">🏈</div>
        <div><h1>NFL Player Props</h1><p>Factual market and performance research</p></div></div>""",
        unsafe_allow_html=True,
    )


def render_player_identity(
    *, player: str, team: str, position: str, opponent: str, market: str,
    game_context: str, source_context: str, player_id: str = '',
) -> None:
    left, right = st.columns([1.35, 1], vertical_alignment="center")
    with left:
        headshot = _identity_image(get_player_headshot('nfl', player_id), 'nfl-headshot', player)
        logo = _identity_image(team_logo_path(team, 'nfl'), 'nfl-team-image', team)
        st.markdown(
            f'<div class="nfl-identity">{headshot}<div><div class="nfl-intel-name">{escape(player)}</div>'
            f'<div class="nfl-intel-meta">{escape(position)} &nbsp;|&nbsp; '
            f'{logo} {escape(team)} &nbsp;|&nbsp; {escape(market)}</div></div></div>',
            unsafe_allow_html=True,
        )
    with right:
        team_image = _identity_image(team_logo_path(team, 'nfl'), 'nfl-team-image', team)
        opponent_image = _identity_image(team_logo_path(opponent, 'nfl'), 'nfl-team-image', opponent)
        st.markdown(
            f'<div class="nfl-intel-matchup">{team_image} {escape(team)} vs {escape(opponent)} {opponent_image}</div>'
            f'<div class="nfl-intel-source">{escape(game_context)}<br>{escape(source_context)}</div>',
            unsafe_allow_html=True,
        )


def recent_performance_chart(results, line: float, average: float | None = None, sportsbook_line=None):
    records = [{
        "Date": result.game_date.isoformat(),
        "Opponent": result.opponent_abbreviation or "N/A",
        "Game": ('@ ' if result.home_away == 'AWAY' else 'vs ') +
                (result.opponent_abbreviation or 'N/A') + ' ' + result.game_date.strftime('%m/%d'),
        "Actual": float(result.actual_value),
        "Result": result.result,
    } for result in reversed(tuple(results))]
    if not records:
        return None
    frame = pd.DataFrame(records)
    floor = min(0.0, float(frame["Actual"].min())) * 1.12
    ceiling = max(float(line), float(frame["Actual"].max()), 1.0) * 1.12
    bars = alt.Chart(frame).mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2).encode(
        x=alt.X("Game:N", sort=None, axis=alt.Axis(labelAngle=-35, title=None, labelFontSize=10)),
        y=alt.Y("Actual:Q", scale=alt.Scale(domain=[floor, ceiling]), title=None),
        color=alt.Color(
            "Result:N",
            scale=alt.Scale(domain=["HIT", "MISS", "PUSH"], range=["#31c77a", "#ef5b67", "#e5b84b"]),
            legend=None,
        ),
        tooltip=["Date:N", "Opponent:N", "Actual:Q", "Result:N"],
    )
    threshold = alt.Chart(pd.DataFrame({"line": [line]})).mark_rule(
        color="#67c9f3", strokeDash=[5, 4], size=2,
    ).encode(y="line:Q")
    labels = alt.Chart(frame).mark_text(dy=-9, color='#e5edf4', fontSize=13, fontWeight=600).encode(
        x=alt.X('Game:N', sort=None), y='Actual:Q', text=alt.Text('Actual:Q', format='.0f'))
    chart = bars + threshold + labels
    if sportsbook_line is not None and sportsbook_line != line:
        chart += alt.Chart(pd.DataFrame({'Sportsbook': [sportsbook_line]})).mark_rule(
            color='#b6c1cb', size=2
        ).encode(y='Sportsbook:Q', tooltip='Sportsbook:Q')
    if average is not None:
        chart += alt.Chart(pd.DataFrame({'average': [average]})).mark_rule(
            color='#e5b84b', strokeDash=[2, 4]
        ).encode(y='average:Q', tooltip=alt.Tooltip('average:Q', title='Average', format='.1f'))
    return chart.properties(height=235)


def prop_row_key(row):
    return f'{row.quote.game_id}_{row.trend.player_id}_{row.trend.market}_{row.quote.book_key}'


def render_prop_scanner(rows, opponents, market_label):
    """Native identity buttons keep selection accessible; quote rows are renderer-only HTML."""
    options = {prop_row_key(row): row for row in rows}
    state_key = 'nfl_research_selection'
    if st.session_state.get(state_key) not in options:
        st.session_state[state_key] = next(iter(options))

    def select(key):
        st.session_state[state_key] = key
        st.session_state['nfl_research_open'] = True

    with st.container(key='nfl_scanner'):
        for key, row in options.items():
            trend, quote = row.trend, row.quote
            identity, evidence = st.columns([1, 3], gap='small', vertical_alignment='center')
            with identity:
                st.button(trend.player_name or trend.player_id, key=f'nfl_select_{key}',
                          type='primary' if st.session_state[state_key] == key else 'secondary',
                          use_container_width=True, on_click=select, args=(key,),
                          help=f'{trend.position or "N/A"} | {trend.team_abbreviation} | Research player')
            def rate(summary):
                return 'N/A' if summary.hit_rate is None else f'{summary.hit_rate:.0%}'
            def price(value):
                return 'N/A' if value is None else f'{value:+d}'
            signals = ''.join(f'<span class="signal"><small>{label}</small>{rate(summary)}</span>'
                              for label, summary in [('L5', trend.last_5), ('L10', trend.last_10),
                                                     ('L20', trend.last_20), ('Season', trend.season)])
            micro = ''.join(f'<i class="{r.result}" title="{r.result}"></i>'
                            for r in reversed(trend.last_10.game_results))
            line = 'Yes' if quote.line is None else f'{quote.line:g}'
            with evidence:
                logo = _identity_image(team_logo_path(trend.team_abbreviation, 'nfl'),
                                       'nfl-team-image', trend.team_abbreviation)
                st.markdown('<div class="nfl-scan">'
                    f'<span class="prop"><strong>{escape(market_label(trend.market))} {line}</strong>'
                    f'<small>{logo} {escape(trend.position or "N/A")} | {escape(trend.team_abbreviation)} '
                    f'vs {escape(opponents.get(trend.team_abbreviation, "N/A"))}</small></span>'
                    f'<span><small>{escape(quote.sportsbook)}</small>O {price(quote.over_price)} '
                    f' / U {price(quote.under_price)}</span>{signals}'
                    f'<span><small>{trend.last_10.games_considered} GP</small>'
                    f'<span class="nfl-micro">{micro}</span></span>'
                    f'<span>{"STALE" if "market_stale" in quote.concerns else "!" if trend.concerns else ""}</span>'
                    '</div>', unsafe_allow_html=True)
    return options[st.session_state[state_key]]


def render_compact_table(headers, rows) -> None:
    head = ''.join(f'<th>{escape(str(value))}</th>' for value in headers)
    body = ''.join('<tr>' + ''.join(
        f'<td class="nfl-{value if value in ("HIT", "MISS", "PUSH") else "value"}">'
        f'{escape(str(value))}</td>' for value in row
    ) + '</tr>' for row in rows)
    st.markdown(f'<div class="nfl-compact"><table><thead><tr>{head}</tr></thead>'
                f'<tbody>{body}</tbody></table></div>', unsafe_allow_html=True)


def render_quote_strip(line, over, under, book) -> None:
    st.markdown(
        '<div class="nfl-quote">'
        f'<span><small>Current line</small> <strong>{escape(str(line))}</strong></span>'
        f'<span>O {escape(over)} &nbsp; U {escape(under)}</span>'
        f'<small>{escape(book)}</small></div>', unsafe_allow_html=True,
    )

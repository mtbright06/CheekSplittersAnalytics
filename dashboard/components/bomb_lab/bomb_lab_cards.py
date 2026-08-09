import streamlit as st

from components.badges import recommendation_badge_html
from components.logos import team_logo_html


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "N/A"


def safe(value, default="N/A"):
    return value if value not in [None, "", "None"] else default


def side_label(side):
    side = str(side or "ANY").upper()

    if side == "L":
        return "LHB"
    if side == "R":
        return "RHB"
    if side == "BOTH":
        return "Both"

    return side


def render_bomb_pitcher_card(item):
    score = item.get("bomb_score") or 0
    tier = item.get("tier") or "PASS"
    offense = safe(item.get("opponent"), "Target Offense")
    pitcher = safe(item.get("pitcher"), "Pitcher Pending")
    pitching_team = safe(item.get("pitching_team"), "Pitching Team")
    score_class = vulnerability_class(score)
    risk_class = vulnerability_class(item.get("pitcher_risk"))

    html = (
        "<article class='bomb-research-card'>"
        "<div class='bomb-research-main'>"
        "<div class='bomb-research-identity'>"
        "<div class='bomb-research-team'>"
        f"<div class='bomb-research-logo'>{team_logo_html(offense, 'mlb')}</div>"
        "<div>"
        "<span>Attack Team</span>"
        f"<strong>{offense}</strong>"
        f"<small>{safe(item.get('game'))}</small>"
        "</div>"
        "</div>"
        "<div class='bomb-research-identity-grid'>"
        "<div class='bomb-research-side-field'>"
        "<span>Side</span>"
        f"<strong>{side_label(item.get('target_side'))}</strong>"
        "</div>"
        "<div class='bomb-research-pitcher-field'>"
        f"<div class='bomb-research-logo bomb-research-logo--small'>{team_logo_html(pitching_team, 'mlb')}</div>"
        "<div>"
        "<span>Pitcher</span>"
        f"<strong>{pitcher}</strong>"
        f"<small>{pitching_team}</small>"
        "</div>"
        "</div>"
        f"{reason_list(item.get('why', []))}"
        "</div>"
        "</div>"
        "<div class='bomb-research-panel'>"
        f"{primary_metric('Attack Score', f'{float(score):.1f}', score_class)}"
        f"{badge_metric('Attack Tier', recommendation_badge_html(tier))}"
        f"{metric('Risk', safe(item.get('pitcher_risk')), risk_class)}"
        f"{metric('Recent', safe(item.get('recent_risk')))}"
        f"{metric('HH%', pct(item.get('recent_hard_hit_pct')))}"
        f"{metric('Barrel%', pct(item.get('recent_barrel_pct')))}"
        f"{metric('Park', safe(item.get('environment')))}"
        "</div>"
        "</div>"
        "</article>"
    )
    st.markdown(html, unsafe_allow_html=True)


def metric(label, value, tone=""):
    tone_class = f" bomb-research-metric--{tone}" if tone else ""
    class_attr = f" class='{tone_class.strip()}'" if tone_class else ""
    return f"<div{class_attr}><span>{label}</span><strong>{value}</strong></div>"


def primary_metric(label, value, tone=""):
    tone_class = f" bomb-research-metric--primary bomb-research-metric--{tone}"
    return f"<div class='{tone_class}'><span>{label}</span><strong>{value}</strong></div>"


def badge_metric(label, badge):
    return f"<div class='bomb-research-metric--badge'><span>{label}</span>{badge}</div>"


def reason_list(reasons):
    items = [reason for reason in reasons[:3] if reason]
    if not items:
        return "<div class='bomb-research-intel'><span>Quick Intel</span><small>No supporting research notes loaded.</small></div>"
    rows = "".join(f"<li>{reason}</li>" for reason in items)
    return f"<div class='bomb-research-intel'><span>Quick Intel</span><ul>{rows}</ul></div>"


def vulnerability_class(score):
    try:
        number = float(score)
    except (TypeError, ValueError):
        return "neutral"

    if number >= 82:
        return "elite"
    if number >= 75:
        return "strong"
    if number >= 68:
        return "watch"
    return "neutral"

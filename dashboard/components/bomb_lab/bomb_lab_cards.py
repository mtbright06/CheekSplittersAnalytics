import streamlit as st


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
        return "LEFTIES"
    if side == "R":
        return "RIGHTIES"
    if side == "BOTH":
        return "BOTH SIDES"

    return side


def render_bomb_pitcher_card(item):
    score = item.get("bomb_score") or 0
    tier = item.get("tier") or "PASS"

    html = f"""
<div class="bomb-card compact">
  <div class="bomb-card-top">
    <div>
      <div class="bomb-tier">{tier}</div>
      <div class="bomb-title">
        {safe(item.get("pitcher"))}
        <span class="pitcher-team">({safe(item.get("pitching_team"))})</span>
      </div>
      <div class="bomb-subtitle">
        Target offense: {safe(item.get("opponent"))} · {safe(item.get("venue"))}
      </div>
    </div>
    <div class="bomb-score">{score:.1f}</div>
  </div>

  <div class="bomb-grid">
    <div><span>Attack Side</span><strong>{side_label(item.get("target_side"))}</strong></div>
    <div><span>Pitcher Risk</span><strong>{safe(item.get("pitcher_risk"))}</strong></div>
    <div><span>Environment</span><strong>{safe(item.get("environment"))}</strong></div>
    <div><span>Sample</span><strong>{safe(item.get("sample_confidence"))}</strong></div>
  </div>

  <div class="bomb-stats">
    <div><span>HH%</span><strong>{pct(item.get("recent_hard_hit_pct"))}</strong></div>
    <div><span>Barrel%</span><strong>{pct(item.get("recent_barrel_pct"))}</strong></div>
    <div><span>Avg EV</span><strong>{safe(item.get("recent_avg_ev"))}</strong></div>
    <div><span>HR/BBE</span><strong>{pct(item.get("recent_hr_per_bbe"))}</strong></div>
    <div><span>BBE</span><strong>{safe(item.get("recent_batted_balls"))}</strong></div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

    for reason in item.get("why", [])[:3]:
        st.markdown(
            f"<div class='reason'>💣 {reason}</div>",
            unsafe_allow_html=True,
        )

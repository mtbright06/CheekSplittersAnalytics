import streamlit as st


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "N/A"


def value(value):
    if value is None:
        return "N/A"

    return value


def render_bomb_pitcher_card(item):
    score = item.get("bomb_score") or 0
    tier = item.get("tier") or "PASS"

    html = f"""
<div class="bomb-card">
  <div class="bomb-card-top">
    <div>
      <div class="bomb-tier">{tier}</div>
      <div class="bomb-title">{item.get("pitcher")}</div>
      <div class="bomb-subtitle">
        {item.get("pitching_team")} vs {item.get("opponent")} · {item.get("venue")}
      </div>
    </div>
    <div class="bomb-score">{score:.1f}</div>
  </div>

  <div class="bomb-grid">
    <div><span>Target Side</span><strong>{item.get("target_side")}</strong></div>
    <div><span>Pitcher Risk</span><strong>{item.get("pitcher_risk")}</strong></div>
    <div><span>Environment</span><strong>{item.get("environment")}</strong></div>
    <div><span>Sample</span><strong>{item.get("sample_confidence")}</strong></div>
  </div>

  <div class="bomb-stats">
    <div><span>HH%</span><strong>{pct(item.get("recent_hard_hit_pct"))}</strong></div>
    <div><span>Barrel%</span><strong>{pct(item.get("recent_barrel_pct"))}</strong></div>
    <div><span>Avg EV</span><strong>{value(item.get("recent_avg_ev"))}</strong></div>
    <div><span>HR/BBE</span><strong>{pct(item.get("recent_hr_per_bbe"))}</strong></div>
    <div><span>BBE</span><strong>{value(item.get("recent_batted_balls"))}</strong></div>
  </div>

  <div class="bomb-stats">
    <div><span>Season HH%</span><strong>{pct(item.get("season_hard_hit_pct"))}</strong></div>
    <div><span>Season Barrel%</span><strong>{pct(item.get("season_barrel_pct"))}</strong></div>
    <div><span>Season EV</span><strong>{value(item.get("season_avg_ev"))}</strong></div>
    <div><span>Season HR/BBE</span><strong>{pct(item.get("season_hr_per_bbe"))}</strong></div>
    <div><span>Season BBE</span><strong>{value(item.get("season_batted_balls"))}</strong></div>
  </div>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)

    side_breakdown = item.get("side_breakdown", [])

    if side_breakdown:
        with st.expander("Side breakdown", expanded=False):
            st.dataframe(
                side_breakdown,
                
                width="stretch",
                hide_index=True,
            )

    for reason in item.get("why", []):
        st.markdown(
            f"<div class='reason'>💣 {reason}</div>",
            unsafe_allow_html=True,
        )
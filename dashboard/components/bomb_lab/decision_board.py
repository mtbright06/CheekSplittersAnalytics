import streamlit as st

from components.page_header import render_compact_header


def safe(value, default="N/A"):
    return value if value not in [None, "", "None"] else default


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "N/A"


def grade_from_score(score):
    try:
        score = float(score)
    except Exception:
        return "PASS"

    if score >= 90:
        return "A+"
    if score >= 82:
        return "A"
    if score >= 75:
        return "B+"
    if score >= 68:
        return "B"
    if score >= 60:
        return "C"
    return "PASS"


def label_from_score(score):
    try:
        score = float(score)
    except Exception:
        return "PASS"

    if score >= 90:
        return "🚨 NUCLEAR"
    if score >= 82:
        return "🔥 ELITE"
    if score >= 75:
        return "💣 STRONG"
    if score >= 68:
        return "👀 PLAYABLE"
    if score >= 60:
        return "WATCH"
    return "PASS"


def stars_from_score(score):
    try:
        score = float(score)
    except Exception:
        return "☆☆☆☆☆"

    if score >= 90:
        return "★★★★★"
    if score >= 82:
        return "★★★★☆"
    if score >= 75:
        return "★★★★"
    if score >= 68:
        return "★★★☆"
    if score >= 60:
        return "★★★"
    return "★★"


def side_text(side):
    side = str(side or "ANY").upper()

    if side == "L":
        return "LEFTIES"
    if side == "R":
        return "RIGHTIES"
    if side == "BOTH":
        return "BOTH SIDES"

    return "ANY"


def render_bomb_lab_header(summary):
    pitchers = summary.get(
        "pitchers_loaded",
        0,
    )
    elite = summary.get(
        "elite",
        0,
    )
    strong = summary.get(
        "strong",
        0,
    )
    watch = summary.get(
        "watch",
        0,
    )

    render_compact_header(
        "💣",
        "Bomb Lab",
        "Pitcher vulnerabilities, preferred hitter sides, and top HR targets.",
        [
            ("Pitchers", pitchers),
            ("Elite", elite),
            ("Strong", strong),
            ("Watch", watch),
        ],
    )

def render_decision_board(pitchers):
    st.markdown("### 🎯 Offenses to Target")

    for rank, item in enumerate(pitchers[:10], start=1):
        render_decision_card(rank, item)


def render_decision_card(rank, item):
    score = item.get("bomb_score") or 0
    offense = safe(item.get("opponent"))
    pitcher = safe(item.get("pitcher"))
    pitcher_team = safe(item.get("pitching_team"))
    venue = safe(item.get("venue"))
    attack_side = side_text(item.get("target_side"))
    grade = grade_from_score(score)
    label = label_from_score(score)
    stars = stars_from_score(score)
    environment = safe(item.get("environment"))

    targets = item.get("top_hitters", [])
    targets_html = ""

    if targets:
        targets_html = "".join(
            [
                f"<span>{h.get('stars')} {h.get('name')}</span>"
                for h in targets[:3]
            ]
        )
    else:
        targets_html = "<span>No hitter targets loaded yet</span>"

    why = item.get("why", [])[:2]
    why_html = "".join([f"<li>{reason}</li>" for reason in why])

    html = f"""
<div class="decision-v2-card">
  <div class="decision-v2-rank">{rank}</div>

  <div class="decision-v2-main">
    <div class="decision-v2-label">{label}</div>
    <div class="decision-v2-title">Attack {offense}</div>
    <div class="decision-v2-subtitle">vs {pitcher} ({pitcher_team}) · {venue}</div>
    <div class="decision-v2-stars">{stars}</div>
  </div>

  <div class="decision-v2-metrics">
    <div><span>Side</span><strong>{attack_side}</strong></div>
    <div><span>Bomb</span><strong>{score}</strong></div>
    <div><span>Grade</span><strong>{grade}</strong></div>
    <div><span>Env</span><strong>{environment}</strong></div>
  </div>

  <div class="decision-v2-targets">
    <span class="decision-v2-small-label">Top HR Targets</span>
    {targets_html}
  </div>

  <div class="decision-v2-why">
    <span class="decision-v2-small-label">Why</span>
    <ul>{why_html}</ul>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def render_game_explorer(item):
    if not item:
        st.info("No game selected.")
        return

    score = item.get("bomb_score") or 0
    offense = safe(item.get("opponent"))
    pitcher = safe(item.get("pitcher"))
    pitcher_team = safe(item.get("pitching_team"))
    attack_side = side_text(item.get("target_side"))
    grade = grade_from_score(score)

    html = f"""
<div class="game-v2-card">
  <div class="game-v2-header">
    <div>
      <div class="bomb-v2-kicker">OFFENSE TO TARGET</div>
      <div class="game-v2-title">{offense}</div>
      <div class="game-v2-subtitle">Attack {pitcher} ({pitcher_team})</div>
    </div>
    <div class="game-v2-score">
      <span>Bomb Score</span>
      <strong>{score}</strong>
    </div>
  </div>

  <div class="game-v2-grid">
    <div><span>Attack Side</span><strong>{attack_side}</strong></div>
    <div><span>Confidence</span><strong>{grade}</strong></div>
    <div><span>Environment</span><strong>{safe(item.get("environment"))}</strong></div>
    <div><span>Pitcher Risk</span><strong>{safe(item.get("pitcher_risk"))}</strong></div>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

    render_top_hitters(item)
    render_reasoning(item)
    render_metric_groups(item)


def render_top_hitters(item):
    targets = item.get("top_hitters", [])

    st.markdown("#### Top HR Targets")

    if not targets:
        st.info("No hitter targets loaded yet for this offense.")
        return

    for hitter in targets:
        html = f"""
<div class="target-hitter-row">
  <div>
    <strong>{hitter.get("stars")} {hitter.get("name")}</strong>
    <span>{hitter.get("team")} · Bats {hitter.get("bat_side")}</span>
  </div>
  <div class="target-score">{hitter.get("target_score")}</div>
</div>
"""
        st.markdown(html, unsafe_allow_html=True)


def render_reasoning(item):
    st.markdown("#### Why This Spot Matters")

    for reason in item.get("why", []):
        st.markdown(
            f"<div class='reason'>💣 {reason}</div>",
            unsafe_allow_html=True,
        )


def render_metric_groups(item):
    html = f"""
<div class="metric-groups">
  <div class="metric-group">
    <h4>Contact Damage</h4>
    <p><b>Barrel%</b> {pct(item.get("recent_barrel_pct"))}</p>
    <p><b>Hard Hit%</b> {pct(item.get("recent_hard_hit_pct"))}</p>
    <p><b>Avg EV</b> {safe(item.get("recent_avg_ev"))}</p>
  </div>

  <div class="metric-group">
    <h4>Power Profile</h4>
    <p><b>HR/BBE</b> {pct(item.get("recent_hr_per_bbe"))}</p>
    <p><b>Recent BBE</b> {safe(item.get("recent_batted_balls"))}</p>
    <p><b>Season BBE</b> {safe(item.get("season_batted_balls"))}</p>
  </div>

  <div class="metric-group">
    <h4>Season Baseline</h4>
    <p><b>Barrel%</b> {pct(item.get("season_barrel_pct"))}</p>
    <p><b>Hard Hit%</b> {pct(item.get("season_hard_hit_pct"))}</p>
    <p><b>HR/BBE</b> {pct(item.get("season_hr_per_bbe"))}</p>
  </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)

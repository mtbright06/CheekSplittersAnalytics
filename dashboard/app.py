import json
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
CARD_PATH = ROOT / "output" / "sharpstack_card.json"
LOGO_PATH = ROOT / "assets" / "logo.png"

st.set_page_config(
    page_title="SharpStack",
    page_icon="🍑",
    layout="wide",
)


st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(60, 83, 115, 0.38), transparent 34%),
            linear-gradient(135deg, #0b1018 0%, #111827 45%, #070a0f 100%);
        color: #f5f7fb;

    .logo-img {
        width: 72px;
        height: 72px;
        object-fit: cover;
        border-radius: 20px;
        border: 1px solid rgba(255,255,255,0.18);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 10px 30px rgba(0,0,0,0.35);
    }

    }




    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1420 0%, #070a0f 100%);
        border-right: 1px solid rgba(124, 181, 255, 0.18);
    }

    .app-header {
        padding: 22px 26px 18px 26px;
        border-radius: 22px;
        background:
            linear-gradient(135deg, rgba(25, 36, 54, 0.96), rgba(10, 14, 22, 0.96)),
            radial-gradient(circle at top right, rgba(113, 181, 255, 0.20), transparent 42%);
        border: 1px solid rgba(160, 190, 230, 0.18);
        box-shadow: 0 18px 55px rgba(0,0,0,0.40);
        margin-bottom: 18px;
    }

    .brand-row {
        display: flex;
        align-items: center;
        gap: 18px;
    }

    .logo-badge {
        width: 72px;
        height: 72px;
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        background:
            radial-gradient(circle at 30% 25%, #ffffff 0%, #d8e8ff 18%, transparent 19%),
            linear-gradient(145deg, #243b61, #101828);
        border: 1px solid rgba(255,255,255,0.18);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 10px 30px rgba(0,0,0,0.35);
        font-size: 34px;
    }

    .brand-title {
        font-size: 48px;
        font-weight: 1000;
        line-height: 0.95;
        letter-spacing: -1.5px;
        margin: 0;
        color: #f8fbff;
    }

    .brand-subtitle {
        color: #b9c7dc;
        font-size: 16px;
        font-weight: 700;
        margin-top: 6px;
    }

    .brand-tagline {
        display: inline-block;
        margin-top: 10px;
        padding: 7px 12px;
        border-radius: 999px;
        background: rgba(124, 181, 255, 0.10);
        border: 1px solid rgba(124, 181, 255, 0.22);
        color: #8ee6a3;
        font-weight: 900;
        font-size: 13px;
    }

    .top-nav {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 18px;
        padding-top: 16px;
        border-top: 1px solid rgba(255,255,255,0.08);
    }

    .nav-pill {
        padding: 9px 14px;
        border-radius: 999px;
        background: rgba(255,255,255,0.055);
        border: 1px solid rgba(255,255,255,0.09);
        color: #d8e3f5;
        font-weight: 850;
        font-size: 14px;
    }

    .nav-pill.active {
        background: linear-gradient(135deg, rgba(65, 134, 255, 0.35), rgba(35, 68, 120, 0.35));
        border-color: rgba(124, 181, 255, 0.38);
        color: #ffffff;
    }

    .section-title {
        font-size: 27px;
        font-weight: 950;
        margin: 20px 0 12px 0;
        color: #f8fbff;
    }

    .sharp-card {
        padding: 20px;
        border-radius: 18px;
        background: rgba(14, 21, 32, 0.88);
        border: 1px solid rgba(160, 190, 230, 0.12);
        box-shadow: 0 14px 36px rgba(0,0,0,0.28);
        margin-bottom: 18px;
    }

    .best-card {
        padding: 24px;
        border-radius: 20px;
        background:
            linear-gradient(135deg, rgba(16, 24, 36, 0.98), rgba(25, 45, 75, 0.94)),
            radial-gradient(circle at top right, rgba(117, 210, 255, 0.18), transparent 38%);
        border: 1px solid rgba(124, 181, 255, 0.30);
        box-shadow: 0 18px 60px rgba(0,0,0,0.38);
        margin-bottom: 24px;
    }

    .badge {
        display: inline-block;
        padding: 6px 12px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 900;
        letter-spacing: .4px;
        background: rgba(255,255,255,0.08);
        color: #ffffff;
        border: 1px solid rgba(255,255,255,0.14);
    }

    .badge-green {
        background: rgba(29, 97, 51, 0.45);
        color: #9cffb0;
        border-color: rgba(156,255,176,0.30);
    }

    .badge-gold {
        background: rgba(104, 78, 28, 0.45);
        color: #ffd976;
        border-color: rgba(255,217,118,0.30);
    }

    .muted {
        color: #aebbd0;
        font-size: 14px;
    }

    .small-label {
        color: #9dadc5;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 850;
    }

    .big-number {
        color: #8ee6a3;
        font-size: 42px;
        font-weight: 1000;
        line-height: 1;
    }

    .reason {
        padding: 8px 10px;
        border-radius: 10px;
        background: rgba(255,255,255,0.045);
        margin-bottom: 8px;
        border-left: 3px solid #8ee6a3;
    }

    .signal-row {
        display: flex;
        justify-content: space-between;
        padding: 8px 10px;
        border-radius: 10px;
        background: rgba(255,255,255,0.045);
        margin-bottom: 8px;
    }

    .pitcher-box {
        padding: 14px;
        border-radius: 14px;
        background: rgba(0,0,0,0.22);
        border: 1px solid rgba(160,190,230,0.10);
        min-height: 112px;
        margin-bottom: 10px;
    }

    .pitcher-name {
        font-size: 19px;
        font-weight: 950;
        color: #ffffff;
        margin-bottom: 4px;
    }

    .stMetric {
        background: rgba(255,255,255,0.035);
        padding: 10px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.06);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def logo_html():
    if LOGO_PATH.exists():
        return f'<img src="data:image/png;base64,{logo_base64()}" class="logo-img" />'

    return '{logo_html()}'

def logo_base64():
    import base64

    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()

def load_card():
    if not CARD_PATH.exists():
        return None
    with open(CARD_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def logo_html():
    if LOGO_PATH.exists():
        return f'<img src="data:image/png;base64,{logo_base64()}" class="logo-img" />'

    return '<div class="logo-badge">🍑⚾</div>'

def logo_base64():
    import base64

    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode()

def grade_label(edge):
    if edge is None:
        return "NO DATA"
    if edge >= 10:
        return "CHEEK RIPPER 🔥"
    if edge >= 7:
        return "STRONG PLAY"
    if edge >= 5:
        return "PLAYABLE"
    if edge >= 2:
        return "LEAN"
    return "PASS"


def badge_class(edge):
    if edge is None:
        return "badge"
    if edge >= 7:
        return "badge badge-green"
    if edge >= 2:
        return "badge badge-gold"
    return "badge"


def stat(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def pitcher_line(pitcher):
    name = pitcher.get("name") or "Unknown Starter"
    pieces = []

    if pitcher.get("throws"):
        pieces.append(f"{pitcher.get('throws')}HP")
    if pitcher.get("record"):
        pieces.append(pitcher.get("record"))
    if pitcher.get("era") is not None:
        pieces.append(f"{pitcher.get('era'):.2f} ERA")
    if pitcher.get("whip") is not None:
        pieces.append(f"{pitcher.get('whip'):.2f} WHIP")

    if pieces:
        return f"{name} ({' | '.join(pieces)})"

    return name


def render_header():
    st.markdown(
        """
        <div class="app-header">
            <div class="brand-row">
                <div class="logo-badge">🍑⚾</div>
                <div>
                    <div class="brand-title">SHARPSTACK</div>
                    <div class="brand-subtitle">Cheek Splitters Decision Support System</div>
                    <div class="brand-tagline">We split cheeks, not bankrolls.</div>
                </div>
            </div>
            <div class="top-nav">
                <span class="nav-pill active">🏠 Dashboard</span>
                <span class="nav-pill">⚾ MLB</span>
                <span class="nav-pill">🇰🇷 KBO</span>
                <span class="nav-pill">💣 Home Runs</span>
                <span class="nav-pill">🎯 Props</span>
                <span class="nav-pill">🏆 Hall of Fame</span>
                <span class="nav-pill">⚙ Settings</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_pitcher_card(title, pitcher):
    st.markdown(
        f"""
        <div class="pitcher-box">
            <div class="small-label">{title}</div>
            <div class="pitcher-name">{pitcher.get("name") or "Unknown Starter"}</div>
            <div class="muted">{pitcher_line(pitcher)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    cols[0].metric("IP", stat(pitcher.get("ip")))
    cols[1].metric("SO", stat(pitcher.get("so")))
    cols[2].metric("BB", stat(pitcher.get("bb")))
    cols[3].metric("HR", stat(pitcher.get("hr_allowed")))

    cols = st.columns(3)
    cols[0].metric("K/9", stat(pitcher.get("k_rate")))
    cols[1].metric("BB/9", stat(pitcher.get("bb_rate")))
    cols[2].metric("HR/9", stat(pitcher.get("hr9")))


def render_signals(signals):
    if not signals:
        st.markdown('<div class="muted">No signals available.</div>', unsafe_allow_html=True)
        return

    for signal in signals:
        st.markdown(
            f"""
            <div class="signal-row">
                <span>{signal.get("name")}</span>
                <strong>{signal.get("value")}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_reasons(reasons):
    if not reasons:
        st.markdown('<div class="muted">No reasons available.</div>', unsafe_allow_html=True)
        return

    for reason in reasons:
        st.markdown(f'<div class="reason">✅ {reason}</div>', unsafe_allow_html=True)


def render_game(game):
    matchup = game["matchup"]
    model = game["model"]
    pitching = game["pitching"]
    odds = game["odds"]

    edge = model.get("edge")
    confidence = model.get("confidence")

    st.markdown('<div class="sharp-card">', unsafe_allow_html=True)

    top = st.columns([3, 1, 1, 1])
    top[0].markdown(f"### {matchup['away']} @ {matchup['home']}")
    top[1].metric("Play", model.get("play"))
    top[2].metric("Edge", f"{edge}%")
    top[3].metric("Confidence", f"{confidence}/100")

    st.markdown(
        f"""
        <span class="{badge_class(edge)}">{grade_label(edge)}</span>
        <span class="muted">&nbsp; {model.get('market')} · Odds: {odds.get('moneyline')} · Book: {odds.get('book_probability')}%</span>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    left, right = st.columns(2)
    with left:
        render_pitcher_card(f"{matchup['away']} Starter", pitching["away"])
    with right:
        render_pitcher_card(f"{matchup['home']} Starter", pitching["home"])

    st.markdown("---")

    signal_col, reason_col = st.columns(2)
    with signal_col:
        st.markdown("#### Model Signals")
        render_signals(model.get("signals", []))
    with reason_col:
        st.markdown("#### Why We Like It")
        render_reasons(model.get("reasons", []))

    st.markdown("</div>", unsafe_allow_html=True)


card = load_card()
render_header()

if card is None:
    st.warning("No JSON card found. Run `python cheek_splitters_engine.py` first.")
    st.stop()

st.sidebar.markdown("## SHARPSTACK")
st.sidebar.caption("Cheeks operational.")
st.sidebar.metric("Sport", card.get("sport") or "N/A")
st.sidebar.metric("Version", card.get("version") or "N/A")
st.sidebar.write(f"Generated: {card.get('generated_at')}")
st.sidebar.markdown("---")
st.sidebar.write("🍑 Mode: Professional Nonsense")
st.sidebar.write("🔥 Status: Online")
st.sidebar.write("🍺 Beer: Recommended")

games = card.get("games", [])

if not games:
    st.info("No confirmed plays today. The cheeks remain unclapped.")
    st.stop()

best_game = max(games, key=lambda g: g["model"].get("edge") or 0)

st.markdown('<div class="section-title">🔥 Cheek Splitter of the Day</div>', unsafe_allow_html=True)

matchup = best_game["matchup"]
model = best_game["model"]

st.markdown('<div class="best-card">', unsafe_allow_html=True)
cols = st.columns([3, 1, 1])
cols[0].markdown(f"## {model.get('play')} ({model.get('market')})")
cols[0].caption(f"{matchup['away']} @ {matchup['home']} · {grade_label(model.get('edge'))}")
cols[1].markdown('<div class="small-label">Edge</div>', unsafe_allow_html=True)
cols[1].markdown(f'<div class="big-number">{model.get("edge")}%</div>', unsafe_allow_html=True)
cols[2].markdown('<div class="small-label">Confidence</div>', unsafe_allow_html=True)
cols[2].markdown(f'<div class="big-number">{model.get("confidence")}</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="section-title">Today’s Card</div>', unsafe_allow_html=True)

for game in sorted(games, key=lambda g: g["model"].get("edge") or 0, reverse=True):
    render_game(game)

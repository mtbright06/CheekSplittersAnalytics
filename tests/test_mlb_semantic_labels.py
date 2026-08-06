from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components import play_summary


def test_mlb_play_summary_labels_model_strength_separately_from_market_probability():
    rendered = []
    original_markdown = play_summary.st.markdown

    play_summary.st.markdown = (
        lambda html, unsafe_allow_html=False: rendered.append(html)
    )

    try:
        play_summary.render_play_summary(
            {
                "sport": "mlb",
                "matchup": {"away": "Away", "home": "Home"},
                "model": {
                    "play": "Away",
                    "market": "Moneyline",
                    "recommendation": "LEAN",
                    "model_win_strength": 0.58,
                    "model_probability": 0.58,
                    "model_confidence": 76.0,
                    "confidence": 76.0,
                },
                "odds": {
                    "book_probability": 0.52,
                    "moneyline": -110,
                    "real_market_loaded": True,
                },
            }
        )
    finally:
        play_summary.st.markdown = original_markdown

    html = "".join(rendered)

    assert "Model Win Strength" in html
    assert "Model Confidence" in html
    assert "Market Probability" not in html

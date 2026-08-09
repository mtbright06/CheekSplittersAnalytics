from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.status_pill import status_pill_html, status_pill_tone


def test_status_pill_maps_known_statuses_to_semantic_tones():
    cases = {
        "BET": "success",
        "WIN": "success",
        "COMPLETE": "success",
        "ACTIVE": "success",
        "LEAN": "warning",
        "PENDING": "warning",
        "PUSH": "warning",
        "LOSS": "danger",
        "PASS": "neutral",
        "MODEL ONLY": "neutral",
        "REAL MARKET": "accent",
    }

    for label, tone in cases.items():
        assert status_pill_tone(label) == tone


def test_status_pill_returns_escaped_compact_inline_html():
    html = status_pill_html("<script>alert(1)</script>", tone="success")

    assert "ss-status-pill" in html
    assert "ss-status-pill--compact" in html
    assert "ss-status-pill--success" in html
    assert "<script>" not in html
    assert "&lt;SCRIPT&gt;ALERT(1)&lt;/SCRIPT&gt;" in html


def test_status_pill_css_stays_compact_and_token_based():
    styles = (DASHBOARD / "styles.py").read_text()

    assert ".ss-status-pill" in styles
    assert "height: 23px" in styles
    assert "font-size: 11px" in styles
    assert "box-shadow" not in styles.partition(".ss-status-pill")[2].partition(".play-hero-metrics")[0]
    assert "var(--ss-color-accent" in styles
    assert "var(--ss-color-success" in styles

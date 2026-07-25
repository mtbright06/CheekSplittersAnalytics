import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard"))

from components.value_meter import value_meter_html


def test_kbo_value_meter_renders_model_analysis_without_market_placeholders():
    html = value_meter_html(
        {
            "sport": "kbo",
            "model": {
                "model_probability": 58.0,
                "edge": None,
            },
            "odds": {
                "book_probability": None,
            },
        }
    )

    assert "Model Assessment" in html
    assert "Model Score" in html
    assert "Book Win %" not in html
    assert "Value Edge" not in html
    assert "Unavailable" not in html


def test_mlb_value_meter_retains_market_comparison():
    html = value_meter_html(
        {
            "sport": "mlb",
            "model": {
                "model_probability": 58.0,
                "edge": 4.0,
            },
            "odds": {
                "book_probability": 54.0,
            },
        }
    )

    assert "Market vs Model" in html
    assert "Book Win %" in html
    assert "Value Edge" in html

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.data_table import render_data_table
import components.data_table as data_table
import components.first5.market_cards as market_cards


def test_render_data_table_keeps_native_dataframe_defaults(monkeypatch):
    rendered = {}
    markers = []

    monkeypatch.setattr(
        data_table.st,
        "markdown",
        lambda html, **kwargs: markers.append((html, kwargs)),
    )
    monkeypatch.setattr(
        data_table.st,
        "dataframe",
        lambda data, **kwargs: rendered.update(data=data, kwargs=kwargs),
    )

    rows = [{"A": 1, "B": None}]
    render_data_table(rows, css_class="ss-data-table ss-data-table--test")

    assert rendered["data"] is rows
    assert rendered["kwargs"] == {
        "width": "stretch",
        "hide_index": True,
    }
    assert markers == [
        (
            '<div class="ss-data-table ss-data-table--test"></div>',
            {"unsafe_allow_html": True},
        )
    ]


def test_first5_market_table_uses_data_table_without_changing_rows(monkeypatch):
    rendered = {}

    monkeypatch.setattr(
        market_cards,
        "render_data_table",
        lambda data, **kwargs: rendered.update(data=data, kwargs=kwargs),
    )

    market_cards.render_market_table(
        [
            {
                "matchup": "Away @ Home",
                "best_market_side": {
                    "recommendation": "NO MARKET",
                    "model_probability": 0.532,
                    "book_no_vig_probability": None,
                    "book_odds": -115,
                    "edge_pct": 2.4,
                    "expected_value_pct": 1.2,
                    "grade": "LEAN",
                },
                "f5_total_market": {
                    "book_line": 4.5,
                    "model_total": 4.91,
                    "lean": "PASS",
                    "run_edge": 0.41,
                },
            }
        ]
    )

    assert rendered["kwargs"] == {
        "css_class": "ss-data-table ss-data-table--first5-market",
    }
    assert list(rendered["data"][0].keys()) == [
        "Matchup",
        "Recommendation",
        "Model %",
        "Book %",
        "Book Odds",
        "Edge %",
        "EV %",
        "Grade",
        "F5 Total",
        "Model Total",
        "Total Lean",
        "Run Edge",
    ]
    assert rendered["data"][0]["Matchup"] == "Away @ Home"
    assert rendered["data"][0]["Recommendation"] == "NO MARKET"
    assert rendered["data"][0]["Model %"] == 53.2
    assert rendered["data"][0]["Book %"] is None


def test_table_styles_are_scoped_to_data_table_marker():
    styles = (DASHBOARD / "styles.py").read_text()
    table_css = styles.partition(".ss-data-table")[2].partition(".first5-confidence span")[0]

    assert '+ [data-testid="stDataFrame"]' in table_css
    assert '[role="columnheader"]' in table_css
    assert "min-height: 32px" in table_css
    assert "min-height: 34px" in table_css
    assert "var(--ss-color-text-secondary" in table_css


def test_only_first5_market_table_migrated_to_data_table():
    market_source = (
        DASHBOARD / "components" / "first5" / "market_cards.py"
    ).read_text()
    other_sources = [
        path
        for path in DASHBOARD.rglob("*.py")
        if path.name not in {"data_table.py", "market_cards.py"}
    ]

    assert "render_data_table(" in market_source

    for path in other_sources:
        assert "render_data_table(" not in path.read_text()

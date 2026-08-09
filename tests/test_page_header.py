from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.page_header import page_header_html


def test_page_header_returns_escaped_compact_markup():
    html = page_header_html(
        "<Best Bets>",
        "Official <card>",
        eyebrow="Official Card",
        status_html="<span class='ss-status-pill'>ACTIVE</span>",
    )

    assert "ss-page-header" in html
    assert "&lt;Best Bets&gt;" in html
    assert "Official &lt;card&gt;" in html
    assert "OFFICIAL CARD" in html
    assert "ss-status-pill" in html
    assert "<Best Bets>" not in html


def test_page_header_css_is_scoped_and_token_based():
    styles = (DASHBOARD / "styles.py").read_text()
    header_css = styles.partition(".ss-page-header")[2].partition("/* Shared Cards */")[0]

    assert ".ss-page-header__eyebrow" in header_css
    assert ".ss-page-header__title" in header_css
    assert "font-size: 26px" in header_css
    assert "font-size: 13px" in header_css
    assert "var(--ss-color-border" in header_css
    assert "box-shadow" not in header_css


def test_only_best_bets_uses_the_standard_page_header_for_this_migration():
    best_bets = (DASHBOARD / "pages" / "best_bets_page.py").read_text()
    page_sources = [
        path
        for path in (DASHBOARD / "pages").glob("*.py")
        if path.name != "best_bets_page.py"
    ]

    assert "render_page_header(" in best_bets
    assert "Official Card" in best_bets

    for path in page_sources:
        assert "render_page_header(" not in path.read_text()

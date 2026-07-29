from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def test_custom_navigation_includes_model_health_and_all_existing_routes():
    source = (DASHBOARD / "shell" / "navigation.py").read_text()

    for page in (
        "Dashboard",
        "Best Bets",
        "MLB",
        "KBO",
        "Bomb Lab",
        "Decisions",
        "Model Health",
        "Props",
        "First 5",
        "Hall",
        "Settings",
    ):
        assert page in source

    assert "NAVIGATION_GROUPS" in source


def test_streamlit_native_page_navigation_is_disabled():
    config = (ROOT / ".streamlit" / "config.toml").read_text()

    assert "showSidebarNavigation = false" in config


def test_app_routes_model_health_through_the_sharpstack_shell():
    source = (DASHBOARD / "app.py").read_text()

    assert "from pages.model_health_page import render_model_health_dashboard" in source
    assert 'elif page == "Model Health":' in source
    assert "render_model_health_dashboard()" in source
    assert "from shell import initialize_shell, render_application_shell" in source
    assert "initialize_shell()" in source
    assert "render_application_shell()" in source


def test_every_shell_route_remains_in_the_application_dispatcher():
    app_source = (DASHBOARD / "app.py").read_text()
    navigation_source = (DASHBOARD / "shell" / "navigation.py").read_text()

    for page in (
        "Dashboard",
        "Best Bets",
        "MLB",
        "KBO",
        "Bomb Lab",
        "Props",
        "First 5",
        "Decisions",
        "Model Health",
        "Hall",
        "Settings",
    ):
        assert page in navigation_source
        assert f'page == "{page}"' in app_source or page == "Dashboard"

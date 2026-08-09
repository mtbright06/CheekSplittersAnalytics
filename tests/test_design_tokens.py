from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOKENS = ROOT / "dashboard" / "design" / "tokens.py"
SHELL_STYLES = ROOT / "dashboard" / "shell" / "styles.py"


def test_design_tokens_define_the_approved_shared_categories():
    source = TOKENS.read_text()

    for token in (
        "--ss-color-app-background",
        "--ss-space-1",
        "--ss-radius-sm",
        "--ss-shadow-panel",
        "--ss-font-page-title",
        "--ss-size-sidebar",
    ):
        assert token in source


def test_shell_styles_consume_shared_design_tokens():
    source = SHELL_STYLES.read_text()

    for token in (
        "var(--ss-size-sidebar)",
        "var(--ss-size-control-compact)",
        "var(--ss-color-border)",
        "var(--ss-font-caption)",
    ):
        assert token in source


def test_compact_control_token_supports_dense_sidebar_navigation():
    source = TOKENS.read_text()

    assert "--ss-size-control-compact: 32px" in source

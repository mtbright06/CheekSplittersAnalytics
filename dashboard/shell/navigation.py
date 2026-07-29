"""Canonical dashboard navigation configuration."""

from __future__ import annotations


NAVIGATION_GROUPS = (
    (
        "Main",
        (
            ("Dashboard", "Dashboard"),
            ("Best Bets", "Best Bets"),
        ),
    ),
    (
        "Sports",
        (
            ("MLB", "MLB"),
            ("KBO", "KBO"),
            ("Bomb Lab", "Bomb Lab"),
            ("Props", "Props"),
            ("First 5", "First 5"),
        ),
    ),
    (
        "Analytics",
        (
            ("Decisions", "Decisions"),
            ("Model Health", "Model Health"),
            ("Hall", "Hall"),
        ),
    ),
    (
        "System",
        (("Settings", "Settings"),),
    ),
)


def navigation_pages() -> tuple[str, ...]:
    """Return every page exposed by the SharpStack application shell."""

    return tuple(
        page
        for _, entries in NAVIGATION_GROUPS
        for _, page in entries
    )

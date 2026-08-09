"""Canonical dashboard navigation configuration."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class NavigationItem:
    """A stable application route and its sidebar presentation metadata."""

    page: str
    label: str
    icon: str


@dataclass(frozen=True)
class NavigationGroup:
    """A visible navigation section; groups remain expanded by default."""

    key: str
    label: str
    items: tuple[NavigationItem, ...]
    collapsible: bool = True


NAVIGATION_GROUPS = (
    NavigationGroup(
        key="main",
        label="Main",
        items=(
            NavigationItem("Dashboard", "Dashboard", "⌂"),
            NavigationItem("Best Bets", "Best Bets", "★"),
        ),
    ),
    NavigationGroup(
        key="sports",
        label="Sports",
        items=(
            NavigationItem("MLB", "MLB", "◉"),
            NavigationItem("KBO", "KBO", "◌"),
            NavigationItem("Bomb Lab", "Bomb Lab", "●"),
            NavigationItem("Props", "Props", "◎"),
            NavigationItem("First 5", "First 5", "◷"),
        ),
    ),
    NavigationGroup(
        key="analytics",
        label="Analytics",
        items=(
            NavigationItem("Decisions", "Decisions", "◆"),
            NavigationItem("Model Health", "Model Health", "▥"),
            NavigationItem("Hall", "Hall", "♜"),
        ),
    ),
    NavigationGroup(
        key="system",
        label="System",
        items=(NavigationItem("Settings", "Settings", "⚙"),),
    ),
)


def navigation_pages() -> tuple[str, ...]:
    """Return every page exposed by the SharpStack application shell."""

    return tuple(
        item.page
        for group in NAVIGATION_GROUPS
        for item in group.items
    )


def navigation_item_label(
    page: str | None,
    items: tuple[NavigationItem, ...],
) -> str:
    """Return a safe display label while a sidebar group resynchronizes."""

    for item in items:
        if item.page == page:
            return f"{item.icon} {item.label}"
    return ""

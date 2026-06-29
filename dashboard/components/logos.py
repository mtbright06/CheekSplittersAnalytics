import base64
from pathlib import Path

from components.team_colors import team_color


ROOT = Path(__file__).resolve().parents[2]
LOGO_ROOT = ROOT / "assets" / "logos"


TEAM_ALIASES = {
    "LG Twins": "lg",
    "Doosan Bears": "doosan",
    "KIA Tigers": "kia",
    "Kiwoom Heroes": "kiwoom",
    "KT Wiz": "kt",
    "Lotte Giants": "lotte",
    "NC Dinos": "nc",
    "Samsung Lions": "samsung",
    "SSG Landers": "ssg",
    "Hanwha Eagles": "hanwha",
}


def image64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def team_key(team_name):
    return TEAM_ALIASES.get(team_name, team_name.lower().replace(" ", "_"))


def team_logo_path(team_name, sport="kbo"):
    return LOGO_ROOT / sport.lower() / f"{team_key(team_name)}.png"


def team_logo_html(team_name, sport="kbo"):
    path = team_logo_path(team_name, sport)

    if path.exists():
        return (
            f"<img src='data:image/png;base64,{image64(path)}' "
            f"class='team-logo' />"
        )

    initials = "".join(word[0] for word in team_name.split()[:2]).upper()

    return (
        f"<div class='team-logo-placeholder' "
        f"style='border-color:{team_color(team_name)};'>"
        f"{initials}</div>"
    )


def team_title_html(team_name, sport="kbo"):
    color = team_color(team_name)

    return (
        f"<div class='team-title' style='border-left:4px solid {color};'>"
        f"{team_logo_html(team_name, sport)}"
        f"<span>{team_name}</span>"
        "</div>"
    )


def matchup_title_html(away, home, sport="kbo"):
    return (
        "<div class='matchup-title'>"
        f"{team_title_html(away, sport)}"
        "<span class='matchup-at'>@</span>"
        f"{team_title_html(home, sport)}"
        "</div>"
    )

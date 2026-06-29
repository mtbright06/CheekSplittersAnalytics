import base64
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOGO_ROOT = ROOT / "assets" / "logos"


TEAM_ALIASES = {
    "LG Twins": "LG",
    "Doosan Bears": "DOOSAN",
    "KIA Tigers": "KIA",
    "Kiwoom Heroes": "KIWOOM",
    "KT Wiz": "KT",
    "Lotte Giants": "LOTTE",
    "NC Dinos": "NC",
    "Samsung Lions": "SAMSUNG",
    "SSG Landers": "SSG",
    "Hanwha Eagles": "HANWHA",
}


def image64(path: Path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def team_logo_path(team_name, sport="kbo"):
    key = TEAM_ALIASES.get(team_name, team_name)
    filename = f"{key}.png"
    return LOGO_ROOT / sport.lower() / filename


def team_logo_html(team_name, sport="kbo"):
    path = team_logo_path(team_name, sport)

    if not path.exists():
        return "<div class='team-logo-placeholder'>⚾</div>"

    return (
        f"<img src='data:image/png;base64,{image64(path)}' "
        f"class='team-logo' />"
    )


def matchup_title_html(away, home, sport="kbo"):
    return (
        "<div class='matchup-title'>"
        "<div class='team-title'>"
        f"{team_logo_html(away, sport)}"
        f"<span>{away}</span>"
        "</div>"
        "<span class='matchup-at'>@</span>"
        "<div class='team-title'>"
        f"{team_logo_html(home, sport)}"
        f"<span>{home}</span>"
        "</div>"
        "</div>"
    )

from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.cards import (
    _pitching_title,
    display_pitcher_name,
    is_pending_pitcher,
    pitcher_line,
)
from loaders.pitcher_loader import PitcherLoader
from models.pitcher import Pitcher
from providers.kbo_data_provider import KBODataProvider


def test_known_kbo_starter_renders_its_actual_name_and_profile_line():
    pitcher = {"name": "So Hyeong-jun", "era": 3.09, "whip": 1.34}

    assert display_pitcher_name(pitcher) == "So Hyeong-jun"
    assert "Awaiting official starter confirmation" not in pitcher_line(pitcher)


def test_missing_kbo_starter_renders_pending_state():
    pitcher = {"name": "Unknown Starter"}

    assert is_pending_pitcher(pitcher) is True
    assert display_pitcher_name(pitcher) == "Starter Pending"
    assert pitcher_line(pitcher) == "Awaiting official starter confirmation"


def test_identity_less_pitching_stats_are_not_presented_as_confirmed_starter_data():
    pitcher = {"name": "", "era": 3.09, "whip": 1.34, "ip": 67.0}

    assert display_pitcher_name(pitcher) == "Unconfirmed Pitching Data"
    assert "not confirmed starter data" in pitcher_line(pitcher)
    assert _pitching_title("Away", pitcher, "kbo") == "Away Pitching Data"


def test_kbo_pitcher_loader_uses_the_profile_name_when_summary_name_is_blank(monkeypatch):
    monkeypatch.setattr(
        KBODataProvider,
        "get_pitcher_details",
        lambda url: {
            "name": "So Hyeong-jun",
            "throws": "R",
            "bats": "R",
            "record": "5-0",
            "era": 3.09,
            "whip": 1.34,
            "ip": 67.0,
            "so": 53,
            "bb": 13,
            "hr_allowed": 3,
            "k_rate": 7.12,
            "bb_rate": 1.75,
            "hr9": 0.4,
        },
    )
    pitcher = Pitcher()

    PitcherLoader._apply_live_pitcher(
        pitcher,
        {"name": "", "record": "5-0", "era": "3.09", "profile_url": "profile"},
    )

    assert pitcher.name == "So Hyeong-jun"
    assert pitcher.starter_confirmed is True
    assert pitcher.data_source == "starter_profile"

from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from components.kbo.workstation import kbo_workstation_html


def test_kbo_workstation_distinguishes_inactive_components_from_zeroes():
    html = kbo_workstation_html(
        {
            "matchup": {
                "away": "Away",
                "home": "Home",
            },
            "teams": {
                "away": {
                    "offense": {
                        "offense_source": "LIVE_TEAM_SPLITS",
                    }
                },
                "home": {
                    "offense": {
                        "offense_source": "LIVE_TEAM_SPLITS",
                    }
                },
            },
            "pitching": {
                "away": {"name": "Away Starter"},
                "home": {"name": "Home Starter"},
            },
            "model": {
                "play": "Away",
                "recommendation": "✅ PLAY",
                "model_strength": 56.8,
                "confidence": 95.0,
                "confidence_breakdown": {
                    "basis": "KBO current input reliability",
                    "offense": 0.0,
                    "starter_identity": 0.0,
                    "starter_stats": 0.0,
                    "schedule_mapping": -5.0,
                },
                "signals": [
                    {"name": "Starting Pitching", "value": 0.42},
                    {"name": "Offense", "value": 0.18},
                    {"name": "Bullpen", "value": 0.0},
                    {"name": "Recent Form", "value": 0.0},
                ],
                "inactive_components": [
                    {
                        "name": "Bullpen",
                        "status": "NOT_MODELED",
                        "reason": "No trustworthy KBO bullpen input is active.",
                    },
                    {
                        "name": "Recent Form",
                        "status": "NOT_MODELED",
                        "reason": "No trustworthy KBO recent-form input is active.",
                    },
                ],
            },
            "odds": {},
        }
    )

    assert "Model Strength" in html
    assert "Reliability" in html
    assert "LIVE_TEAM_SPLITS" in html
    assert "Starting Pitching" in html
    assert "Offense" in html
    assert "Bullpen" in html
    assert "Recent Form" in html
    assert html.count("Not modeled") == 2
    assert "Reliability Concerns" in html
    assert "Schedule mapping -5" in html

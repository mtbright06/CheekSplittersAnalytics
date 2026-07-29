from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def test_dashboard_entrypoint_resolves_the_application_package_before_pages():
    code = f'''
import sys
from pathlib import Path
root = Path({str(ROOT)!r})
dashboard = Path({str(DASHBOARD)!r})
sys.path.insert(0, str(dashboard))
from pages.model_health_page import render_model_health_dashboard
import app
from app.services.recommendation_analytics_service import RecommendationAnalyticsService
assert Path(app.__file__).resolve() == root / "app" / "__init__.py"
assert RecommendationAnalyticsService.__module__ == "app.services.recommendation_analytics_service"
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

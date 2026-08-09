from __future__ import annotations

import json
import tempfile
from pathlib import Path

from engine.nhl.moneypuck import (
    MoneyPuckProvider,
    normalize_moneypuck_goalie_stats,
    normalize_moneypuck_situation,
    normalize_moneypuck_skater_stats,
    normalize_moneypuck_team_stats,
    validate_moneypuck_csv,
)


class FakeResponse:
    def __init__(
        self,
        text: str,
        *,
        status_error: Exception | None = None,
        content_type: str = "text/csv",
        url: str = "https://moneypuck.com/test.csv",
    ):
        self.text = text
        self._status_error = status_error
        self.headers = {"content-type": content_type}
        self.url = url

    def raise_for_status(self) -> None:
        if self._status_error:
            raise self._status_error
        return None


TEAM_CSV = """team,season,name,position,situation,games_played,iceTime,xGoalsPercentage,xGoalsFor,xGoalsAgainst,shotAttemptsFor,shotAttemptsAgainst,shotsOnGoalFor,shotsOnGoalAgainst,goalsFor,goalsAgainst,highDangerxGoalsFor,highDangerxGoalsAgainst
BOS,2025,BOS,Team Level,5on5,82,241000,0.53,180.2,160.1,4100,3900,2500,2400,230,210,55.2,48.1
"""


SKATER_CSV = """playerId,season,name,team,position,situation,games_played,icetime,I_F_shotsOnGoal,I_F_shotAttempts,I_F_xGoals,I_F_goals,I_F_points,OnIce_F_xGoals,OnIce_A_xGoals,I_F_highDangerShots,I_F_highDangerxGoals
8478402,2025,Connor McDavid,EDM,C,all,82,1800,300,520,42.5,44,132,120.1,80.2,90,22.4
"""


GOALIE_CSV = """playerId,season,name,team,position,situation,games_played,icetime,xGoals,goals,ongoal,highDangerShots,highDangerxGoals
8480280,2025,Jeremy Swayman,BOS,G,5on5,55,3100,130.5,125,1500,390,66.5
"""


def test_situation_normalization_preserves_moneypuck_context():
    assert normalize_moneypuck_situation("all") == "ALL"
    assert normalize_moneypuck_situation("5on5") == "5ON5"
    assert normalize_moneypuck_situation("5on4") == "5ON4"
    assert normalize_moneypuck_situation("4on5") == "4ON5"
    assert normalize_moneypuck_situation("other") == "OTHER"
    assert normalize_moneypuck_situation("bad") is None


def test_team_advanced_normalization_preserves_team_and_situation():
    stats = normalize_moneypuck_team_stats(
        _rows(TEAM_CSV)
    )

    team = stats[0]
    assert team.team_abbreviation == "BOS"
    assert team.season == 2025
    assert team.situation == "5ON5"
    assert team.games_played == 82
    assert team.x_goals_for == 180.2
    assert team.x_goals_against == 160.1
    assert team.shot_attempts_for == 4100.0
    assert team.source == "MoneyPuck.com"


def test_skater_advanced_normalization_preserves_nhl_player_id():
    stats = normalize_moneypuck_skater_stats(
        _rows(SKATER_CSV)
    )

    skater = stats[0]
    assert skater.player_id == 8478402
    assert skater.name == "Connor McDavid"
    assert skater.team_abbreviation == "EDM"
    assert skater.position == "C"
    assert skater.situation == "ALL"
    assert skater.individual_x_goals == 42.5
    assert skater.on_ice_x_goals_for == 120.1
    assert skater.source == "MoneyPuck.com"


def test_goalie_advanced_normalization_derives_gsax_from_xga_minus_goals():
    stats = normalize_moneypuck_goalie_stats(
        _rows(GOALIE_CSV)
    )

    goalie = stats[0]
    assert goalie.player_id == 8480280
    assert goalie.name == "Jeremy Swayman"
    assert goalie.team_abbreviation == "BOS"
    assert goalie.situation == "5ON5"
    assert goalie.expected_goals_against == 130.5
    assert goalie.goals_against == 125.0
    assert goalie.goals_saved_above_expected == 5.5
    assert goalie.source == "MoneyPuck.com"


def test_malformed_unknown_and_duplicate_rows_are_safe():
    duplicate = _rows(TEAM_CSV)[0]
    assert normalize_moneypuck_team_stats([duplicate, duplicate]) == (
        normalize_moneypuck_team_stats([duplicate])
    )
    assert normalize_moneypuck_team_stats(
        [{**duplicate, "situation": "unsupported"}]
    ) == []
    assert normalize_moneypuck_skater_stats(
        [{**_rows(SKATER_CSV)[0], "playerId": ""}]
    ) == []
    assert normalize_moneypuck_goalie_stats(
        [{**_rows(GOALIE_CSV)[0], "name": ""}]
    ) == []


def test_provider_caches_downloads_and_handles_html_license_page():
    calls = []

    def fetcher(url: str, **kwargs):
        calls.append(url)
        if url.endswith("teams.csv"):
            return FakeResponse(TEAM_CSV)
        if url.endswith("skaters.csv"):
            return FakeResponse(SKATER_CSV)
        if url.endswith("goalies.csv"):
            return FakeResponse(GOALIE_CSV)
        raise AssertionError(url)

    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=fetcher,
            cache_dir=tmpdir,
        )

        assert provider.load_team_advanced_stats(season=2025)
        assert provider.load_team_advanced_stats(season=2025)
        assert provider.load_skater_advanced_stats(season=2025)
        assert provider.load_goalie_advanced_stats(season=2025)
        assert len(calls) == 3

        html_provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse("<html>license</html>"),
            cache_dir=Path(tmpdir) / "html",
        )
        assert html_provider.load_team_advanced_stats(season=2025) == []


def test_provider_failure_degrades_to_empty_stats():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("down")
            ),
            cache_dir=tmpdir,
        )

        assert provider.load_team_advanced_stats(season=2025) == []
        assert provider.load_skater_advanced_stats(season=2025) == []
        assert provider.load_goalie_advanced_stats(season=2025) == []


def test_successful_remote_csv_creates_known_good_cache_and_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse(TEAM_CSV),
            cache_dir=tmpdir,
        )

        result = provider.refresh_dataset(
            season=2025,
            dataset="teams.csv",
        )

        cache_path = Path(tmpdir) / "2025" / "regular" / "teams.csv"
        metadata_path = cache_path.with_suffix(".csv.json")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert result.success is True
        assert cache_path.read_text(encoding="utf-8") == TEAM_CSV
        assert metadata["source"] == "MoneyPuck.com"
        assert metadata["dataset"] == "teams.csv"
        assert metadata["row_count"] == 1
        assert metadata["last_refresh_status"] == "success"


def test_subsequent_load_uses_cache_without_network():
    calls = []

    def fetcher(*args, **kwargs):
        calls.append(args[0])
        return FakeResponse(TEAM_CSV)

    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=fetcher,
            cache_dir=tmpdir,
        )
        assert provider.load_team_advanced_stats(season=2025)
        second_provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("network should not be used")
            ),
            cache_dir=tmpdir,
        )

        assert second_provider.load_team_advanced_stats(season=2025)
        assert len(calls) == 1


def test_html_malformed_wrong_schema_and_empty_csv_are_rejected():
    for text in (
        "<html>license</html>",
        "not,csv\n",
        "team,season\nBOS,2025\n",
        TEAM_CSV.splitlines()[0] + "\n",
    ):
        try:
            validate_moneypuck_csv(text, "teams.csv")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid CSV should fail validation")


def test_failed_refresh_cannot_overwrite_known_good_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse(TEAM_CSV),
            cache_dir=tmpdir,
        )
        assert provider.refresh_dataset(season=2025, dataset="teams").success
        cache_path = Path(tmpdir) / "2025" / "regular" / "teams.csv"
        original = cache_path.read_text(encoding="utf-8")

        failing_provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse("<html>blocked</html>"),
            cache_dir=tmpdir,
        )
        result = failing_provider.refresh_dataset(
            season=2025,
            dataset="teams.csv",
        )
        metadata = json.loads(
            cache_path.with_suffix(".csv.json").read_text(encoding="utf-8")
        )

        assert result.success is False
        assert cache_path.read_text(encoding="utf-8") == original
        assert metadata["last_refresh_status"] == "failed"
        assert metadata["row_count"] == 1


def test_network_failure_with_valid_cache_survives_and_loads():
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse(TEAM_CSV),
            cache_dir=tmpdir,
        )
        assert provider.refresh_dataset(season=2025, dataset="teams").success

        offline = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: (_ for _ in ()).throw(
                RuntimeError("down")
            ),
            cache_dir=tmpdir,
        )

        assert offline.load_team_advanced_stats(season=2025)


def test_refresh_success_atomically_replaces_cache():
    updated = TEAM_CSV.replace("0.53", "0.55")
    with tempfile.TemporaryDirectory() as tmpdir:
        provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse(TEAM_CSV),
            cache_dir=tmpdir,
        )
        assert provider.refresh_dataset(season=2025, dataset="teams").success
        provider = MoneyPuckProvider(
            fetcher=lambda *args, **kwargs: FakeResponse(updated),
            cache_dir=tmpdir,
        )

        assert provider.refresh_dataset(season=2025, dataset="teams").success
        assert provider.load_team_advanced_stats(
            season=2025
        )[0].x_goals_percentage == 0.55


def _rows(text: str) -> list[dict[str, str]]:
    import csv
    import io

    return list(csv.DictReader(io.StringIO(text)))

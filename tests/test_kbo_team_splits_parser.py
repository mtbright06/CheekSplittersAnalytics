from parsers.team_splits_parser import TeamSplitsParser
from providers.kbo_data_provider import KBODataProvider


TEAMS = [
    ("KT Wiz", 5.61, 5.59, 5.63, 4.80, 4.75),
    ("Samsung Lions", 5.72, 5.57, 5.86, 5.90, 4.61),
    ("LG Twins", 5.08, 5.04, 5.12, 6.30, 5.16),
    ("Doosan Bears", 4.61, 4.50, 4.72, 5.80, 5.10),
    ("Kia Tigers", 5.34, 5.20, 5.48, 6.10, 4.90),
    ("Hanwha Eagles", 4.95, 4.80, 5.10, 5.60, 5.00),
    ("NC Dinos", 5.20, 5.00, 5.40, 5.80, 4.70),
    ("Lotte Giants", 4.90, 4.70, 5.10, 4.60, 5.20),
    ("SSG Landers", 4.80, 4.60, 5.00, 4.50, 5.30),
    ("Kiwoom Heroes", 4.30, 4.10, 4.50, 4.40, 5.70),
]


def _table(label, values_index):
    rows = [
        "<tr><th>{}</th><th>G</th><th>W</th><th>L</th><th>D</th>"
        "<th>W%</th><th>R/G</th><th>-R/G</th><th>ERA_{{SP}}</th>"
        "<th>ERA_{{RP}}</th></tr>".format(label)
    ]
    for index, (team, season, home, away, last_10, allowed) in enumerate(
        reversed(TEAMS),
        start=1,
    ):
        rpg = (season, home, away, last_10)[values_index]
        rows.append(
            "<tr><td>{}</td><td>{}</td><td>0</td><td>0</td><td>0</td>"
            "<td>.500</td><td>{:.2f}</td><td>{:.2f}</td><td>{:.2f}</td><td>{:.2f}</td></tr>".format(
                team,
                90 + index,
                rpg,
                allowed,
                4.00 + (index / 10),
                3.00 + (index / 10),
            )
        )
    return "<table>{}</table>".format("".join(rows))


def _html():
    return (
        _table("Season", 0)
        + _table("Home", 1)
        + _table("Away", 2)
        + _table("Last 10G", 3)
    )


def test_team_splits_parser_maps_all_kbo_teams_by_identity():
    dataset = TeamSplitsParser.parse(
        _html(),
        retrieved_at="2026-08-07T16:00:00",
    )

    assert len(dataset.teams) == 10
    assert dataset.teams["KIA Tigers"]["runs_per_game"] == 5.34
    assert dataset.teams["KT Wiz"]["home_runs_per_game"] == 5.59
    assert dataset.teams["Samsung Lions"]["away_runs_per_game"] == 5.86
    assert dataset.teams["Kiwoom Heroes"]["runs_allowed_per_game"] == 5.70
    assert dataset.teams["Kiwoom Heroes"]["bullpen_era"] == 3.10
    assert dataset.teams["Kiwoom Heroes"]["starting_era"] == 4.10
    assert dataset.teams["KT Wiz"]["last_10_runs_per_game"] == 4.80
    assert dataset.teams["KT Wiz"]["last_10_games"] == 100
    assert dataset.league_starting_era == 4.55
    assert dataset.league_bullpen_era == 3.55
    assert dataset.league_rpg == 5.051


def test_team_splits_parser_rejects_missing_team_rows():
    broken = _html().replace(
        "<td>Kiwoom Heroes</td>",
        "<td>Missing Heroes</td>",
        1,
    )

    try:
        TeamSplitsParser.parse(
            broken,
            retrieved_at="2026-08-07T16:00:00",
        )
    except ValueError as exc:
        assert "mapping mismatch" in str(exc)
    else:
        raise AssertionError("Expected parser to reject missing KBO team.")


def test_kbo_provider_live_team_splits_supersede_static_fallback(monkeypatch):
    dataset = TeamSplitsParser.parse(
        _html(),
        retrieved_at="2026-08-07T16:00:00",
    )
    monkeypatch.setattr(KBODataProvider, "_team_splits_cache", dataset)

    team = KBODataProvider.get_team_data("KT Wiz")

    assert team["offense"]["runs_per_game"] == 5.61
    assert team["offense"]["league_runs_per_game"] == 5.051
    assert team["offense"]["league_starting_era"] == 4.55
    assert team["offense"]["bullpen_era"] == 4.0
    assert team["offense"]["league_bullpen_era"] == 3.55
    assert team["offense"]["last_10_runs_per_game"] == 4.80
    assert team["offense"]["last_10_games"] == 100
    assert team["offense"]["bullpen_source"] == "LIVE_TEAM_SPLITS"
    assert team["offense"]["offense_source"] == "LIVE_TEAM_SPLITS"


def test_kbo_provider_static_fallback_is_explicit(monkeypatch):
    monkeypatch.setattr(KBODataProvider, "_team_splits_cache", False)

    team = KBODataProvider.get_team_data("KT Wiz")

    assert team["offense"]["runs_per_game"] == 4.7
    assert team["offense"]["offense_source"] == "STATIC_FALLBACK"

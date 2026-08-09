from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

from pages.dashboard_page import (  # noqa: E402
    _alternate_bomb_ticket,
    _bomb_parlay_hitters,
    _lucky_bomb_ticket,
)


def bomb_pitcher(game_pk, opponent, hitters):
    return {
        "game_pk": game_pk,
        "game": f"Pitching Team vs {opponent}",
        "pitching_team": f"Pitching {game_pk}",
        "opponent": opponent,
        "top_hitters": hitters,
    }


def bomb_hitter(name, team, target, opportunity=45.0, hitter_id=None):
    return {
        "batter_id": hitter_id or f"{team}-{name}",
        "name": name,
        "team": team,
        "bat_side": "R",
        "target_score": target,
        "hr_opportunity_score": opportunity,
        "hr": 12,
    }


def bomb_card_for_parlay():
    return {
        "generated_at": "fixture-build",
        "pitchers": [
            bomb_pitcher(
                "game-1",
                "Team A",
                [
                    bomb_hitter("Official A", "Team A", 90),
                    bomb_hitter("Alt A", "Team A", 88),
                ],
            ),
            bomb_pitcher(
                "game-2",
                "Team B",
                [
                    bomb_hitter("Official B", "Team B", 89),
                    bomb_hitter("Alt B", "Team B", 87),
                ],
            ),
            bomb_pitcher(
                "game-3",
                "Team C",
                [
                    bomb_hitter("Official C", "Team C", 88),
                    bomb_hitter("Alt C", "Team C", 86),
                ],
            ),
            bomb_pitcher(
                "game-4",
                "Team D",
                [
                    bomb_hitter("Alt D", "Team D", 85),
                ],
            ),
            bomb_pitcher(
                "game-5",
                "Team E",
                [
                    bomb_hitter("Alt E", "Team E", 84),
                ],
            ),
            bomb_pitcher(
                "game-6",
                "Team F",
                [
                    bomb_hitter("Alt F", "Team F", 83),
                ],
            ),
        ],
    }


def test_official_bomb_parlay_behavior_is_unchanged():
    card = bomb_card_for_parlay()

    hitters = _bomb_parlay_hitters(card)

    assert [hitter["name"] for hitter in hitters] == [
        "Official A",
        "Official B",
        "Official C",
    ]
    assert [hitter["team"] for hitter in hitters] == [
        "Team A",
        "Team B",
        "Team C",
    ]


def test_alternate_bomb_parlay_is_deterministic_and_excludes_official_hitters():
    card = bomb_card_for_parlay()
    official = {
        "hitters": _bomb_parlay_hitters(card),
    }

    first = _alternate_bomb_ticket(card, official)
    second = _alternate_bomb_ticket(card, official)

    assert first == second
    assert [hitter["name"] for hitter in first["hitters"]] == [
        "Alt D",
        "Alt E",
        "Alt F",
    ]
    assert {
        hitter["team"]
        for hitter in first["hitters"]
    }.isdisjoint({"Team A", "Team B", "Team C"})


def test_alternate_bomb_parlay_allows_official_teams_but_never_hitters_when_needed():
    card = {
        "generated_at": "fixture-build",
        "pitchers": bomb_card_for_parlay()["pitchers"][:3],
    }
    official = {
        "hitters": _bomb_parlay_hitters(card),
    }

    alternate = _alternate_bomb_ticket(card, official)

    assert [hitter["name"] for hitter in alternate["hitters"]] == [
        "Alt A",
        "Alt B",
        "Alt C",
    ]
    assert not {
        hitter["name"]
        for hitter in alternate["hitters"]
    }.intersection({"Official A", "Official B", "Official C"})


def test_lucky_bomb_ticket_uses_unique_hitters_teams_and_games():
    ticket = _lucky_bomb_ticket(
        bomb_card_for_parlay(),
        seed=42,
    )

    hitters = ticket["hitters"]

    assert len(hitters) == 3
    assert len({hitter["name"] for hitter in hitters}) == 3
    assert len({hitter["team"] for hitter in hitters}) == 3
    assert len({hitter["game_id"] for hitter in hitters}) == 3
    assert all(hitter["target_score"] >= 80 for hitter in hitters)


def test_lucky_bomb_ticket_never_uses_lower_threshold_fallback():
    card = {
        "generated_at": "fixture-build",
        "pitchers": [
            bomb_pitcher("game-1", "Team A", [bomb_hitter("A", "Team A", 81)]),
            bomb_pitcher("game-2", "Team B", [bomb_hitter("B", "Team B", 79)]),
            bomb_pitcher("game-3", "Team C", [bomb_hitter("C", "Team C", 70)]),
            bomb_pitcher("game-4", "Team D", [bomb_hitter("D", "Team D", 65)]),
        ],
    }

    ticket = _lucky_bomb_ticket(card, seed=7)

    assert ticket["target_floor"] == 80.0
    assert ticket["complete"] is False
    assert len(ticket["hitters"]) == 1
    assert all(hitter["target_score"] >= 80 for hitter in ticket["hitters"])


def test_lucky_bomb_ticket_three_eligible_hitters_still_produces_valid_ticket():
    card = {
        "generated_at": "fixture-build",
        "pitchers": [
            bomb_pitcher("game-1", "Team A", [bomb_hitter("A", "Team A", 81)]),
            bomb_pitcher("game-2", "Team B", [bomb_hitter("B", "Team B", 82)]),
            bomb_pitcher("game-3", "Team C", [bomb_hitter("C", "Team C", 83)]),
            bomb_pitcher("game-4", "Team D", [bomb_hitter("D", "Team D", 79)]),
        ],
    }

    ticket = _lucky_bomb_ticket(card, seed=7)

    assert ticket["target_floor"] == 80.0
    assert ticket["complete"] is True
    assert len(ticket["hitters"]) == 3
    assert all(hitter["target_score"] >= 80 for hitter in ticket["hitters"])


def test_lucky_bomb_ticket_same_seed_is_stable_and_new_seed_can_differ():
    card = bomb_card_for_parlay()

    first = _lucky_bomb_ticket(card, seed=11)
    second = _lucky_bomb_ticket(card, seed=11)
    third = _lucky_bomb_ticket(card, seed=12)

    assert first == second
    assert first["hitters"] != third["hitters"]


def test_lucky_bomb_ticket_handles_insufficient_pool_safely():
    card = {
        "generated_at": "fixture-build",
        "pitchers": [
            bomb_pitcher("game-1", "Team A", [bomb_hitter("A", "Team A", 80)]),
            bomb_pitcher("game-2", "Team B", [bomb_hitter("B", "Team B", 64)]),
        ],
    }

    ticket = _lucky_bomb_ticket(card, seed=4)

    assert ticket["complete"] is False
    assert len(ticket["hitters"]) == 1
    assert ticket["hitters"][0]["target_score"] >= 80

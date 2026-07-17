from __future__ import annotations

from engine.mlb.totals import (
    build_totals_projection,
)


from datetime import datetime
from types import SimpleNamespace
from typing import Any

from engine.mlb.offense import fetch_team_batting_stats
from engine.mlb.pitchers import fetch_pitcher_stats
from engine.mlb.team_mapping import MLB_TEAM_ABBR
from engine.model.sharpscore import build_sharpscore_decision
from engine.odds.best_line import select_best_quote
from engine.odds.provider_factory import get_odds_provider


MAXIMUM_QUOTE_AGE_MINUTES = 20


def clean(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def get_value(
    obj: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def pitcher_from_team(team_blob: dict) -> dict:
    pitcher = team_blob.get("probablePitcher") or {}
    pitcher_id = pitcher.get("id")

    stats = fetch_pitcher_stats(pitcher_id)

    return {
        "id": pitcher_id,
        "name": (
            pitcher.get("fullName")
            or "Unknown Starter"
        ),
        "throws": pitcher.get(
            "pitchHand",
            {},
        ).get("code"),
        "record": stats.get("record"),
        "era": stats.get("era"),
        "whip": stats.get("whip"),
        "ip": stats.get("ip"),
        "so": stats.get("so"),
        "bb": stats.get("bb"),
        "hr_allowed": stats.get(
            "hr_allowed"
        ),
        "k_rate": stats.get("k_rate"),
        "bb_rate": stats.get("bb_rate"),
        "hr9": stats.get("hr9"),
    }


def team_profile(team_blob: dict) -> dict:
    team = team_blob.get("team", {})
    name = team.get("name")
    team_id = team.get("id")

    return {
        "id": team_id,
        "name": name,
        "abbr": MLB_TEAM_ABBR.get(name),
        "record": None,
        "form": None,
        "offense": fetch_team_batting_stats(
            team_id
        ),
        "bullpen": {
            "era": None,
            "whip": None,
            "fip": None,
            "recent_usage": None,
        },
    }


def unavailable_quote_dict() -> dict:
    return {
        "provider": None,
        "sportsbook": "Unavailable",
        "league": "MLB",
        "market": "Moneyline",
        "selection": None,
        "moneyline": None,
        "american_odds": None,
        "book_probability": None,
        "implied_probability": None,
        "edge_pct": None,
        "expected_value_pct": None,
        "event_id": None,
        "commence_time": None,
        "last_updated": None,
        "stale": True,
        "real_market_loaded": False,
        "quotes_compared": 0,
    }


def quote_to_dict(
    quote: Any,
) -> dict:
    if not quote:
        return unavailable_quote_dict()

    american_odds = get_value(
        quote,
        "american_odds",
    )

    implied_probability = get_value(
        quote,
        "implied_probability",
    )

    return {
        "provider": get_value(
            quote,
            "provider",
        ),
        "sportsbook": get_value(
            quote,
            "sportsbook",
        ),
        "league": get_value(
            quote,
            "league",
            "MLB",
        ),
        "market": get_value(
            quote,
            "market",
            "Moneyline",
        ),
        "selection": get_value(
            quote,
            "selection",
        ),
        "moneyline": american_odds,
        "american_odds": american_odds,
        "book_probability": (
            implied_probability
        ),
        "implied_probability": (
            implied_probability
        ),
        "edge_pct": get_value(
            quote,
            "edge_pct",
        ),
        "expected_value_pct": get_value(
            quote,
            "expected_value_pct",
        ),
        "event_id": get_value(
            quote,
            "event_id",
        ),
        "commence_time": get_value(
            quote,
            "commence_time",
        ),
        "last_updated": (
            get_value(
                quote,
                "last_updated",
            )
            or get_value(
                quote,
                "updated_at",
            )
        ),
        "stale": bool(
            get_value(
                quote,
                "stale",
                True,
            )
        ),
        "real_market_loaded": bool(
            get_value(
                quote,
                "real_market_loaded",
                False,
            )
        ),
        "quotes_compared": int(
            get_value(
                quote,
                "quotes_compared",
                1,
            )
            or 0
        ),
    }


def quote_object(
    quote: dict | None,
) -> SimpleNamespace | None:
    """
    SharpScore currently expects quote attributes
    such as quote.american_odds. The best-line engine
    returns dictionaries, so expose the selected quote
    through attribute access without losing metadata.
    """

    if not quote:
        return None

    return SimpleNamespace(
        **quote
    )


def build_quote_lookup() -> dict[
    tuple[str, str, str],
    list[Any],
]:
    try:
        provider = get_odds_provider(
            "the_odds_api"
        )

        quotes = provider.get_moneylines(
            "MLB"
        )
    except Exception as ex:
        print(
            f"MLB odds unavailable: {ex}"
        )
        return {}

    lookup: dict[
        tuple[str, str, str],
        list[Any],
    ] = {}

    for quote in quotes:
        key = (
            clean(
                get_value(
                    quote,
                    "away_team",
                )
            ),
            clean(
                get_value(
                    quote,
                    "home_team",
                )
            ),
            clean(
                get_value(
                    quote,
                    "selection",
                )
            ),
        )

        if not all(key):
            continue

        lookup.setdefault(
            key,
            [],
        ).append(quote)

    return lookup


def quote_for_team(
    quote_lookup: dict[
        tuple[str, str, str],
        list[Any],
    ],
    away: str,
    home: str,
    selection: str,
) -> SimpleNamespace | None:
    key = (
        clean(away),
        clean(home),
        clean(selection),
    )

    candidates = quote_lookup.get(
        key,
        [],
    )

    if not candidates:
        return None

    best_quote = select_best_quote(
        candidates,
        maximum_age_minutes=(
            MAXIMUM_QUOTE_AGE_MINUTES
        ),
        allow_stale=False,
    )

    return quote_object(
        best_quote
    )


def build_mlb_card(
    raw_games: list[dict],
) -> dict:
    quote_lookup = build_quote_lookup()
    games: list[dict] = []

    for raw in raw_games:
        teams = raw.get("teams", {})
        away_blob = teams.get("away", {})
        home_blob = teams.get("home", {})

        away_profile = team_profile(
            away_blob
        )

        home_profile = team_profile(
            home_blob
        )

        away = away_profile.get("name")
        home = home_profile.get("name")

        if not away or not home:
            continue

        away_pitcher = pitcher_from_team(
            away_blob
        )

        home_pitcher = pitcher_from_team(
            home_blob
        )

        away_quote = quote_for_team(
            quote_lookup,
            away,
            home,
            away,
        )

        home_quote = quote_for_team(
            quote_lookup,
            away,
            home,
            home,
        )

        decision = build_sharpscore_decision(
            away,
            home,
            away_profile,
            home_profile,
            away_pitcher,
            home_pitcher,
            away_quote,
            home_quote,
        )

        selected_quote = decision.get(
            "quote"
        )

        game = {
            "sport": "mlb",
            "game_id": raw.get(
                "gamePk"
            ),
            "status": raw.get(
                "status",
                {},
            ).get(
                "detailedState"
            ),
            "commence_time": raw.get(
                "gameDate"
            ),
            "venue": raw.get(
                "venue",
                {},
            ).get("name"),
            "matchup": {
                "away": away,
                "home": home,
            },
            "teams": {
                "away": away_profile,
                "home": home_profile,
            },
            "pitching": {
                "away": away_pitcher,
                "home": home_pitcher,
            },
            "model": decision["model"],
            "odds": quote_to_dict(
                selected_quote
            ),
            "market_edge": decision[
                "market_edge"
            ],
        }

        game["totals_model"] = (
            build_totals_projection(
                game
            )
        )

        games.append(game)

    return {
        "sport": "MLB",
        "version": "0.8 Alpha",
        "generated_at": datetime.now().isoformat(
            timespec="seconds"
        ),
        "games": games,
    }

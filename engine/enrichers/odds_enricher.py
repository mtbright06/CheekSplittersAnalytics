from __future__ import annotations

from collections import defaultdict
from typing import Any

from engine.odds.best_line import (
    enrich_quote,
    select_best_quote,
)
from engine.odds.market_edge import (
    calculate_market_edge,
    market_edge_to_dict,
)
from engine.odds.provider_factory import (
    get_odds_provider,
)
from engine.odds.reference_price import (
    ReferencePriceResolver,
    resolve_reference_quote,
)


DEFAULT_MAXIMUM_QUOTE_AGE_MINUTES = 20

class AttrDict(dict):
    """
    Dictionary that also supports attribute access.

    Example:
        value["moneyline"]
        value.moneyline

    Both return the same value.
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def _clean(value: Any) -> str:
    return " ".join(
        str(value or "")
        .strip()
        .lower()
        .split()
    )


def _get(
    obj: Any,
    key: str,
    default: Any = None,
) -> Any:
    if isinstance(obj, dict):
        return obj.get(
            key,
            default,
        )

    return getattr(
        obj,
        key,
        default,
    )


def _set(
    obj: Any,
    key: str,
    value: Any,
) -> None:
    if (
        key in {"odds", "market_edge"}
        and isinstance(value, dict)
        and not isinstance(value, AttrDict)
    ):
        value = AttrDict(value)

    if isinstance(obj, dict):
        obj[key] = value
        return

    setattr(
        obj,
        key,
        value,
    )


def _normalize_probability(
    value: Any,
) -> float | None:
    try:
        probability = float(value)
    except (TypeError, ValueError):
        return None

    if probability > 1:
        probability /= 100

    if probability < 0 or probability > 1:
        return None

    return probability


def quote_to_odds_dict(
    quote: Any,
    *,
    model_probability: float | None = None,
    maximum_age_minutes: float = (
        DEFAULT_MAXIMUM_QUOTE_AGE_MINUTES
    ),
) -> dict:
    enriched = enrich_quote(
        quote,
        model_probability=model_probability,
        maximum_age_minutes=(
            maximum_age_minutes
        ),
    )

    return {
        "provider": enriched.get(
            "provider"
        ),
        "sportsbook": enriched.get(
            "sportsbook"
        ),
        "league": enriched.get(
            "league"
        ),
        "market": enriched.get(
            "market"
        ),
        "selection": enriched.get(
            "selection"
        ),
        "away_team": enriched.get(
            "away_team"
        ),
        "home_team": enriched.get(
            "home_team"
        ),
        "moneyline": enriched.get(
            "american_odds"
        ),
        "american_odds": enriched.get(
            "american_odds"
        ),
        "book_probability": enriched.get(
            "implied_probability"
        ),
        "implied_probability": enriched.get(
            "implied_probability"
        ),
        "edge_pct": enriched.get(
            "edge_pct"
        ),
        "expected_value_pct": enriched.get(
            "expected_value_pct"
        ),
        "event_id": enriched.get(
            "event_id"
        ),
        "commence_time": enriched.get(
            "commence_time"
        ),
        "last_updated": (
            enriched.get(
                "last_updated"
            )
            or enriched.get(
                "updated_at"
            )
        ),
        "stale": enriched.get(
            "stale",
            True,
        ),
        "real_market_loaded": enriched.get(
            "real_market_loaded",
            False,
        ),
        "quotes_compared": enriched.get(
            "quotes_compared",
            1,
        ),
    }


class OddsEnricher:
    def __init__(
        self,
        league: str,
        *,
        provider_name: str = "the_odds_api",
        maximum_quote_age_minutes: float = (
            DEFAULT_MAXIMUM_QUOTE_AGE_MINUTES
        ),
        allow_stale_quotes: bool = False,
        reference_price_resolver: ReferencePriceResolver | None = None,
    ):
        self.provider = get_odds_provider(
            provider_name
        )

        self.league = (
            league
            or "MLB"
        ).upper()

        self.maximum_quote_age_minutes = (
            maximum_quote_age_minutes
        )

        self.allow_stale_quotes = (
            allow_stale_quotes
        )
        self.reference_price_resolver = reference_price_resolver

        self.quote_lookup: dict[
            tuple[str, str, str],
            list[Any],
        ] = {}

    def load_quotes(self) -> None:
        quotes = self.provider.get_moneylines(
            self.league
        )

        grouped: dict[
            tuple[str, str, str],
            list[Any],
        ] = defaultdict(list)

        for quote in quotes:
            away = _clean(
                _get(
                    quote,
                    "away_team",
                )
            )

            home = _clean(
                _get(
                    quote,
                    "home_team",
                )
            )

            selection = _clean(
                _get(
                    quote,
                    "selection",
                )
            )

            if (
                not away
                or not home
                or not selection
            ):
                continue

            key = (
                away,
                home,
                selection,
            )

            grouped[key].append(
                quote
            )

        self.quote_lookup = dict(
            grouped
        )

    def find_quotes(
        self,
        game: Any,
    ) -> list[Any]:
        matchup = _get(
            game,
            "matchup",
            {},
        )

        model = _get(
            game,
            "model",
            {},
        )

        away = _get(
            matchup,
            "away",
        )

        home = _get(
            matchup,
            "home",
        )

        selection = (
            _get(
                game,
                "play",
            )
            or _get(
                model,
                "play",
            )
            or _get(
                game,
                "selection",
            )
        )

        if (
            not away
            or not home
            or not selection
        ):
            return []

        key = (
            _clean(away),
            _clean(home),
            _clean(selection),
        )

        return self.quote_lookup.get(
            key,
            [],
        )

    def find_quote(
        self,
        game: Any,
        *,
        model_probability: float | None = None,
    ) -> dict | None:
        quotes = self.find_quotes(
            game
        )

        if not quotes:
            return None

        return select_best_quote(
            quotes,
            model_probability=(
                model_probability
            ),
            maximum_age_minutes=(
                self.maximum_quote_age_minutes
            ),
            allow_stale=(
                self.allow_stale_quotes
            ),
        )

    def enrich(
        self,
        games: list[Any],
    ) -> list[Any]:
        self.load_quotes()

        for game in games:
            model = _get(
                game,
                "model",
                {},
            )

            raw_model_probability = (
                _get(
                    game,
                    "model_probability",
                )
                or _get(
                    model,
                    "model_probability",
                )
            )

            model_probability = (
                _normalize_probability(
                    raw_model_probability
                )
            )

            best_quote = self.find_quote(
                game,
                model_probability=(
                    model_probability
                ),
            )

            if best_quote is None:
                _set(
                    game,
                    "odds",
                    {
                        "provider": None,
                        "sportsbook": None,
                        "market": "Moneyline",
                        "selection": (
                            _get(
                                model,
                                "play",
                            )
                            or _get(
                                game,
                                "play",
                            )
                        ),
                        "moneyline": None,
                        "american_odds": None,
                        "book_probability": None,
                        "implied_probability": None,
                        "last_updated": None,
                        "stale": True,
                        "real_market_loaded": False,
                        "quotes_compared": 0,
                        "current_price": None,
                        "current_book": None,
                        "current_captured_at": None,
                        "reference_price": None,
                        "reference_implied_probability": None,
                        "reference_book": None,
                        "reference_captured_at": None,
                        "reference_minutes_before_start": None,
                        "reference_status": "REFERENCE_UNAVAILABLE_NO_QUOTE",
                        "reference_policy_version": None,
                    },
                )

                _set(
                    game,
                    "market_edge",
                    {},
                )

                continue

            odds_dict = quote_to_odds_dict(
                best_quote,
                model_probability=(
                    model_probability
                ),
                maximum_age_minutes=(
                    self.maximum_quote_age_minutes
                ),
            )

            odds_dict[
                "quotes_compared"
            ] = best_quote.get(
                "quotes_compared",
                odds_dict.get(
                    "quotes_compared",
                    1,
                ),
            )

            reference = resolve_reference_quote(
                best_quote,
                league=self.league,
                resolver=self.reference_price_resolver,
            )
            odds_dict.update(reference.reference_fields)

            _set(
                game,
                "odds",
                odds_dict,
            )

            if model_probability is None:
                _set(
                    game,
                    "market_edge",
                    {},
                )
                continue

            if reference.reference_quote is None:
                _set(
                    game,
                    "market_edge",
                    {
                        **reference.reference_fields,
                        "edge": None,
                        "real_market_loaded": False,
                    },
                )
                continue

            edge = calculate_market_edge(
                raw_model_probability,
                AttrDict(reference.reference_quote),
            )

            edge_dict = market_edge_to_dict(
                edge
            )

            edge_dict.update(
                {
                    "best_sportsbook": (
                        best_quote.get(
                            "sportsbook"
                        )
                    ),
                    "best_american_odds": (
                        best_quote.get(
                            "american_odds"
                        )
                    ),
                    "quotes_compared": (
                        best_quote.get(
                            "quotes_compared",
                            1,
                        )
                    ),
                    "quote_stale": (
                        best_quote.get(
                            "stale",
                            False,
                        )
                    ),
                    "real_market_loaded": True,
                    **reference.reference_fields,
                }
            )

            _set(
                game,
                "market_edge",
                edge_dict,
            )

        return games

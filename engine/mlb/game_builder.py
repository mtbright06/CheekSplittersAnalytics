from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, Callable

from engine.core import (
    ELIGIBLE_PREGAME,
    PregameEligibility,
    PregameEligibilityReason,
    evaluate_pregame_eligibility,
)
from engine.mlb.offense import (
    fetch_team_batting_stats,
)
from engine.mlb.bullpen.provider import (
    fetch_bullpen_profile,
)
from engine.mlb.pitchers import (
    PitcherGameLogCache,
    fetch_pitcher_stats,
)
from engine.mlb.team_mapping import (
    MLB_TEAM_ABBR,
)
from engine.mlb.totals import (
    build_totals_projection,
    build_totals_league_baselines,
)
from engine.model.sharpscore import (
    build_sharpscore_decision,
)
from engine.odds.best_line import (
    select_best_quote,
)
from engine.odds.quote_utils import (
    parse_timestamp as parse_quote_timestamp,
)
from engine.odds.implied_probability import (
    american_to_implied_probability,
)
from engine.odds.provider_factory import (
    get_odds_provider,
)
from engine.odds.reference_price import (
    ReferencePriceResolver,
    resolve_reference_quote,
)


MAXIMUM_QUOTE_AGE_MINUTES = 20


PREFERRED_TOTAL_SPORTSBOOKS = [
    "FanDuel",
    "DraftKings",
    "BetMGM",
    "Caesars",
    "Fanatics",
    "BetRivers",
    "ESPN BET",
]


class TeamProfileCache:
    """Build-local reuse for deterministic MLB team provider data."""

    def __init__(self) -> None:
        self._entries: dict[
            tuple[str, int],
            dict[str, Any],
        ] = {}

    def get_or_fetch(
        self,
        team_id: int,
        *,
        fetcher: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        key = (
            "team_batting_and_bullpen_context",
            int(team_id),
        )

        if key not in self._entries:
            self._entries[key] = fetcher()

        # Each game receives independent profile data even when the provider
        # response was shared within this build.
        return deepcopy(self._entries[key])


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
        return obj.get(
            key,
            default,
        )

    return getattr(
        obj,
        key,
        default,
    )


def to_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None


def to_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    try:
        return int(
            round(float(value))
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def parse_timestamp(
    value: Any,
) -> float:
    parsed = parse_quote_timestamp(value)
    return parsed.timestamp() if parsed else 0.0


def sportsbook_priority(
    sportsbook: Any,
) -> int:
    name = clean(
        sportsbook
    )

    for index, preferred in enumerate(
        PREFERRED_TOTAL_SPORTSBOOKS
    ):
        if name == clean(preferred):
            return index

    return len(
        PREFERRED_TOTAL_SPORTSBOOKS
    ) + 100


def pitcher_from_team(
    team_blob: dict,
    *,
    game_date: Any = None,
    game_log_cache: PitcherGameLogCache | None = None,
) -> dict:
    pitcher = (
        team_blob.get(
            "probablePitcher"
        )
        or {}
    )

    pitcher_id = pitcher.get("id")

    stats = fetch_pitcher_stats(
        pitcher_id,
        as_of=game_date,
        game_log_cache=game_log_cache,
    )

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
        "starts": stats.get("starts"),
        "so": stats.get("so"),
        "bb": stats.get("bb"),
        "hits": stats.get("hits"),
        "hbp": stats.get("hbp"),
        "hr_allowed": stats.get(
            "hr_allowed"
        ),
        "batters_faced": stats.get(
            "batters_faced"
        ),
        "k_rate": stats.get("k_rate"),
        "bb_rate": stats.get("bb_rate"),
        "hr9": stats.get("hr9"),
        "h9": stats.get("h9"),
        "k_bb_pct": stats.get(
            "k_bb_pct"
        ),
        "strike_pct": stats.get(
            "strike_pct"
        ),
        "pitches_per_inning": stats.get(
            "pitches_per_inning"
        ),
        "ground_air_ratio": stats.get(
            "ground_air_ratio"
        ),
        "opponent_avg": stats.get(
            "opponent_avg"
        ),
        "previous_start_date": stats.get(
            "previous_start_date"
        ),
        "previous_appearance_date": stats.get(
            "previous_appearance_date"
        ),
        "days_rest": stats.get("days_rest"),
        "previous_start_ip": stats.get(
            "previous_start_ip"
        ),
        "previous_start_pitch_count": stats.get(
            "previous_start_pitch_count"
        ),
        "last_two_starts_ip": stats.get(
            "last_two_starts_ip"
        ),
        "last_two_starts_pitch_count": stats.get(
            "last_two_starts_pitch_count"
        ),
        "last14_start_ip": stats.get(
            "last14_start_ip"
        ),
        "average_start_ip": stats.get(
            "average_start_ip"
        ),
        "role_context": stats.get(
            "role_context"
        ),
        "data_source": stats.get(
            "data_source"
        ),
    }


def team_profile(
    team_blob: dict,
    *,
    game_log_cache: PitcherGameLogCache | None = None,
    team_profile_cache: TeamProfileCache | None = None,
) -> dict:
    team = team_blob.get(
        "team",
        {},
    )

    name = team.get("name")
    team_id = team.get("id")

    def fetch_context() -> dict[str, Any]:
        return {
            "offense": fetch_team_batting_stats(
                team_id
            ),
            "bullpen": fetch_bullpen_profile(
                team_id,
                name,
                game_log_cache=game_log_cache,
            ),
        }

    context = (
        team_profile_cache.get_or_fetch(
            team_id,
            fetcher=fetch_context,
        )
        if team_profile_cache is not None and team_id
        else fetch_context()
    )

    return {
        "id": team_id,
        "name": name,
        "abbr": MLB_TEAM_ABBR.get(
            name
        ),
        "record": None,
        "form": None,
        "offense": context["offense"],
        "bullpen": context["bullpen"],
    }


def build_moneyline_league_baselines(
    profiles: list[dict[str, Any]],
) -> dict[str, Any]:
    unique_profiles = {
        profile.get("id"): profile
        for profile in profiles
        if profile.get("id")
    }

    offense = build_offense_league_baselines(
        [
            profile.get("offense", {})
            for profile in unique_profiles.values()
        ]
    )
    bullpen = build_bullpen_league_baselines(
        [
            profile.get("bullpen", {})
            for profile in unique_profiles.values()
        ]
    )

    baselines: dict[str, Any] = {
        "source": "current_build_team_season_profiles",
    }

    if offense:
        baselines["offense"] = offense

    if bullpen:
        baselines["bullpen"] = bullpen

    return baselines


def build_offense_league_baselines(
    offenses: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [
        offense
        for offense in offenses
        if offense.get("source_quality") == "COMPLETE"
    ]

    baselines = {
        "runs_per_game": average_metric(
            eligible,
            "runs_per_game",
        ),
        "ops": average_metric(
            eligible,
            "ops",
        ),
        "iso": average_metric(
            eligible,
            "iso",
        ),
        "hr_per_game": average_metric(
            eligible,
            "hr_per_game",
        ),
    }

    discipline_values = [
        offense.get("bb_rate") - offense.get("k_rate")
        for offense in eligible
        if offense.get("bb_rate") is not None
        and offense.get("k_rate") is not None
    ]
    if discipline_values:
        baselines["bb_minus_k_rate"] = round(
            sum(discipline_values) / len(discipline_values),
            3,
        )

    return with_baseline_metadata(
        baselines,
        source="mlb_statsapi_team_hitting_season",
        sample_size=len(eligible),
    )


def build_bullpen_league_baselines(
    bullpens: list[dict[str, Any]],
) -> dict[str, Any]:
    eligible = [
        bullpen
        for bullpen in bullpens
        if bullpen.get("source_quality") == "COMPLETE"
    ]

    baselines = {
        "era": average_metric(
            eligible,
            "season_era",
        ),
        "whip": average_metric(
            eligible,
            "season_whip",
        ),
    }

    return with_baseline_metadata(
        baselines,
        source="active_roster_reliever_game_logs",
        sample_size=len(eligible),
    )


def with_baseline_metadata(
    baselines: dict[str, Any],
    *,
    source: str,
    sample_size: int,
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in baselines.items()
        if value is not None
    }

    if sample_size < 10 or not values:
        return {}

    values["source"] = source
    values["sample_size"] = sample_size
    return values


def average_metric(
    rows: list[dict[str, Any]],
    key: str,
) -> float | None:
    values = [
        float(row[key])
        for row in rows
        if row.get(key) is not None
    ]

    if not values:
        return None

    return round(
        sum(values) / len(values),
        3,
    )


def unavailable_total_dict() -> dict:
    return {
        "line": None,
        "sportsbook": "Unavailable",
        "over_odds": None,
        "under_odds": None,
        "provider": None,
        "event_id": None,
        "commence_time": None,
        "last_updated": None,
        "available": False,
        "stale": True,
        "real_market_loaded": False,
        "quotes_compared": 0,
    }


def ineligible_total_dict(
    eligibility: PregameEligibility,
) -> dict:
    data = unavailable_total_dict()
    data.update(
        {
            "freshness_reason": eligibility.reason.value,
            "market_status": eligibility.reason.value,
            "pregame_eligible": eligibility.eligible,
            "pregame_eligibility_reason": eligibility.reason.value,
        }
    )
    return data


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
        "quote_updated_at_utc": None,
        "quote_age_minutes": None,
        "freshness_status": "NO_SELECTED_QUOTE",
        "freshness_reason": "No fresh production-eligible quote was selected.",
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
        "totals": unavailable_total_dict(),
    }


def ineligible_quote_dict(
    eligibility: PregameEligibility,
) -> dict:
    data = unavailable_quote_dict()
    data.update(
        {
            "freshness_status": "UNAVAILABLE",
            "freshness_reason": eligibility.reason.value,
            "market_status": eligibility.reason.value,
            "pregame_eligible": eligibility.eligible,
            "pregame_eligibility_reason": eligibility.reason.value,
            "totals": ineligible_total_dict(eligibility),
        }
    )
    return data


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
        "quote_updated_at_utc": get_value(
            quote,
            "quote_updated_at_utc",
        ),
        "quote_age_minutes": get_value(
            quote,
            "quote_age_minutes",
        ),
        "freshness_status": get_value(
            quote,
            "freshness_status",
        ),
        "freshness_reason": get_value(
            quote,
            "freshness_reason",
        ),
        "is_live": bool(
            get_value(
                quote,
                "is_live",
                False,
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
        "totals": unavailable_total_dict(),
    }


def quote_object(
    quote: dict | None,
) -> SimpleNamespace | None:
    """
    SharpScore expects quote attributes such as
    quote.american_odds. The best-line engine returns
    dictionaries, so expose the selected quote through
    attribute access without losing metadata.
    """

    if not quote:
        return None

    return SimpleNamespace(
        **quote
    )


def fetch_market_quotes() -> tuple[
    list[Any],
    list[Any],
]:
    """
    Fetch moneylines and totals.

    The preferred provider implementation retrieves both
    markets in one API request. The fallback keeps this
    builder compatible with providers that expose only
    separate methods.
    """

    try:
        provider = get_odds_provider(
            "the_odds_api"
        )

        combined_method = getattr(
            provider,
            "get_moneylines_and_totals",
            None,
        )

        if callable(combined_method):
            markets = combined_method(
                "MLB"
            )

            return (
                markets.get(
                    "moneylines",
                    [],
                ),
                markets.get(
                    "totals",
                    [],
                ),
            )

        moneylines = provider.get_moneylines(
            "MLB"
        )

        totals_method = getattr(
            provider,
            "get_totals",
            None,
        )

        totals = (
            totals_method("MLB")
            if callable(totals_method)
            else []
        )

        return (
            moneylines,
            totals,
        )

    except Exception as ex:
        print(
            f"MLB odds unavailable: {ex}"
        )

        return (
            [],
            [],
        )


def build_moneyline_lookup(
    quotes: list[Any],
) -> dict[
    tuple[str, str, str],
    list[Any],
]:
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
        ).append(
            quote
        )

    return lookup


def build_total_lookup(
    quotes: list[Any],
) -> dict[
    tuple[str, str],
    list[dict],
]:
    """
    Pair OVER and UNDER quotes by:

        matchup
        sportsbook
        total line

    This prevents combining FanDuel OVER 8.5 with
    DraftKings UNDER 8.0.
    """

    paired: dict[
        tuple[
            str,
            str,
            str,
            float,
        ],
        dict,
    ] = {}

    for quote in quotes:
        away = clean(
            get_value(
                quote,
                "away_team",
            )
        )

        home = clean(
            get_value(
                quote,
                "home_team",
            )
        )

        sportsbook = get_value(
            quote,
            "sportsbook",
        )

        sportsbook_key = clean(
            sportsbook
        )

        line = to_float(
            get_value(
                quote,
                "line",
            )
        )

        selection = clean(
            get_value(
                quote,
                "selection",
            )
        ).upper()

        if (
            not away
            or not home
            or not sportsbook_key
            or line is None
            or selection
            not in {
                "OVER",
                "UNDER",
            }
        ):
            continue

        pair_key = (
            away,
            home,
            sportsbook_key,
            line,
        )

        candidate = paired.setdefault(
            pair_key,
            {
                "line": line,
                "sportsbook": sportsbook,
                "over_odds": None,
                "under_odds": None,
                "provider": get_value(
                    quote,
                    "provider",
                ),
                "event_id": get_value(
                    quote,
                    "event_id",
                ),
                "commence_time": get_value(
                    quote,
                    "commence_time",
                ),
                "last_updated": get_value(
                    quote,
                    "last_updated",
                ),
                "is_live": bool(
                    get_value(
                        quote,
                        "is_live",
                        False,
                    )
                ),
                "available": True,
                "stale": False,
                "real_market_loaded": True,
                "quotes_compared": 0,
            },
        )

        odds = to_int(
            get_value(
                quote,
                "american_odds",
            )
        )

        if selection == "OVER":
            candidate[
                "over_odds"
            ] = odds
        else:
            candidate[
                "under_odds"
            ] = odds

        quote_updated = get_value(
            quote,
            "last_updated",
        )

        if (
            parse_timestamp(
                quote_updated
            )
            > parse_timestamp(
                candidate.get(
                    "last_updated"
                )
            )
        ):
            candidate[
                "last_updated"
            ] = quote_updated

    lookup: dict[
        tuple[str, str],
        list[dict],
    ] = {}

    for (
        away,
        home,
        _sportsbook,
        _line,
    ), candidate in paired.items():
        matchup_key = (
            away,
            home,
        )

        lookup.setdefault(
            matchup_key,
            [],
        ).append(
            candidate
        )

    for candidates in lookup.values():
        quote_count = len(
            candidates
        )

        for candidate in candidates:
            candidate[
                "quotes_compared"
            ] = quote_count

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

    candidates = [
        candidate
        for candidate in candidates
        if not bool(
            get_value(
                candidate,
                "is_live",
                False,
            )
        )
    ]

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


def log_moneyline_quote_diagnostic(
    away: str,
    home: str,
    selection: str,
    quote: Any,
    *,
    artifact_generated_at: str,
) -> None:
    data = quote_to_dict(quote)
    print(
        "MLB quote diagnostic | "
        f"{away} @ {home} | {selection} | "
        f"book={data.get('sportsbook')} | odds={data.get('american_odds')} | "
        f"implied_probability={data.get('implied_probability')} | "
        f"updated_at_utc={data.get('quote_updated_at_utc')} | "
        f"artifact_generated_at_utc={artifact_generated_at} | "
        f"age_minutes={data.get('quote_age_minutes')} | "
        f"freshness={data.get('freshness_status')} | "
        f"reason={data.get('freshness_reason')} | "
        "quote_identity="
        f"{data.get('event_id')}:{data.get('selection')}:"
        f"{data.get('sportsbook')}:{data.get('american_odds')}"
    )


def total_price_balance(
    candidate: dict,
) -> float:
    """
    Prefer the sportsbook's primary total by selecting
    the OVER/UNDER pair whose implied probabilities are
    closest together.
    """

    over = to_int(
        candidate.get(
            "over_odds"
        )
    )

    under = to_int(
        candidate.get(
            "under_odds"
        )
    )

    if over is None or under is None:
        return float("inf")

    over_prob = (
        american_to_implied_probability(
            over
        )
    )

    under_prob = (
        american_to_implied_probability(
            under
        )
    )

    return abs(
        over_prob - under_prob
    )


def total_market_vig(
    candidate: dict,
) -> float:
    """
    Secondary tiebreaker that prefers the lower-vig
    market when totals are similarly balanced.
    """

    over = to_int(
        candidate.get(
            "over_odds"
        )
    )

    under = to_int(
        candidate.get(
            "under_odds"
        )
    )

    if over is None or under is None:
        return float("inf")

    over_prob = (
        american_to_implied_probability(
            over
        )
    )

    under_prob = (
        american_to_implied_probability(
            under
        )
    )

    return abs(
        (
            over_prob
            + under_prob
        )
        - 1.0
    )


def total_for_game(
    total_lookup: dict[
        tuple[str, str],
        list[dict],
    ],
    away: str,
    home: str,
    *,
    eligibility: PregameEligibility = ELIGIBLE_PREGAME,
) -> dict:
    if not eligibility.eligible:
        return ineligible_total_dict(
            eligibility
        )

    key = (
        clean(away),
        clean(home),
    )

    candidates = total_lookup.get(
        key,
        [],
    )

    if not candidates:
        return unavailable_total_dict()

    candidates = [
        candidate
        for candidate in candidates
        if not candidate.get("is_live")
    ]

    if not candidates:
        return ineligible_total_dict(
            PregameEligibility(
                False,
                PregameEligibilityReason.LIVE_MARKET,
            )
        )

    complete_pairs = [
        candidate
        for candidate in candidates
        if (
            candidate.get(
                "line"
            )
            is not None
            and candidate.get(
                "over_odds"
            )
            is not None
            and candidate.get(
                "under_odds"
            )
            is not None
        )
    ]

    usable = (
        complete_pairs
        or candidates
    )

    usable.sort(
        key=lambda candidate: (
            sportsbook_priority(
                candidate.get(
                    "sportsbook"
                )
            ),
            total_price_balance(
                candidate
            ),
            total_market_vig(
                candidate
            ),
            -parse_timestamp(
                candidate.get(
                    "last_updated"
                )
            ),
        )
    )

    selected = dict(
        usable[0]
    )

    selected[
        "available"
    ] = (
        selected.get("line")
        is not None
    )

    selected[
        "real_market_loaded"
    ] = bool(
        selected.get(
            "available"
        )
    )

    selected[
        "pregame_eligible"
    ] = eligibility.eligible

    selected[
        "pregame_eligibility_reason"
    ] = eligibility.reason.value

    return selected


def build_mlb_card(
    raw_games: list[dict],
    *,
    reference_price_resolver: ReferencePriceResolver | None = None,
) -> dict:
    (
        moneyline_quotes,
        total_quotes,
    ) = fetch_market_quotes()

    moneyline_lookup = (
        build_moneyline_lookup(
            moneyline_quotes
        )
    )

    total_lookup = build_total_lookup(
        total_quotes
    )

    print(
        "MLB moneyline quotes loaded:",
        len(moneyline_quotes),
    )

    print(
        "MLB total quotes loaded:",
        len(total_quotes),
    )

    print(
        "MLB total matchups loaded:",
        len(total_lookup),
    )

    games: list[dict] = []
    game_log_cache = PitcherGameLogCache()
    team_profile_cache = TeamProfileCache()
    profile_contexts: dict[int, dict[str, Any]] = {}
    league_baselines: dict[str, Any] = {}

    for index, raw in enumerate(raw_games):
        teams = raw.get(
            "teams",
            {},
        )

        away_blob = teams.get(
            "away",
            {},
        )

        home_blob = teams.get(
            "home",
            {},
        )

        away_profile = team_profile(
            away_blob,
            game_log_cache=game_log_cache,
            team_profile_cache=team_profile_cache,
        )

        home_profile = team_profile(
            home_blob,
            game_log_cache=game_log_cache,
            team_profile_cache=team_profile_cache,
        )
        scheduled_start_at = raw.get(
            "gameDate"
        )
        away_pitcher = pitcher_from_team(
            away_blob,
            game_date=scheduled_start_at,
            game_log_cache=game_log_cache,
        )
        home_pitcher = pitcher_from_team(
            home_blob,
            game_date=scheduled_start_at,
            game_log_cache=game_log_cache,
        )

        profile_contexts[index] = {
            "away": away_profile,
            "home": home_profile,
            "away_pitcher": away_pitcher,
            "home_pitcher": home_pitcher,
        }

    league_baselines = build_moneyline_league_baselines(
        [
            profile
            for context in profile_contexts.values()
            for profile in (
                context["away"],
                context["home"],
            )
        ]
    )
    totals_league_baselines = build_totals_league_baselines(
        team_profiles=[
            profile
            for context in profile_contexts.values()
            for profile in (
                context["away"],
                context["home"],
            )
        ],
        starter_profiles=[
            pitcher
            for context in profile_contexts.values()
            for pitcher in (
                context["away_pitcher"],
                context["home_pitcher"],
            )
        ],
    )

    for index, raw in enumerate(raw_games):
        teams = raw.get(
            "teams",
            {},
        )

        away_blob = teams.get(
            "away",
            {},
        )

        home_blob = teams.get(
            "home",
            {},
        )

        context = profile_contexts.get(
            index,
            {},
        )
        away_profile = context.get("away") or team_profile(
            away_blob,
            game_log_cache=game_log_cache,
            team_profile_cache=team_profile_cache,
        )

        home_profile = context.get("home") or team_profile(
            home_blob,
            game_log_cache=game_log_cache,
            team_profile_cache=team_profile_cache,
        )

        away = away_profile.get(
            "name"
        )

        home = home_profile.get(
            "name"
        )

        if not away or not home:
            continue

        status_payload = raw.get(
            "status",
            {},
        )

        scheduled_start_at = raw.get(
            "gameDate"
        )

        pregame_eligibility = evaluate_pregame_eligibility(
            game_status=status_payload,
            scheduled_start=scheduled_start_at,
        )

        away_pitcher = context.get("away_pitcher") or pitcher_from_team(
            away_blob,
            game_date=scheduled_start_at,
            game_log_cache=game_log_cache,
        )

        home_pitcher = context.get("home_pitcher") or pitcher_from_team(
            home_blob,
            game_date=scheduled_start_at,
            game_log_cache=game_log_cache,
        )

        if pregame_eligibility.eligible:
            away_quote = quote_for_team(
                moneyline_lookup,
                away,
                home,
                away,
            )

            home_quote = quote_for_team(
                moneyline_lookup,
                away,
                home,
                home,
            )
        else:
            away_quote = None
            home_quote = None

        away_reference = resolve_reference_quote(
            away_quote,
            league="MLB",
            resolver=reference_price_resolver,
        )
        home_reference = resolve_reference_quote(
            home_quote,
            league="MLB",
            resolver=reference_price_resolver,
        )

        decision = (
            build_sharpscore_decision(
                away,
                home,
                away_profile,
                home_profile,
                away_pitcher,
                home_pitcher,
                quote_object(away_reference.reference_quote),
                quote_object(home_reference.reference_quote),
                league_baselines=league_baselines,
            )
        )

        selected_is_away = (
            decision.get("model", {}).get("play") == away
        )
        selected_current = (
            away_reference
            if selected_is_away
            else home_reference
        )

        if pregame_eligibility.eligible:
            odds = quote_to_dict(
                quote_object(selected_current.current_quote)
            )
            odds.update(selected_current.reference_fields)
        else:
            odds = ineligible_quote_dict(
                pregame_eligibility
            )

        odds[
            "totals"
        ] = total_for_game(
            total_lookup,
            away,
            home,
            eligibility=pregame_eligibility,
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
            "scheduled_start_at": scheduled_start_at,
            "pregame_eligible": pregame_eligibility.eligible,
            "pregame_eligibility_reason": pregame_eligibility.reason.value,
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
            "bullpen": {
                "away": away_profile.get("bullpen", {}),
                "home": home_profile.get("bullpen", {}),
            },
            "model": decision[
                "model"
            ],
            "odds": odds,
            "market_edge": {
                **decision["market_edge"],
                **selected_current.reference_fields,
            },
        }

        game[
            "totals_model"
        ] = build_totals_projection(
            game,
            league_baselines=totals_league_baselines,
        )

        games.append(
            game
        )

    generated_at = datetime.now(UTC).isoformat(
        timespec="seconds"
    )

    for game in games:
        matchup = game.get("matchup", {})
        model = game.get("model", {})
        log_moneyline_quote_diagnostic(
            matchup.get("away", "Away"),
            matchup.get("home", "Home"),
            model.get("play", "Unknown"),
            game.get("odds"),
            artifact_generated_at=generated_at,
        )

    return {
        "sport": "MLB",
        "version": "0.9 Alpha",
        "generated_at": generated_at,
        "games": games,
    }

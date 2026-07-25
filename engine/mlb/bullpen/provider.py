from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import requests

from engine.mlb.bullpen.bullpen_data import BullpenSnapshot
from engine.mlb.pitchers import (
    PitcherGameLogCache,
    fetch_pitcher_game_log,
)


BASE_URL = "https://statsapi.mlb.com/api/v1"
RELIEVER_POSITIONS = {"RP", "CP"}


def fetch_bullpen_profile(
    team_id: int | None,
    team_name: str | None,
    *,
    as_of: date | None = None,
    game_log_cache: PitcherGameLogCache | None = None,
) -> dict[str, Any]:
    """Return a normalized active-roster bullpen profile from MLB data."""
    if not team_id:
        return unavailable_bullpen_profile(team_name)

    roster = fetch_active_pitcher_roster(team_id)

    if roster is None:
        return unavailable_bullpen_profile(team_name)

    reference_date = as_of or date.today()
    relief_appearances: list[dict[str, Any]] = []
    evidence_ledger: list[dict[str, Any]] = []
    reliever_count = 0
    failed_pitchers = 0

    for pitcher in roster:
        appearances = fetch_pitcher_game_log(
            pitcher["player_id"],
            game_log_cache=game_log_cache,
        )

        if appearances is None:
            failed_pitchers += 1
            evidence_ledger.append(
                unavailable_pitcher_evidence(
                    pitcher,
                )
            )
            continue

        reliever_appearances = classify_reliever_appearances(
            pitcher,
            appearances,
        )
        evidence_ledger.append(
            pitcher_evidence(
                pitcher,
                appearances,
                reliever_appearances,
                as_of=reference_date,
            )
        )

        if reliever_appearances:
            reliever_count += 1
            relief_appearances.extend(reliever_appearances)

    if not relief_appearances:
        return unavailable_bullpen_profile(
            team_name,
            source_quality=(
                "PARTIAL" if roster else "UNAVAILABLE"
            ),
            source_detail="no_active_reliever_appearances",
            evidence_ledger=evidence_ledger,
        )

    snapshot = build_bullpen_snapshot(
        team_name=team_name,
        appearances=relief_appearances,
        as_of=reference_date,
    )

    source_quality = (
        "COMPLETE" if failed_pitchers == 0 else "PARTIAL"
    )

    return serialize_bullpen_snapshot(
        snapshot,
        reliever_count=reliever_count,
        source_quality=source_quality,
        source_detail="active_roster_game_logs",
        evidence_ledger=evidence_ledger,
    )


def fetch_active_pitcher_roster(
    team_id: int,
) -> list[dict[str, Any]] | None:
    url = f"{BASE_URL}/teams/{team_id}/roster"

    try:
        response = requests.get(
            url,
            params={"rosterType": "active"},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    pitchers = []

    for item in data.get("roster", []):
        person = item.get("person", {})
        position = item.get("position", {})

        if position.get("type") != "Pitcher":
            continue

        player_id = person.get("id")

        if not player_id:
            continue

        pitchers.append(
            {
                "player_id": player_id,
                "player_name": person.get("fullName"),
                "position": position.get("abbreviation"),
            }
        )

    return pitchers


def classify_reliever_appearances(
    pitcher: dict[str, Any],
    appearances: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep relief outings while excluding current starters and openers."""
    relief_appearances = [
        appearance
        for appearance in appearances
        if to_int(appearance.get("stat", {}).get("gamesStarted"))
        in (None, 0)
    ]

    if pitcher.get("position") in RELIEVER_POSITIONS:
        return relief_appearances

    season_starts = sum(
        to_int(appearance.get("stat", {}).get("gamesStarted")) or 0
        for appearance in appearances
    )

    return relief_appearances if season_starts == 0 else []


def pitcher_evidence(
    pitcher: dict[str, Any],
    appearances: list[dict[str, Any]],
    reliever_appearances: list[dict[str, Any]],
    *,
    as_of: date,
) -> dict[str, Any]:
    """Serialize existing pitcher facts without assigning a bullpen role."""
    if not appearances:
        return empty_pitcher_evidence(pitcher)

    observed_relief_appearances = [
        appearance
        for appearance in appearances
        if to_int(appearance.get("stat", {}).get("gamesStarted"))
        in (None, 0)
    ]
    workload = observed_relief_workload(
        observed_relief_appearances,
        as_of=as_of,
        game_log_empty=not appearances,
    )
    season_starts = sum(
        to_int(appearance.get("stat", {}).get("gamesStarted")) or 0
        for appearance in appearances
    )
    last3_start = as_of - timedelta(days=2)
    recent_appearances = [
        appearance
        for appearance in reliever_appearances
        if appearance_date(appearance)
        and last3_start <= appearance_date(appearance) <= as_of
    ]
    appearance_dates = [
        appearance_date(appearance)
        for appearance in reliever_appearances
        if appearance_date(appearance)
    ]
    included = bool(reliever_appearances)

    return {
        "pitcher_id": pitcher.get("player_id"),
        "pitcher_name": pitcher.get("player_name"),
        "roster_position": pitcher.get("position"),
        "season_starts": season_starts,
        # `relief_appearances` retains its diagnostic meaning as all observed
        # non-start outings, regardless of the existing aggregation decision.
        "relief_appearances": len(observed_relief_appearances),
        "observed_relief_appearances": len(
            observed_relief_appearances
        ),
        "included_relief_appearances": len(
            reliever_appearances
        ),
        "last_appearance_date": (
            max(appearance_dates).isoformat()
            if appearance_dates
            else None
        ),
        "appearances_last3": len(recent_appearances),
        "innings_last3": round(
            sum(
                extract_outs(
                    appearance.get("stat", {})
                )
                for appearance in recent_appearances
            ) / 3,
            1,
        ),
        "observed_last_appearance_date": workload[
            "last_appearance_date"
        ],
        "observed_appearances_last3": workload[
            "appearances_last3"
        ],
        "observed_innings_last3": workload["innings_last3"],
        "appearances_last5": workload["appearances_last5"],
        "innings_last5": workload["innings_last5"],
        "multi_inning_appearances_last5": workload[
            "multi_inning_appearances_last5"
        ],
        "days_since_last_appearance": workload[
            "days_since_last_appearance"
        ],
        "appeared_on_consecutive_days": workload[
            "appeared_on_consecutive_days"
        ],
        "consecutive_days_used": workload[
            "consecutive_days_used"
        ],
        "limited_history": workload["limited_history"],
        "inclusion_status": (
            "INCLUDED" if included else "EXCLUDED"
        ),
        "exclusion_reason": (
            None
            if included
            else exclusion_reason(
                pitcher,
                appearances,
                season_starts,
            )
        ),
        "source_quality": "COMPLETE",
        "game_log_status": (
            "AVAILABLE" if appearances else "EMPTY"
        ),
    }


def unavailable_pitcher_evidence(
    pitcher: dict[str, Any],
) -> dict[str, Any]:
    return {
        "pitcher_id": pitcher.get("player_id"),
        "pitcher_name": pitcher.get("player_name"),
        "roster_position": pitcher.get("position"),
        "season_starts": None,
        "relief_appearances": None,
        "observed_relief_appearances": None,
        "included_relief_appearances": None,
        "last_appearance_date": None,
        "appearances_last3": None,
        "innings_last3": None,
        "observed_last_appearance_date": None,
        "observed_appearances_last3": None,
        "observed_innings_last3": None,
        "appearances_last5": None,
        "innings_last5": None,
        "multi_inning_appearances_last5": None,
        "days_since_last_appearance": None,
        "appeared_on_consecutive_days": None,
        "consecutive_days_used": None,
        "limited_history": None,
        "inclusion_status": "EXCLUDED",
        "exclusion_reason": "game_log_unavailable",
        "source_quality": "UNAVAILABLE",
        "game_log_status": "FAILED",
    }


def empty_pitcher_evidence(
    pitcher: dict[str, Any],
) -> dict[str, Any]:
    """Keep successful-but-empty game logs distinct from zero workload."""
    return {
        "pitcher_id": pitcher.get("player_id"),
        "pitcher_name": pitcher.get("player_name"),
        "roster_position": pitcher.get("position"),
        "season_starts": None,
        "relief_appearances": None,
        "observed_relief_appearances": None,
        "included_relief_appearances": None,
        "last_appearance_date": None,
        "appearances_last3": None,
        "innings_last3": None,
        "observed_last_appearance_date": None,
        "observed_appearances_last3": None,
        "observed_innings_last3": None,
        "appearances_last5": None,
        "innings_last5": None,
        "multi_inning_appearances_last5": None,
        "days_since_last_appearance": None,
        "appeared_on_consecutive_days": None,
        "consecutive_days_used": None,
        "limited_history": True,
        "inclusion_status": "EXCLUDED",
        "exclusion_reason": "no_game_log_appearances",
        "source_quality": "COMPLETE",
        "game_log_status": "EMPTY",
    }


def exclusion_reason(
    pitcher: dict[str, Any],
    appearances: list[dict[str, Any]],
    season_starts: int,
) -> str:
    if not appearances:
        return "no_game_log_appearances"

    if (
        pitcher.get("position") not in RELIEVER_POSITIONS
        and season_starts > 0
    ):
        return "non_reliever_with_season_starts"

    return "no_non_starting_appearances"


def observed_relief_workload(
    appearances: list[dict[str, Any]],
    *,
    as_of: date,
    game_log_empty: bool,
) -> dict[str, Any]:
    """Return factual recent workload for observed non-start outings only."""
    if game_log_empty:
        return {
            "last_appearance_date": None,
            "appearances_last3": None,
            "innings_last3": None,
            "appearances_last5": None,
            "innings_last5": None,
            "multi_inning_appearances_last5": None,
            "days_since_last_appearance": None,
            "appeared_on_consecutive_days": None,
            "consecutive_days_used": None,
            "limited_history": True,
        }

    dated_appearances = [
        appearance
        for appearance in appearances
        if (
            (appearance_day := appearance_date(appearance))
            is not None
            and appearance_day <= as_of
        )
    ]
    last3_start = as_of - timedelta(days=2)
    last5_start = as_of - timedelta(days=4)
    last3 = [
        appearance
        for appearance in dated_appearances
        if appearance_date(appearance) >= last3_start
    ]
    last5 = [
        appearance
        for appearance in dated_appearances
        if appearance_date(appearance) >= last5_start
    ]
    dates_used = {
        appearance_date(appearance)
        for appearance in dated_appearances
    }
    last_appearance = max(dates_used) if dates_used else None
    consecutive_days_used = 0

    if last_appearance is not None:
        streak_day = last_appearance
        while streak_day in dates_used:
            consecutive_days_used += 1
            streak_day -= timedelta(days=1)

    return {
        "last_appearance_date": (
            last_appearance.isoformat()
            if last_appearance is not None
            else None
        ),
        "appearances_last3": len(last3),
        "innings_last3": innings_from_appearances(last3),
        "appearances_last5": len(last5),
        "innings_last5": innings_from_appearances(last5),
        "multi_inning_appearances_last5": sum(
            extract_outs(appearance.get("stat", {})) >= 6
            for appearance in last5
        ),
        "days_since_last_appearance": (
            (as_of - last_appearance).days
            if last_appearance is not None
            else None
        ),
        "appeared_on_consecutive_days": consecutive_days_used >= 2,
        "consecutive_days_used": consecutive_days_used,
        "limited_history": (
            len(appearances) < 3 or not dated_appearances
        ),
    }


def innings_from_appearances(
    appearances: list[dict[str, Any]],
) -> float:
    return round(
        sum(
            extract_outs(appearance.get("stat", {}))
            for appearance in appearances
        ) / 3,
        1,
    )


def build_bullpen_snapshot(
    *,
    team_name: str | None,
    appearances: list[dict[str, Any]],
    as_of: date,
) -> BullpenSnapshot:
    season = aggregate_appearances(appearances)
    last7_start = as_of - timedelta(days=6)
    last3_start = as_of - timedelta(days=2)

    last7 = aggregate_appearances(
        [
            appearance
            for appearance in appearances
            if appearance_date(appearance)
            and last7_start <= appearance_date(appearance) <= as_of
        ]
    )
    last3 = aggregate_appearances(
        [
            appearance
            for appearance in appearances
            if appearance_date(appearance)
            and last3_start <= appearance_date(appearance) <= as_of
        ]
    )

    return BullpenSnapshot(
        team=(team_name or "UNKNOWN"),
        season_era=era_from_totals(season),
        season_whip=whip_from_totals(season),
        last7_era=era_from_totals(last7),
        innings_last3=round(last3["outs"] / 3, 1),
        appearances_last3=last3["appearances"],
        # The existing contract requires booleans. Unknown availability stays
        # neutral and is explicitly marked in the serialized source metadata.
        closer_available=True,
        setup_available=True,
        fatigue_score=None,
        quality_score=None,
        confidence=None,
    )


def serialize_bullpen_snapshot(
    snapshot: BullpenSnapshot,
    *,
    reliever_count: int,
    source_quality: str,
    source_detail: str,
    evidence_ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Adapt one normalized profile to the existing totals and SharpScore keys."""
    return {
        "season_era": snapshot.season_era,
        "season_whip": snapshot.season_whip,
        "last7_era": snapshot.last7_era,
        "innings_last3": snapshot.innings_last3,
        "appearances_last3": snapshot.appearances_last3,
        "closer_available": snapshot.closer_available,
        "setup_available": snapshot.setup_available,
        "availability_status": "UNCONFIRMED_NEUTRAL",
        "availability_source": "active_roster_without_depth_chart",
        "reliever_count": reliever_count,
        "data_source": "active_roster_reliever_game_logs",
        "source_quality": source_quality,
        "source_detail": source_detail,
        "evidence_ledger": evidence_ledger or [],
        # Legacy SharpScore keys. The values remain the same normalized data.
        "era": snapshot.season_era,
        "whip": snapshot.season_whip,
        "fip": None,
        "recent_usage": snapshot.innings_last3,
    }


def unavailable_bullpen_profile(
    team_name: str | None,
    *,
    source_quality: str = "UNAVAILABLE",
    source_detail: str = "active_roster_unavailable",
    evidence_ledger: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    snapshot = BullpenSnapshot(
        team=(team_name or "UNKNOWN"),
        season_era=None,
        season_whip=None,
        last7_era=None,
        innings_last3=0.0,
        appearances_last3=0,
        closer_available=True,
        setup_available=True,
        fatigue_score=None,
        quality_score=None,
        confidence=None,
    )

    return serialize_bullpen_snapshot(
        snapshot,
        reliever_count=0,
        source_quality=source_quality,
        source_detail=source_detail,
        evidence_ledger=evidence_ledger,
    )


def aggregate_appearances(
    appearances: list[dict[str, Any]],
) -> dict[str, int]:
    totals = {
        "appearances": 0,
        "outs": 0,
        "earned_runs": 0,
        "hits": 0,
        "walks": 0,
    }

    for appearance in appearances:
        stat = appearance.get("stat", {})
        totals["appearances"] += 1
        totals["outs"] += extract_outs(stat)
        totals["earned_runs"] += to_int(stat.get("earnedRuns")) or 0
        totals["hits"] += to_int(stat.get("hits")) or 0
        totals["walks"] += to_int(stat.get("baseOnBalls")) or 0

    return totals


def era_from_totals(totals: dict[str, int]) -> float | None:
    if totals["outs"] <= 0:
        return None

    return round(totals["earned_runs"] * 27 / totals["outs"], 2)


def whip_from_totals(totals: dict[str, int]) -> float | None:
    if totals["outs"] <= 0:
        return None

    return round(
        (totals["hits"] + totals["walks"]) * 3 / totals["outs"],
        2,
    )


def appearance_date(appearance: dict[str, Any]) -> date | None:
    value = appearance.get("date")

    if not value:
        return None

    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def extract_outs(stat: dict[str, Any]) -> int:
    outs = to_int(stat.get("outs"))

    if outs is not None:
        return outs

    value = stat.get("inningsPitched")

    if value in (None, ""):
        return 0

    try:
        whole, _, partial = str(value).partition(".")
        partial_outs = int(partial) if partial else 0

        if partial_outs not in (0, 1, 2):
            return 0

        return int(whole) * 3 + partial_outs
    except (TypeError, ValueError):
        return 0


def to_int(value: Any) -> int | None:
    try:
        if value in (None, ""):
            return None

        return int(value)
    except (TypeError, ValueError):
        return None

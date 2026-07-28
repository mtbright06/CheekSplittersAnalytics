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
    role_evidence = build_role_evidence(
        appearances,
        observed_relief_appearances,
        as_of=as_of,
    )
    workload_assessment = build_workload_assessment(
        workload,
        source_quality="COMPLETE",
        game_log_status="AVAILABLE",
    )
    availability_evidence = build_availability_evidence(
        source_quality="COMPLETE",
        game_log_status="AVAILABLE",
        limited_history=workload["limited_history"],
        workload_assessment=workload_assessment,
        role_evidence=role_evidence,
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
        "role_evidence": role_evidence,
        "workload_assessment": workload_assessment,
        "availability_evidence": availability_evidence,
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
    workload = unavailable_workload_facts()
    role_evidence = unavailable_role_evidence()
    workload_assessment = build_workload_assessment(
        workload,
        source_quality="UNAVAILABLE",
        game_log_status="FAILED",
    )
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
        "observed_last_appearance_date": workload["last_appearance_date"],
        "observed_appearances_last3": workload["appearances_last3"],
        "observed_innings_last3": workload["innings_last3"],
        "appearances_last5": workload["appearances_last5"],
        "innings_last5": workload["innings_last5"],
        "multi_inning_appearances_last5": workload[
            "multi_inning_appearances_last5"
        ],
        "days_since_last_appearance": workload["days_since_last_appearance"],
        "appeared_on_consecutive_days": workload[
            "appeared_on_consecutive_days"
        ],
        "consecutive_days_used": workload["consecutive_days_used"],
        "limited_history": workload["limited_history"],
        "role_evidence": role_evidence,
        "workload_assessment": workload_assessment,
        "availability_evidence": build_availability_evidence(
            source_quality="UNAVAILABLE",
            game_log_status="FAILED",
            limited_history=workload["limited_history"],
            workload_assessment=workload_assessment,
            role_evidence=role_evidence,
        ),
        "inclusion_status": "EXCLUDED",
        "exclusion_reason": "game_log_unavailable",
        "source_quality": "UNAVAILABLE",
        "game_log_status": "FAILED",
    }


def empty_pitcher_evidence(
    pitcher: dict[str, Any],
) -> dict[str, Any]:
    """Keep successful-but-empty game logs distinct from zero workload."""
    workload = empty_workload_facts()
    role_evidence = unavailable_role_evidence()
    workload_assessment = build_workload_assessment(
        workload,
        source_quality="COMPLETE",
        game_log_status="EMPTY",
    )
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
        "observed_last_appearance_date": workload["last_appearance_date"],
        "observed_appearances_last3": workload["appearances_last3"],
        "observed_innings_last3": workload["innings_last3"],
        "appearances_last5": workload["appearances_last5"],
        "innings_last5": workload["innings_last5"],
        "multi_inning_appearances_last5": workload[
            "multi_inning_appearances_last5"
        ],
        "days_since_last_appearance": workload["days_since_last_appearance"],
        "appeared_on_consecutive_days": workload[
            "appeared_on_consecutive_days"
        ],
        "consecutive_days_used": workload["consecutive_days_used"],
        "limited_history": workload["limited_history"],
        "role_evidence": role_evidence,
        "workload_assessment": workload_assessment,
        "availability_evidence": build_availability_evidence(
            source_quality="COMPLETE",
            game_log_status="EMPTY",
            limited_history=workload["limited_history"],
            workload_assessment=workload_assessment,
            role_evidence=role_evidence,
        ),
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
        return empty_workload_facts()

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


def unavailable_workload_facts() -> dict[str, Any]:
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
        "limited_history": None,
    }


def empty_workload_facts() -> dict[str, Any]:
    facts = unavailable_workload_facts()
    facts["limited_history"] = True
    return facts


def build_workload_assessment(
    workload: dict[str, Any],
    *,
    source_quality: str,
    game_log_status: str,
) -> dict[str, Any]:
    """Describe observed workload without inferring pitcher availability.

    Thresholds are descriptive only: appearances are HEAVY at 3 in three days
    or 4 in five days; innings are HEAVY at 4.0 in three days or 5.0 in five.
    MODERATE begins at 2 appearances / 2.0 innings in three days or 3
    appearances / 3.0 innings in five days. Any lower observed activity is
    LIGHT.
    """
    assessment_quality = workload_assessment_source_quality(
        source_quality,
        game_log_status,
        workload.get("limited_history"),
    )
    unavailable = assessment_quality == "UNAVAILABLE"
    empty = assessment_quality == "EMPTY"

    rest_bucket = rest_bucket_for_workload(
        workload.get("days_since_last_appearance"),
        unavailable=unavailable,
    )
    consecutive_usage_bucket = consecutive_usage_bucket_for_workload(
        workload.get("consecutive_days_used"),
        unavailable=unavailable,
        empty=empty,
    )
    appearance_volume = appearance_volume_for_workload(
        workload.get("appearances_last3"),
        workload.get("appearances_last5"),
        unavailable=unavailable,
        empty=empty,
    )
    innings_volume = innings_volume_for_workload(
        workload.get("innings_last3"),
        workload.get("innings_last5"),
        unavailable=unavailable,
        empty=empty,
    )
    multi_inning_load = multi_inning_load_for_workload(
        workload.get("multi_inning_appearances_last5"),
        unavailable=unavailable,
        empty=empty,
    )
    overall_workload = overall_workload_for_assessment(
        appearance_volume=appearance_volume,
        innings_volume=innings_volume,
        consecutive_usage_bucket=consecutive_usage_bucket,
        multi_inning_load=multi_inning_load,
        assessment_quality=assessment_quality,
    )

    return {
        "rest_bucket": rest_bucket,
        "consecutive_usage_bucket": consecutive_usage_bucket,
        "appearance_volume": appearance_volume,
        "innings_volume": innings_volume,
        "multi_inning_load": multi_inning_load,
        "overall_workload": overall_workload,
        "source_quality": assessment_quality,
        "reasons": workload_assessment_reasons(
            workload,
            rest_bucket=rest_bucket,
            assessment_quality=assessment_quality,
        ),
    }


def build_availability_evidence(
    *,
    source_quality: str | None,
    game_log_status: str | None,
    limited_history: bool | None,
    workload_assessment: dict[str, Any] | None,
    role_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    """Summarize workload evidence without predicting pitcher availability."""
    assessment_quality = availability_source_quality(
        source_quality,
        game_log_status,
        limited_history,
        workload_assessment,
    )
    overall_workload = (
        workload_assessment.get("overall_workload")
        if isinstance(workload_assessment, dict)
        else None
    )

    if availability_evidence_is_unknown(
        source_quality=source_quality,
        game_log_status=game_log_status,
        limited_history=limited_history,
        assessment_quality=assessment_quality,
        overall_workload=overall_workload,
    ):
        return {
            "status": "UNKNOWN",
            "confidence": "LOW",
            "source_quality": assessment_quality,
            "reasons": availability_unknown_reasons(
                source_quality=source_quality,
                game_log_status=game_log_status,
                limited_history=limited_history,
                workload_assessment=workload_assessment,
            ),
        }

    if overall_workload in {"MODERATE", "HEAVY"}:
        return {
            "status": "OBSERVED_WORKLOAD_CONCERN",
            "confidence": "HIGH",
            "source_quality": assessment_quality,
            "reasons": availability_concern_reasons(
                workload_assessment,
                role_evidence,
            ),
        }

    return {
        "status": "NO_OBSERVED_CONCERN",
        "confidence": "HIGH",
        "source_quality": assessment_quality,
        "reasons": availability_no_concern_reasons(workload_assessment),
    }


def availability_source_quality(
    source_quality: str | None,
    game_log_status: str | None,
    limited_history: bool | None,
    workload_assessment: dict[str, Any] | None,
) -> str:
    if (
        source_quality is None
        or source_quality == "UNAVAILABLE"
        or game_log_status == "FAILED"
    ):
        return "UNAVAILABLE"
    if game_log_status == "EMPTY":
        return "EMPTY"
    if limited_history or source_quality == "PARTIAL":
        return "PARTIAL"
    if not isinstance(workload_assessment, dict):
        return "UNAVAILABLE"
    return workload_assessment.get("source_quality") or "UNAVAILABLE"


def availability_evidence_is_unknown(
    *,
    source_quality: str | None,
    game_log_status: str | None,
    limited_history: bool | None,
    assessment_quality: str,
    overall_workload: str | None,
) -> bool:
    return (
        source_quality in {None, "UNAVAILABLE", "PARTIAL"}
        or game_log_status in {None, "FAILED", "EMPTY"}
        or limited_history is True
        or assessment_quality != "COMPLETE"
        or overall_workload not in {"NONE", "LIGHT", "MODERATE", "HEAVY"}
    )


def availability_unknown_reasons(
    *,
    source_quality: str | None,
    game_log_status: str | None,
    limited_history: bool | None,
    workload_assessment: dict[str, Any] | None,
) -> list[str]:
    if source_quality == "UNAVAILABLE" or game_log_status == "FAILED":
        return ["pitcher game log unavailable"]
    if game_log_status == "EMPTY":
        return ["successful game log contains no appearances"]
    if limited_history:
        return ["limited observed relief history"]
    if source_quality == "PARTIAL":
        return ["partial pitcher evidence"]
    if not isinstance(workload_assessment, dict):
        return ["workload assessment unavailable"]
    return ["workload assessment has incomplete provenance"]


def availability_concern_reasons(
    workload_assessment: dict[str, Any],
    role_evidence: dict[str, Any] | None,
) -> list[str]:
    overall_workload = workload_assessment["overall_workload"].lower()
    reasons = [f"{overall_workload.title()} workload assessment"]
    reasons.extend(workload_assessment.get("reasons", []))

    role = primary_role_candidate(role_evidence)
    if role:
        reasons.append(
            f"{role.replace('_', ' ').title()} candidate with {overall_workload} recent workload"
        )
    return reasons


def availability_no_concern_reasons(
    workload_assessment: dict[str, Any],
) -> list[str]:
    overall_workload = workload_assessment["overall_workload"]
    reasons = [
        (
            "no observed workload"
            if overall_workload == "NONE"
            else "light workload assessment"
        )
    ]
    reasons.extend(workload_assessment.get("reasons", []))
    reasons.append("no elevated workload buckets observed")
    return reasons


def primary_role_candidate(
    role_evidence: dict[str, Any] | None,
) -> str | None:
    if not isinstance(role_evidence, dict):
        return None
    candidates = role_evidence.get("candidate_roles")
    if not isinstance(candidates, list) or not candidates:
        return None
    role = candidates[0].get("role") if isinstance(candidates[0], dict) else None
    return role if isinstance(role, str) else None


def workload_assessment_source_quality(
    source_quality: str,
    game_log_status: str,
    limited_history: bool | None,
) -> str:
    if source_quality == "UNAVAILABLE" or game_log_status == "FAILED":
        return "UNAVAILABLE"
    if game_log_status == "EMPTY":
        return "EMPTY"
    if source_quality == "PARTIAL" or limited_history:
        return "PARTIAL"
    return "COMPLETE"


def rest_bucket_for_workload(
    days_since_last_appearance: int | None,
    *,
    unavailable: bool,
) -> str:
    if unavailable:
        return "UNKNOWN"
    if days_since_last_appearance is None:
        return "NO_DATED_APPEARANCE"
    if days_since_last_appearance <= 0:
        return "SAME_DAY"
    if days_since_last_appearance == 1:
        return "ONE_DAY"
    if days_since_last_appearance == 2:
        return "TWO_DAYS"
    return "THREE_PLUS_DAYS"


def consecutive_usage_bucket_for_workload(
    consecutive_days_used: int | None,
    *,
    unavailable: bool,
    empty: bool,
) -> str:
    if unavailable:
        return "UNKNOWN"
    if empty:
        return "NONE"
    if consecutive_days_used is None:
        return "UNKNOWN"
    if consecutive_days_used <= 1:
        return "NONE"
    if consecutive_days_used == 2:
        return "TWO_DAYS"
    if consecutive_days_used == 3:
        return "THREE_DAYS"
    return "FOUR_PLUS_DAYS"


def appearance_volume_for_workload(
    appearances_last3: int | None,
    appearances_last5: int | None,
    *,
    unavailable: bool,
    empty: bool,
) -> str:
    if unavailable:
        return "UNKNOWN"
    if empty:
        return "NONE"
    if appearances_last3 is None or appearances_last5 is None:
        return "UNKNOWN"
    if appearances_last3 >= 3 or appearances_last5 >= 4:
        return "HEAVY"
    if appearances_last3 >= 2 or appearances_last5 >= 3:
        return "MODERATE"
    if appearances_last3 > 0 or appearances_last5 > 0:
        return "LIGHT"
    return "NONE"


def innings_volume_for_workload(
    innings_last3: float | None,
    innings_last5: float | None,
    *,
    unavailable: bool,
    empty: bool,
) -> str:
    if unavailable:
        return "UNKNOWN"
    if empty:
        return "NONE"
    if innings_last3 is None or innings_last5 is None:
        return "UNKNOWN"
    if innings_last3 >= 4.0 or innings_last5 >= 5.0:
        return "HEAVY"
    if innings_last3 >= 2.0 or innings_last5 >= 3.0:
        return "MODERATE"
    if innings_last3 > 0 or innings_last5 > 0:
        return "LIGHT"
    return "NONE"


def multi_inning_load_for_workload(
    multi_inning_appearances_last5: int | None,
    *,
    unavailable: bool,
    empty: bool,
) -> str:
    if unavailable:
        return "UNKNOWN"
    if empty:
        return "NONE"
    if multi_inning_appearances_last5 is None:
        return "UNKNOWN"
    if multi_inning_appearances_last5 >= 2:
        return "REPEATED"
    if multi_inning_appearances_last5 == 1:
        return "PRESENT"
    return "NONE"


def overall_workload_for_assessment(
    *,
    appearance_volume: str,
    innings_volume: str,
    consecutive_usage_bucket: str,
    multi_inning_load: str,
    assessment_quality: str,
) -> str:
    if assessment_quality == "UNAVAILABLE":
        return "UNKNOWN"

    severe_components = (
        appearance_volume == "HEAVY",
        innings_volume == "HEAVY",
        consecutive_usage_bucket == "FOUR_PLUS_DAYS",
    )
    elevated_components = sum(
        (
            appearance_volume in {"MODERATE", "HEAVY"},
            innings_volume in {"MODERATE", "HEAVY"},
            consecutive_usage_bucket in {"THREE_DAYS", "FOUR_PLUS_DAYS"},
            multi_inning_load == "REPEATED",
        )
    )
    light_components = (
        appearance_volume == "LIGHT",
        innings_volume == "LIGHT",
        consecutive_usage_bucket == "TWO_DAYS",
        multi_inning_load == "PRESENT",
    )

    if any(severe_components) or elevated_components >= 2:
        return "HEAVY"
    if elevated_components == 1:
        return "MODERATE"
    if assessment_quality == "PARTIAL":
        return "UNKNOWN"
    if any(light_components):
        return "LIGHT"
    return "NONE"


def workload_assessment_reasons(
    workload: dict[str, Any],
    *,
    rest_bucket: str,
    assessment_quality: str,
) -> list[str]:
    reasons = []
    appearances_last3 = workload.get("appearances_last3")
    appearances_last5 = workload.get("appearances_last5")
    innings_last3 = workload.get("innings_last3")
    innings_last5 = workload.get("innings_last5")
    consecutive_days_used = workload.get("consecutive_days_used")
    multi_inning_appearances_last5 = workload.get(
        "multi_inning_appearances_last5"
    )

    if appearances_last3:
        reasons.append(
            f"{appearances_last3} {'appearance' if appearances_last3 == 1 else 'appearances'} in the last 3 calendar days"
        )
    if appearances_last5 and appearances_last5 != appearances_last3:
        reasons.append(
            f"{appearances_last5} {'appearance' if appearances_last5 == 1 else 'appearances'} in the last 5 calendar days"
        )
    if innings_last3:
        reasons.append(
            f"{innings_last3:.1f} observed relief innings in the last 3 calendar days"
        )
    if innings_last5 and innings_last5 != innings_last3:
        reasons.append(
            f"{innings_last5:.1f} observed relief innings in the last 5 calendar days"
        )
    if consecutive_days_used and consecutive_days_used >= 2:
        reasons.append(f"{consecutive_days_used} consecutive usage dates")
    if multi_inning_appearances_last5:
        reasons.append(
            f"{multi_inning_appearances_last5} multi-inning relief appearances in the last 5 calendar days"
        )
    if rest_bucket == "NO_DATED_APPEARANCE":
        reasons.append("no dated observed relief appearance")
    if assessment_quality == "EMPTY":
        reasons.append("successful game log contains no appearances")
    elif assessment_quality == "PARTIAL":
        reasons.append("limited observed relief history")
    elif assessment_quality == "UNAVAILABLE":
        reasons.append("pitcher game log unavailable")
    return reasons


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


def build_role_evidence(
    appearances: list[dict[str, Any]],
    observed_relief_appearances: list[dict[str, Any]],
    *,
    as_of: date,
) -> dict[str, Any]:
    """Summarize observed role patterns without assigning a definitive role."""
    season_saves = optional_stat_sum(appearances, "saves")
    season_holds = optional_stat_sum(appearances, "holds")
    games_finished = optional_stat_sum(appearances, "gamesFinished")
    last5_start = as_of - timedelta(days=4)
    recent_relief = [
        appearance
        for appearance in observed_relief_appearances
        if (
            (appearance_day := appearance_date(appearance))
            is not None
            and last5_start <= appearance_day <= as_of
        )
    ]
    has_dated_relief = any(
        appearance_date(appearance) is not None
        and appearance_date(appearance) <= as_of
        for appearance in observed_relief_appearances
    )
    recent_saves = recent_optional_stat_sum(
        recent_relief,
        "saves",
        has_dated_relief=has_dated_relief,
    )
    recent_holds = recent_optional_stat_sum(
        recent_relief,
        "holds",
        has_dated_relief=has_dated_relief,
    )
    recent_games_finished = recent_optional_stat_sum(
        recent_relief,
        "gamesFinished",
        has_dated_relief=has_dated_relief,
    )
    multi_inning_appearances = sum(
        extract_outs(appearance.get("stat", {})) >= 6
        for appearance in observed_relief_appearances
    )
    relief_appearance_count = len(observed_relief_appearances)
    multi_inning_rate = (
        round(
            multi_inning_appearances / relief_appearance_count,
            3,
        )
        if relief_appearance_count
        else None
    )
    short_start_appearances = sum(
        is_short_start(appearance)
        for appearance in appearances
    )

    facts = {
        "season_saves": season_saves,
        "season_holds": season_holds,
        "games_finished": games_finished,
        "recent_games_finished_last5": recent_games_finished,
        "recent_saves_last5": recent_saves,
        "recent_holds_last5": recent_holds,
        "multi_inning_relief_appearances": multi_inning_appearances,
        "multi_inning_relief_rate": multi_inning_rate,
        "short_start_appearances": short_start_appearances,
    }

    return {
        "facts": facts,
        "candidate_roles": role_candidates(
            facts,
            relief_appearance_count=relief_appearance_count,
        ),
    }


def unavailable_role_evidence() -> dict[str, Any]:
    return {
        "facts": {
            "season_saves": None,
            "season_holds": None,
            "games_finished": None,
            "recent_games_finished_last5": None,
            "recent_saves_last5": None,
            "recent_holds_last5": None,
            "multi_inning_relief_appearances": None,
            "multi_inning_relief_rate": None,
            "short_start_appearances": None,
        },
        "candidate_roles": [],
    }


def optional_stat_sum(
    appearances: list[dict[str, Any]],
    stat_name: str,
) -> int | None:
    if not appearances:
        return None

    values = [
        to_int(appearance.get("stat", {}).get(stat_name))
        for appearance in appearances
    ]

    if any(value is None for value in values):
        return None

    return sum(values)


def recent_optional_stat_sum(
    appearances: list[dict[str, Any]],
    stat_name: str,
    *,
    has_dated_relief: bool,
) -> int | None:
    if not has_dated_relief:
        return None

    if not appearances:
        return 0

    return optional_stat_sum(appearances, stat_name)


def is_short_start(appearance: dict[str, Any]) -> bool:
    stat = appearance.get("stat", {})

    if (to_int(stat.get("gamesStarted")) or 0) <= 0:
        return False

    outs = to_int(stat.get("outs"))

    if outs is None and stat.get("inningsPitched") not in (None, ""):
        outs = extract_outs(stat)

    return outs is not None and outs <= 9


def role_candidates(
    facts: dict[str, Any],
    *,
    relief_appearance_count: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    saves = facts["season_saves"]
    holds = facts["season_holds"]
    games_finished = facts["games_finished"]
    multi_inning = facts["multi_inning_relief_appearances"]
    multi_inning_rate = facts["multi_inning_relief_rate"]
    short_starts = facts["short_start_appearances"]

    if saves is not None and saves >= 1:
        if saves >= 10 and (games_finished or 0) >= 10:
            confidence = "HIGH"
        elif saves >= 5 and (games_finished or 0) >= 5:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        evidence = [f"{saves} season saves"]
        if games_finished is not None:
            evidence.append(f"{games_finished} games finished")
        if facts["recent_saves_last5"]:
            evidence.append(
                f"{facts['recent_saves_last5']} saves in last 5 calendar days"
            )
        candidates.append(
            role_candidate("CLOSER", confidence, evidence)
        )

    if holds is not None and holds >= 1:
        confidence = (
            "HIGH" if holds >= 10 else "MEDIUM" if holds >= 5 else "LOW"
        )
        evidence = [f"{holds} season holds"]
        if facts["recent_holds_last5"]:
            evidence.append(
                f"{facts['recent_holds_last5']} holds in last 5 calendar days"
            )
        candidates.append(
            role_candidate("SETUP", confidence, evidence)
        )

    if (
        games_finished is not None
        and games_finished >= 3
        and saves == 0
    ):
        confidence = (
            "HIGH"
            if games_finished >= 15
            else "MEDIUM" if games_finished >= 8 else "LOW"
        )
        candidates.append(
            role_candidate(
                "GAME_FINISHER",
                confidence,
                [f"{games_finished} games finished", "0 season saves"],
            )
        )

    if multi_inning and relief_appearance_count:
        if multi_inning >= 5 and (multi_inning_rate or 0) >= 0.5:
            confidence = "HIGH"
        elif multi_inning >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        candidates.append(
            role_candidate(
                "BULK_RELIEVER",
                confidence,
                [
                    f"{multi_inning} relief outings of at least 6 outs",
                    (
                        f"{multi_inning_rate:.0%} multi-inning relief usage"
                        if multi_inning_rate is not None
                        else ""
                    ),
                ],
            )
        )

    if short_starts and relief_appearance_count:
        if short_starts >= 5 and relief_appearance_count >= 5:
            confidence = "HIGH"
        elif short_starts >= 3 and relief_appearance_count >= 3:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"
        candidates.append(
            role_candidate(
                "SHORT_START_RELIEF_USAGE",
                confidence,
                [
                    (
                        f"{short_starts} short-start outings "
                        "of 3.0 innings or fewer"
                    ),
                    f"{relief_appearance_count} observed relief outings",
                ],
            )
        )

    return candidates


def role_candidate(
    role: str,
    confidence: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "role": role,
        "confidence": confidence,
        "evidence": [item for item in evidence if item],
    }


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

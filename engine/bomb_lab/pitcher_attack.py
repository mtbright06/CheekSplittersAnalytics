from datetime import datetime, timedelta
import time

import pandas as pd
from pybaseball import statcast

from engine.bomb_lab.constants import PARK_FACTORS
from engine.bomb_lab.statcast_contract import statcast_barrel_flag
from engine.hitters.target_hitters import attach_target_hitters_to_pitchers
from engine.mlb.schedule import fetch_mlb_schedule


RECENT_DAYS = 30
SEASON_DAYS = 120

WATCH_THRESHOLD = 52.5
STRONG_THRESHOLD = 57.5
ELITE_THRESHOLD = 65.0
WATCH_RELIABILITY_MIN = 55.0
STRONG_RELIABILITY_MIN = 70.0

PITCHER_HARD_HIT_WEIGHT = 70.0
PITCHER_BARREL_WEIGHT = 220.0
PITCHER_HR_PER_BBE_WEIGHT = 180.0
PITCHER_AVG_EV_BASELINE = 84.0
PITCHER_AVG_EV_WEIGHT = 3.0
PITCHER_AIR_BALL_WEIGHT = 18.0


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def get_probables():
    data = fetch_mlb_schedule()
    rows = []

    for day in data.get("dates", []):
        for game in day.get("games", []):
            teams = game.get("teams", {})
            away = teams.get("away", {})
            home = teams.get("home", {})

            away_team = away.get("team", {}).get("name")
            home_team = home.get("team", {}).get("name")
            away_abbr = away.get("team", {}).get("abbreviation")
            home_abbr = home.get("team", {}).get("abbreviation")
            away_id = away.get("team", {}).get("id")
            home_id = home.get("team", {}).get("id")

            for team_blob, opponent_name, opponent_abbr, opponent_id in [
                (away, home_team, home_abbr, home_id),
                (home, away_team, away_abbr, away_id),
            ]:
                pitcher = team_blob.get("probablePitcher")
                if not pitcher:
                    continue

                rows.append(
                    {
                        "game_pk": game.get("gamePk"),
                        "pitcher_id": pitcher.get("id"),
                        "pitcher": pitcher.get("fullName"),
                        "pitching_team": team_blob.get("team", {}).get("name"),
                        "pitching_team_abbr": team_blob.get("team", {}).get("abbreviation"),
                        "pitching_team_id": team_blob.get("team", {}).get("id"),
                        "opponent": opponent_name,
                        "opponent_abbr": opponent_abbr,
                        "opponent_team_id": opponent_id,
                        "game": f"{away_team} @ {home_team}",
                        "venue": game.get("venue", {}).get("name"),
                        "commence_time": game.get("gameDate"),
                    }
                )

    return pd.DataFrame(rows)


def get_statcast_data(days, retries=3):
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")

    for attempt in range(1, retries + 1):
        try:
            return statcast(
                start_dt=start_date,
                end_dt=end_date,
                verbose=False,
            )
        except Exception as ex:
            print(f"Statcast pull failed for {days} days, attempt {attempt}/{retries}: {ex}")
            time.sleep(3)

    return pd.DataFrame()


def build_split_stats(statcast_df, prefix):
    if statcast_df.empty:
        return pd.DataFrame()

    df = statcast_df[statcast_df["launch_speed"].notna()].copy()

    if df.empty:
        return pd.DataFrame()

    df["hard_hit"] = (df["launch_speed"] >= 95).astype(int)

    if "launch_speed_angle" in df.columns:
        df["barrel"] = df.apply(statcast_barrel_flag, axis=1)
    else:
        df["barrel"] = 0

    df["air_ball"] = df["bb_type"].isin(
        ["fly_ball", "line_drive", "popup"]
    ).astype(int)

    grouped = (
        df.groupby(["pitcher", "stand"])
        .agg(
            hard_hit_pct=("hard_hit", "mean"),
            barrel_pct=("barrel", "mean"),
            avg_ev=("launch_speed", "mean"),
            hrs_allowed=("events", lambda x: (x == "home_run").sum()),
            batted_balls=("launch_speed", "count"),
            air_pct=("air_ball", "mean"),
            pitcher_throw=("p_throws", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
        )
        .reset_index()
        .rename(columns={"pitcher": "pitcher_id"})
    )

    grouped["hr_per_bbe"] = grouped["hrs_allowed"] / grouped[
        "batted_balls"
    ].replace(0, pd.NA)

    rename = {
        col: f"{prefix}_{col}"
        for col in [
            "hard_hit_pct",
            "barrel_pct",
            "avg_ev",
            "hrs_allowed",
            "batted_balls",
            "air_pct",
            "hr_per_bbe",
        ]
    }

    return grouped.rename(columns=rename)

def pitcher_risk(hh, barrel, ev, hr_rate, air):
    score = (
        safe_num(hh) * PITCHER_HARD_HIT_WEIGHT
        + safe_num(barrel) * PITCHER_BARREL_WEIGHT
        + safe_num(hr_rate) * PITCHER_HR_PER_BBE_WEIGHT
        + max(safe_num(ev) - PITCHER_AVG_EV_BASELINE, 0)
        * PITCHER_AVG_EV_WEIGHT
        + safe_num(air) * PITCHER_AIR_BALL_WEIGHT
    )

    return round(clamp(score), 1)


def sample_confidence(recent_bbe, season_bbe):
    recent_bbe = safe_num(recent_bbe)
    season_bbe = safe_num(season_bbe)

    score = 35

    if recent_bbe >= 45:
        score += 35
    elif recent_bbe >= 30:
        score += 27
    elif recent_bbe >= 20:
        score += 18
    elif recent_bbe >= 12:
        score += 10

    if season_bbe >= 160:
        score += 25
    elif season_bbe >= 100:
        score += 18
    elif season_bbe >= 60:
        score += 10

    return round(clamp(score, 30, 95), 1)


def bomb_authority_score(pitcher_score, park):
    """Score HR vulnerability from strength inputs only."""
    return round(
        clamp(
            safe_num(pitcher_score) * 0.80
            + safe_num(park) * 0.20
        ),
        1,
    )


def bomb_reliability(recent_bbe, season_bbe):
    """Measure trust in today's Bomb Lab inputs, not HR probability."""
    reliability = sample_confidence(recent_bbe, season_bbe)
    concerns = []

    recent_bbe = safe_num(recent_bbe)
    season_bbe = safe_num(season_bbe)

    if recent_bbe <= 0:
        concerns.append("recent_statcast_sample_missing")
    elif recent_bbe < 20:
        concerns.append("recent_statcast_sample_thin")

    if season_bbe <= 0:
        concerns.append("season_statcast_sample_missing")
    elif season_bbe < 60:
        concerns.append("season_statcast_sample_thin")

    return {
        "score": reliability,
        "concerns": concerns,
        "definition": (
            "Bomb Lab Reliability measures trust in today's available "
            "Statcast sample inputs only; it is not HR probability or "
            "Bomb Score strength."
        ),
    }


def park_score(team_name):
    factor = PARK_FACTORS.get(team_name, 1.0)
    return round(clamp(50 + ((factor - 1.0) * 180)), 1)


def environment_label(score):
    if score >= 75:
        return "ELITE"
    if score >= 65:
        return "PLUS"
    if score >= 55:
        return "PLAYABLE"
    return "NEUTRAL"


def tier(score, reliability=None):
    if reliability is not None and safe_num(reliability) < WATCH_RELIABILITY_MIN:
        return "PASS"

    if score >= ELITE_THRESHOLD:
        if reliability is not None and safe_num(reliability) < STRONG_RELIABILITY_MIN:
            return "👀 WATCH"
        return "🔥 ELITE"

    if score >= STRONG_THRESHOLD:
        if reliability is not None and safe_num(reliability) < STRONG_RELIABILITY_MIN:
            return "👀 WATCH"
        return "💣 STRONG"

    if score >= WATCH_THRESHOLD:
        return "👀 WATCH"

    return "PASS"


def target_side_label(rows):
    if "stand" not in rows.columns or rows.empty:
        return "ANY"

    if len(rows) < 2:
        side = rows.iloc[0].get("stand")
        return side if side in ["L", "R"] else "ANY"

    l_score = rows[rows["stand"] == "L"]["bomb_score"].max()
    r_score = rows[rows["stand"] == "R"]["bomb_score"].max()

    l_score = safe_num(l_score, None)
    r_score = safe_num(r_score, None)

    if l_score is None and r_score is None:
        return "ANY"
    if l_score is None:
        return "R"
    if r_score is None:
        return "L"
    if abs(l_score - r_score) <= 5:
        return "BOTH"

    return "L" if l_score > r_score else "R"


def build_why(row):
    why = []

    if row.get("recent_barrel_pct", 0) >= 0.10:
        why.append(
            f"Recent barrel rate allowed is dangerous ({row['recent_barrel_pct']:.1%})."
        )

    if row.get("recent_hard_hit_pct", 0) >= 0.42:
        why.append(
            f"Recent hard-hit allowed is elevated ({row['recent_hard_hit_pct']:.1%})."
        )

    if row.get("season_barrel_pct", 0) >= 0.09:
        why.append(
            f"Season barrel baseline supports the trend ({row['season_barrel_pct']:.1%})."
        )

    if row.get("recent_hr_per_bbe", 0) >= 0.06:
        why.append(
            f"Recent HR per batted ball is flashing ({row['recent_hr_per_bbe']:.1%})."
        )

    if row.get("park_factor", 1.0) > 1.05:
        why.append("Park environment boosts home run upside.")

    if row.get("sample_confidence", 100) < 55:
        why.append("Signal is volatile because the recent sample is thin.")

    if not why:
        why.append("Playable profile, but no major standout bomb signal.")

    return why


def build_bomb_lab_card():
    probables = get_probables()

    if probables.empty:
        return empty_card("No probable pitchers found.")

    recent_raw = get_statcast_data(RECENT_DAYS)
    season_raw = get_statcast_data(SEASON_DAYS)

    recent = build_split_stats(recent_raw, "recent")
    season = build_split_stats(season_raw, "season")

    if recent.empty and season.empty:
        return empty_card("No Statcast pitcher data available.")

    merged = probables.merge(recent, on="pitcher_id", how="left")

    if season.empty:
        for col in [
            "season_hard_hit_pct",
            "season_barrel_pct",
            "season_avg_ev",
            "season_hrs_allowed",
            "season_batted_balls",
            "season_air_pct",
            "season_hr_per_bbe",
        ]:
            merged[col] = 0
    else:
        merged = merged.merge(season, on=["pitcher_id", "stand"], how="left")

    for col in merged.columns:
        if any(x in col for x in ["pct", "ev", "allowed", "balls", "bbe"]):
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    rows = []

    for _, row in merged.iterrows():
        recent_risk = pitcher_risk(
            row.get("recent_hard_hit_pct"),
            row.get("recent_barrel_pct"),
            row.get("recent_avg_ev"),
            row.get("recent_hr_per_bbe"),
            row.get("recent_air_pct"),
        )

        season_risk = pitcher_risk(
            row.get("season_hard_hit_pct"),
            row.get("season_barrel_pct"),
            row.get("season_avg_ev"),
            row.get("season_hr_per_bbe"),
            row.get("season_air_pct"),
        )

        pitcher_score = round((recent_risk * 0.65) + (season_risk * 0.35), 1)
        park = park_score(row.get("opponent"))
        reliability = bomb_reliability(
            row.get("recent_batted_balls"),
            row.get("season_batted_balls"),
        )

        score = bomb_authority_score(
            pitcher_score,
            park,
        )

        park_factor = PARK_FACTORS.get(row.get("opponent"), 1.0)

        item = {
            "stand": row.get("stand") or "ANY",
            "pitcher": row.get("pitcher"),
            "pitching_team": row.get("pitching_team"),
            "pitching_team_abbr": row.get("pitching_team_abbr"),
            "pitching_team_id": row.get("pitching_team_id"),
            "opponent_abbr": row.get("opponent_abbr"),
            "opponent_team_id": row.get("opponent_team_id"),
            "opponent": row.get("opponent"),
            "game": row.get("game"),
            "venue": row.get("venue"),
            "commence_time": row.get("commence_time"),
            "target_side": row.get("stand") or "ANY",
            "bomb_score": score,
            "tier": tier(score, reliability["score"]),
            "pitcher_throw": (
                row.get("pitcher_throw")
                or row.get("pitcher_throw_x")
                or row.get("pitcher_throw_y")
            ),
            "pitcher_vulnerability": pitcher_score,
            "environment_score": park,
            "pitcher_risk": pitcher_score,
            "recent_risk": recent_risk,
            "season_risk": season_risk,
            "park_score": park,
            "environment": environment_label(park),
            "bomb_reliability": reliability["score"],
            "reliability": reliability["score"],
            "reliability_concerns": reliability["concerns"],
            "reliability_definition": reliability["definition"],
            "sample_confidence": reliability["score"],
            "recent_hard_hit_pct": round(safe_num(row.get("recent_hard_hit_pct")), 3),
            "recent_barrel_pct": round(safe_num(row.get("recent_barrel_pct")), 3),
            "recent_avg_ev": round(safe_num(row.get("recent_avg_ev")), 1),
            "recent_hr_per_bbe": round(safe_num(row.get("recent_hr_per_bbe")), 3),
            "recent_batted_balls": int(safe_num(row.get("recent_batted_balls"))),
            "season_hard_hit_pct": round(safe_num(row.get("season_hard_hit_pct")), 3),
            "season_barrel_pct": round(safe_num(row.get("season_barrel_pct")), 3),
            "season_avg_ev": round(safe_num(row.get("season_avg_ev")), 1),
            "season_hr_per_bbe": round(safe_num(row.get("season_hr_per_bbe")), 3),
            "season_batted_balls": int(safe_num(row.get("season_batted_balls"))),
            "park_factor": park_factor,
        }

        item["why"] = build_why(item)
        rows.append(item)

    df = pd.DataFrame(rows)

    if df.empty:
        return empty_card("No Bomb Lab rows generated.")

    grouped = []

    for pitcher, group in df.groupby("pitcher", dropna=False):
        group = group.sort_values("bomb_score", ascending=False)
        best = group.iloc[0].to_dict()
        best["target_side"] = target_side_label(group)
        best["side_breakdown"] = group[
            [
                "target_side",
                "bomb_score",
                "pitcher_risk",
                "recent_barrel_pct",
                "recent_hard_hit_pct",
                "recent_batted_balls",
            ]
        ].to_dict("records")
        grouped.append(best)

    grouped = sorted(grouped, key=lambda x: x["bomb_score"], reverse=True)
    grouped = attach_target_hitters_to_pitchers(grouped, season_raw)
    for item in grouped:
        if item.get("hr_opportunity_score") is not None:
            item["tier"] = tier(
                item["hr_opportunity_score"],
                item.get("opportunity_reliability"),
            )
            item["bomb_score"] = item["hr_opportunity_score"]

    grouped = sorted(
        grouped,
        key=lambda x: x.get("hr_opportunity_score") or x["bomb_score"],
        reverse=True,
    )

    table = [
        {
            "tier": x["tier"],
            "bomb_score": x["bomb_score"],
            "hr_opportunity_score": x.get("hr_opportunity_score"),
            "hitter_hr_ability": x.get("hitter_hr_ability"),
            "pitcher_vulnerability": x.get("pitcher_vulnerability"),
            "confidence": x["sample_confidence"],
            "reliability": x["bomb_reliability"],
            "opportunity_reliability": x.get("opportunity_reliability"),
            "reliability_concerns": x["reliability_concerns"],
            "recommended_hitter": x.get("recommended_hitter"),
            "pitcher": x["pitcher"],
            "pitching_team": x["pitching_team"],
            "target_offense": x["opponent"],
            "game": x["game"],
            "attack_side": x["target_side"],
            "pitcher_risk": x["pitcher_risk"],
            "barrel_pct": x["recent_barrel_pct"],
            "hard_hit_pct": x["recent_hard_hit_pct"],
            "hr_per_bbe": x["recent_hr_per_bbe"],
            "park": x["environment"],
            "bbe": x["recent_batted_balls"],
        }
        for x in grouped
    ]

    return {
        "sport": "MLB",
        "type": "bomb_lab",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "pitchers_loaded": len(grouped),
            "elite": len([x for x in grouped if x["tier"] == "🔥 ELITE"]),
            "strong": len([x for x in grouped if x["tier"] == "💣 STRONG"]),
            "watch": len([x for x in grouped if x["tier"] == "👀 WATCH"]),
        },
        "table": table,
        "pitchers": grouped,
    }


def empty_card(message):
    return {
        "sport": "MLB",
        "type": "bomb_lab",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": {
            "pitchers_loaded": 0,
            "elite": 0,
            "strong": 0,
            "watch": 0,
        },
        "table": [],
        "pitchers": [],
        "message": message,
    }

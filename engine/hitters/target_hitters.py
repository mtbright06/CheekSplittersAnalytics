from datetime import datetime

import pandas as pd

from engine.lineups.mlb_roster import (
    fetch_active_roster,
    roster_id_set,
    roster_name_map,
    roster_position_map,
)
from engine.lineups.models import (
    GameLineupStatus,
    LineupActionability,
    PlayerLineupStatus,
)
from engine.bomb_lab.statcast_contract import statcast_barrel_flag
from engine.mlb import offense
from engine.hitters.team_abbreviations import statcast_team_abbreviations


HITTER_BARREL_CENTER = 0.04
HITTER_BARREL_HALF_RANGE = 0.08
HITTER_HARD_HIT_CENTER = 0.09
HITTER_HARD_HIT_HALF_RANGE = 0.09
HITTER_AVG_EV_CENTER = 84.0
HITTER_AVG_EV_HALF_RANGE = 8.0
HITTER_SPLIT_HR_CENTER = 8.0
HITTER_SPLIT_HR_HALF_RANGE = 12.0

HITTER_BARREL_WEIGHT = 0.45
HITTER_HARD_HIT_WEIGHT = 0.20
HITTER_AVG_EV_WEIGHT = 0.20
HITTER_SPLIT_POWER_WEIGHT = 0.15

OPPORTUNITY_PITCHER_WEIGHT = 0.40
OPPORTUNITY_HITTER_WEIGHT = 0.45
OPPORTUNITY_ENVIRONMENT_WEIGHT = 0.15


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clamp_score(value):
    return max(0.0, min(100.0, value))


def centered_score(value, center, half_range):
    if half_range <= 0:
        return 50.0

    return clamp_score(50.0 + ((safe_num(value) - center) / half_range) * 50.0)


def side_matches(bat_side, attack_side):
    bat_side = str(bat_side or "").upper()
    attack_side = str(attack_side or "ANY").upper()

    if attack_side in ["ANY", "BOTH"]:
        return True

    return bat_side == attack_side


def star_rating(score):
    if score >= 90:
        return "★★★★★"
    if score >= 82:
        return "★★★★☆"
    if score >= 74:
        return "★★★★"
    if score >= 66:
        return "★★★☆"
    if score >= 58:
        return "★★★"
    return "★★"


def days_since(date_value):
    if not date_value:
        return None

    try:
        dt = pd.to_datetime(date_value).date()
        return (datetime.today().date() - dt).days
    except Exception:
        return None


def batting_team(row):
    if row.get("inning_topbot") == "Top":
        return row.get("away_team")
    return row.get("home_team")


def add_contact_flags(df):
    df = df.copy()

    launch_speed = pd.to_numeric(df["launch_speed"], errors="coerce").fillna(0)

    df["hard_hit"] = (launch_speed >= 95).astype(int)

    if "launch_speed_angle" in df.columns:
        df["barrel"] = df.apply(statcast_barrel_flag, axis=1)
    else:
        df["barrel"] = 0

    df["is_hr"] = (df["events"] == "home_run").astype(int)

    return df


def build_hitter_profiles(statcast_df, team_abbr, roster_players):
    if statcast_df is None or statcast_df.empty:
        return []

    required = [
        "batter",
        "stand",
        "p_throws",
        "events",
        "launch_speed",
        "launch_angle",
        "game_date",
        "inning_topbot",
        "away_team",
        "home_team",
    ]

    for col in required:
        if col not in statcast_df.columns:
            return []

    allowed_ids = roster_id_set(roster_players)
    names = roster_name_map(roster_players)
    positions = roster_position_map(roster_players)

    if not allowed_ids:
        return []

    df = statcast_df.copy()
    df["batting_team"] = df.apply(batting_team, axis=1)
    team_abbrs = statcast_team_abbreviations(team_abbr)
    df = df[df["batting_team"].isin(team_abbrs)].copy()

    if df.empty:
        return []

    df["batter"] = pd.to_numeric(df["batter"], errors="coerce")
    df = df[df["batter"].isin(allowed_ids)].copy()

    if df.empty:
        return []

    df = add_contact_flags(df)
    df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")

    grouped = (
        df.groupby(["batter", "stand"])
        .agg(
            pa=("events", "count"),
            bbe=("launch_speed", lambda x: x.notna().sum()),
            hard_hit_pct=("hard_hit", "mean"),
            barrel_pct=("barrel", "mean"),
            avg_ev=("launch_speed", "mean"),
            hr=("is_hr", "sum"),
        )
        .reset_index()
    )

    hitter_rows = []

    for batter_id, batter_df in df.groupby("batter"):
        try:
            batter_id = int(batter_id)
        except Exception:
            continue

        total = grouped[grouped["batter"] == batter_id].sort_values(
            "pa",
            ascending=False,
        )

        if total.empty:
            continue

        base = total.iloc[0].to_dict()

        vs_l = batter_df[batter_df["p_throws"] == "L"]
        vs_r = batter_df[batter_df["p_throws"] == "R"]

        hr_vs_l = int((vs_l["events"] == "home_run").sum())
        hr_vs_r = int((vs_r["events"] == "home_run").sum())

        last_hr_l = None
        last_hr_r = None

        if hr_vs_l:
            last_hr_l = vs_l[vs_l["events"] == "home_run"]["game_date"].max()

        if hr_vs_r:
            last_hr_r = vs_r[vs_r["events"] == "home_run"]["game_date"].max()

        hitter_rows.append(
            {
                "batter_id": batter_id,
                "name": names.get(batter_id, f"MLBAM {batter_id}"),
                "position": positions.get(batter_id),
                "bat_side": base.get("stand"),
                "pa": int(safe_num(base.get("pa"))),
                "bbe": int(safe_num(base.get("bbe"))),
                "hard_hit_pct": round(safe_num(base.get("hard_hit_pct")), 3),
                "barrel_pct": round(safe_num(base.get("barrel_pct")), 3),
                "avg_ev": round(safe_num(base.get("avg_ev")), 1),
                "hr": int(safe_num(base.get("hr"))),
                "hr_vs_lhp": hr_vs_l,
                "hr_vs_rhp": hr_vs_r,
                "last_hr_vs_lhp": (
                    str(last_hr_l.date())
                    if last_hr_l is not None and not pd.isna(last_hr_l)
                    else None
                ),
                "last_hr_vs_rhp": (
                    str(last_hr_r.date())
                    if last_hr_r is not None and not pd.isna(last_hr_r)
                    else None
                ),
                "days_since_hr_vs_lhp": days_since(last_hr_l),
                "days_since_hr_vs_rhp": days_since(last_hr_r),
            }
        )

    return hitter_rows


def split_hr_score(hitter, pitcher_throw):
    pitcher_throw = str(pitcher_throw or "").upper()

    if pitcher_throw == "L":
        hrs = safe_num(hitter.get("hr_vs_lhp"))
        days = hitter.get("days_since_hr_vs_lhp")
    else:
        hrs = safe_num(hitter.get("hr_vs_rhp"))
        days = hitter.get("days_since_hr_vs_rhp")

    score = min(hrs * 12, 40)

    if days is not None:
        if days <= 7:
            score += 30
        elif days <= 14:
            score += 22
        elif days <= 30:
            score += 14
        elif days <= 60:
            score += 8

    return min(score, 70)


def hitter_sample_reliability(hitter, pitcher_throw=None):
    score = 100.0
    concerns = []

    bbe = safe_num(hitter.get("bbe"))
    pa = safe_num(hitter.get("pa"))

    if bbe <= 0:
        score -= 35.0
        concerns.append("hitter_batted_ball_sample_missing")
    elif bbe < 60:
        score -= 18.0
        concerns.append("hitter_batted_ball_sample_thin")
    elif bbe < 120:
        score -= 8.0
        concerns.append("hitter_batted_ball_sample_moderate")

    if pa <= 0:
        score -= 20.0
        concerns.append("hitter_pa_sample_missing")
    elif pa < 80:
        score -= 8.0
        concerns.append("hitter_pa_sample_thin")

    pitcher_throw = str(pitcher_throw or "").upper()
    if pitcher_throw not in {"L", "R"}:
        score -= 8.0
        concerns.append("pitcher_hand_missing")

    return {
        "score": round(max(0.0, min(100.0, score)), 1),
        "concerns": concerns,
    }


def hitter_hr_ability_score(hitter, pitcher_throw):
    barrel_score = centered_score(
        hitter.get("barrel_pct"),
        HITTER_BARREL_CENTER,
        HITTER_BARREL_HALF_RANGE,
    )
    hard_hit_score = centered_score(
        hitter.get("hard_hit_pct"),
        HITTER_HARD_HIT_CENTER,
        HITTER_HARD_HIT_HALF_RANGE,
    )
    ev_score = centered_score(
        hitter.get("avg_ev"),
        HITTER_AVG_EV_CENTER,
        HITTER_AVG_EV_HALF_RANGE,
    )

    pitcher_throw = str(pitcher_throw or "").upper()
    if pitcher_throw == "L":
        split_hrs = safe_num(hitter.get("hr_vs_lhp"))
    elif pitcher_throw == "R":
        split_hrs = safe_num(hitter.get("hr_vs_rhp"))
    else:
        split_hrs = 0.0

    split_power_score = centered_score(
        split_hrs,
        HITTER_SPLIT_HR_CENTER,
        HITTER_SPLIT_HR_HALF_RANGE,
    )

    score = (
        barrel_score * HITTER_BARREL_WEIGHT
        + hard_hit_score * HITTER_HARD_HIT_WEIGHT
        + ev_score * HITTER_AVG_EV_WEIGHT
        + split_power_score * HITTER_SPLIT_POWER_WEIGHT
    )

    return round(clamp_score(score), 1)


def hr_opportunity_score(
    *,
    pitcher_vulnerability,
    hitter_hr_ability,
    environment_score,
):
    score = (
        safe_num(pitcher_vulnerability) * OPPORTUNITY_PITCHER_WEIGHT
        + safe_num(hitter_hr_ability) * OPPORTUNITY_HITTER_WEIGHT
        + safe_num(environment_score) * OPPORTUNITY_ENVIRONMENT_WEIGHT
    )

    return round(clamp_score(score), 1)


def hitter_lineup_actionability(hitter, team_lineup):
    if team_lineup is None:
        return {
            "lineup_status": PlayerLineupStatus.UNKNOWN.value,
            "actionability": LineupActionability.SOURCE_UNKNOWN.value,
            "batting_order": None,
            "position": hitter.get("position"),
            "concerns": ["lineup_source_unknown"],
            "official_candidate": True,
        }

    lineup_player = team_lineup.player_status(hitter.get("batter_id"))
    concerns = []

    if lineup_player.lineup_status == PlayerLineupStatus.CONFIRMED_STARTER:
        actionability = LineupActionability.ACTIONABLE
        official_candidate = True
    elif lineup_player.lineup_status in {
        PlayerLineupStatus.BENCH,
        PlayerLineupStatus.NOT_LISTED,
    }:
        actionability = LineupActionability.NOT_STARTING
        official_candidate = False
        concerns.append("hitter_not_in_confirmed_lineup")
    elif team_lineup.status == GameLineupStatus.NOT_POSTED:
        actionability = LineupActionability.PENDING_LINEUP
        official_candidate = True
        concerns.append("lineup_not_posted")
    else:
        actionability = LineupActionability.SOURCE_UNKNOWN
        official_candidate = True
        concerns.append("lineup_status_unknown")

    return {
        "lineup_status": lineup_player.lineup_status.value,
        "actionability": actionability.value,
        "batting_order": lineup_player.batting_order,
        "position": lineup_player.position or hitter.get("position"),
        "concerns": concerns,
        "official_candidate": official_candidate,
    }


def build_target_score(hitter, attack_side, pitcher_throw, opportunity_score):
    barrel = safe_num(hitter.get("barrel_pct")) * 100
    hard_hit = safe_num(hitter.get("hard_hit_pct")) * 100
    ev = max(safe_num(hitter.get("avg_ev")) - 86, 0) * 3
    hr_split = split_hr_score(hitter, pitcher_throw)
    side_fit = 100 if side_matches(hitter.get("bat_side"), attack_side) else 50
    opp = safe_num(opportunity_score)

    score = (
        barrel * 1.25
        + hard_hit * 0.55
        + ev * 0.35
        + hr_split * 0.75
        + side_fit * 0.18
        + opp * 0.15
    )

    return round(max(0, min(100, score)), 1)


def attach_target_hitters_to_pitchers(
    pitchers,
    season_statcast_df=None,
    lineup_service=None,
):
    enriched = []

    roster_cache = {}

    for item in pitchers:
        offense = item.get("opponent")
        team_id = item.get("opponent_team_id")
        from engine.hitters.team_abbreviations import TEAM_ABBR
        team_abbr = item.get("opponent_abbr") or TEAM_ABBR.get(offense)
        attack_side = item.get("target_side")
        pitcher_throw = item.get("pitcher_throw")
        opportunity_score = item.get("bomb_score") or 0
        game_id = item.get("game_pk")
        lineup_state = (
            lineup_service.get_game_lineup(game_id)
            if lineup_service and game_id
            else None
        )
        team_lineup = (
            lineup_state.team_lineup(team_id)
            if lineup_state is not None
            else None
        )

        if team_id not in roster_cache:
            roster_cache[team_id] = fetch_active_roster(team_id)

        roster_players = roster_cache.get(team_id, [])

        hitters = build_hitter_profiles(
            statcast_df=season_statcast_df,
            team_abbr=team_abbr,
            roster_players=roster_players,
        )

        for hitter in hitters:
            hitter["team"] = offense
            hitter["hitter_hr_ability"] = hitter_hr_ability_score(
                hitter,
                pitcher_throw,
            )
            hitter_reliability = hitter_sample_reliability(
                hitter,
                pitcher_throw,
            )
            hitter["hitter_reliability"] = hitter_reliability["score"]
            hitter["hitter_reliability_concerns"] = hitter_reliability[
                "concerns"
            ]
            hitter["hr_opportunity_score"] = hr_opportunity_score(
                pitcher_vulnerability=item.get("pitcher_vulnerability")
                or item.get("pitcher_risk"),
                hitter_hr_ability=hitter["hitter_hr_ability"],
                environment_score=item.get("environment_score")
                or item.get("park_score"),
            )
            hitter["reliability"] = min(
                safe_num(item.get("bomb_reliability"), 100.0),
                hitter["hitter_reliability"],
            )
            lineup_actionability = hitter_lineup_actionability(
                hitter,
                team_lineup,
            )
            hitter["lineup_status"] = lineup_actionability["lineup_status"]
            hitter["lineup_actionability"] = lineup_actionability[
                "actionability"
            ]
            hitter["batting_order"] = lineup_actionability["batting_order"]
            hitter["position"] = lineup_actionability["position"]
            hitter["lineup_concerns"] = lineup_actionability["concerns"]
            hitter["official_candidate"] = lineup_actionability[
                "official_candidate"
            ]
            hitter["target_score"] = build_target_score(
                hitter=hitter,
                attack_side=attack_side,
                pitcher_throw=pitcher_throw,
                opportunity_score=opportunity_score,
            )
            hitter["stars"] = star_rating(hitter["target_score"])

        ranked_hitters = sorted(
            hitters,
            key=lambda x: (
                x["hr_opportunity_score"],
                x["hitter_hr_ability"],
                x["target_score"],
            ),
            reverse=True,
        )
        target_ranked_hitters = sorted(
            hitters,
            key=lambda x: (
                x["target_score"],
                x["hr_opportunity_score"],
                x["hitter_hr_ability"],
            ),
            reverse=True,
        )

        item["diagnostic_hitters"] = ranked_hitters[:5]
        item["top_hitters"] = [
            hitter
            for hitter in target_ranked_hitters
            if hitter.get("official_candidate", True)
        ][:5]

        if lineup_state is not None:
            item["lineup_state"] = lineup_state.status.value
            item["lineup_game_status"] = lineup_state.game_status
            item["lineup_source"] = lineup_state.source
            item["lineup_retrieved_at"] = lineup_state.retrieved_at.isoformat()
            item["lineup_freshness_seconds"] = round(
                lineup_state.freshness_seconds,
                1,
            )
            item["lineup_is_stale"] = lineup_state.is_stale
            item["lineup_concerns"] = list(
                lineup_state.concerns
                + ((team_lineup.concerns if team_lineup else ()) or ())
            )
            item["away_lineup_starters"] = (
                len(lineup_state.away_lineup.starters)
                if lineup_state.away_lineup
                else 0
            )
            item["home_lineup_starters"] = (
                len(lineup_state.home_lineup.starters)
                if lineup_state.home_lineup
                else 0
            )
        else:
            item["lineup_state"] = GameLineupStatus.UNKNOWN.value
            item["lineup_concerns"] = ["lineup_service_unavailable"]

        if item["top_hitters"]:
            best_hitter = item["top_hitters"][0]
            item["recommended_hitter"] = best_hitter.get("name")
            item["hitter_hr_ability"] = best_hitter.get(
                "hitter_hr_ability"
            )
            item["hr_opportunity_score"] = best_hitter.get(
                "hr_opportunity_score"
            )
            item["opportunity_reliability"] = best_hitter.get(
                "reliability"
            )
            item["hitter_reliability_concerns"] = best_hitter.get(
                "hitter_reliability_concerns",
                [],
            )
            item["lineup_status"] = best_hitter.get("lineup_status")
            item["lineup_actionability"] = best_hitter.get(
                "lineup_actionability"
            )
            item["batting_order"] = best_hitter.get("batting_order")
            item["recommended_hitter_position"] = best_hitter.get("position")
            item["recommended_hitter_lineup_concerns"] = best_hitter.get(
                "lineup_concerns",
                [],
            )
            item["bomb_score"] = best_hitter["hr_opportunity_score"]
        elif ranked_hitters:
            item["lineup_actionability"] = LineupActionability.NOT_STARTING.value

        enriched.append(item)

    return enriched

from datetime import datetime

import pandas as pd

from engine.lineups.mlb_roster import (
    fetch_active_roster,
    roster_id_set,
    roster_name_map,
    roster_position_map,
)
from engine.mlb import offense


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


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
    launch_angle = pd.to_numeric(df["launch_angle"], errors="coerce").fillna(-999)

    df["hard_hit"] = (launch_speed >= 95).astype(int)

    df["barrel"] = (
        ((launch_speed >= 98) & (launch_angle.between(26, 30)))
        |
        ((launch_speed >= 95) & (launch_angle.between(8, 50)))
    ).astype(int)

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
    df = df[df["batting_team"] == team_abbr].copy()

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


def attach_target_hitters_to_pitchers(pitchers, season_statcast_df=None):
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
            hitter["target_score"] = build_target_score(
                hitter=hitter,
                attack_side=attack_side,
                pitcher_throw=pitcher_throw,
                opportunity_score=opportunity_score,
            )
            hitter["stars"] = star_rating(hitter["target_score"])

        item["top_hitters"] = sorted(
            hitters,
            key=lambda x: x["target_score"],
            reverse=True,
        )[:5]

        enriched.append(item)

    return enriched

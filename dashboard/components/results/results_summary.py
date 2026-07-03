import pandas as pd
import streamlit as st


def calculate_summary(rows):
    if not rows:
        return {
            "tracked": 0,
            "graded": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "win_rate": 0,
        }

    df = pd.DataFrame(rows)

    if "result" not in df.columns:
        return {
            "tracked": len(df),
            "graded": 0,
            "wins": 0,
            "losses": 0,
            "pushes": 0,
            "win_rate": 0,
        }

    graded = df[df["result"].isin(["WIN", "LOSS", "PUSH"])].copy()
    wins = len(graded[graded["result"] == "WIN"])
    losses = len(graded[graded["result"] == "LOSS"])
    pushes = len(graded[graded["result"] == "PUSH"])

    decisions = wins + losses
    win_rate = round((wins / decisions) * 100, 1) if decisions else 0

    return {
        "tracked": len(df),
        "graded": len(graded),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": win_rate,
    }


def render_results_summary(rows):
    summary = calculate_summary(rows)

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Tracked", summary["tracked"])
    c2.metric("Graded", summary["graded"])
    c3.metric("Wins", summary["wins"])
    c4.metric("Losses", summary["losses"])
    c5.metric("Win Rate", f"{summary['win_rate']}%")
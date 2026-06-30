import streamlit as st

from components.module_dashboard import render_module_dashboard


def render_mlb():
    render_module_dashboard(
        icon="⚾",
        title="MLB Command Center",
        subtitle="The flagship league is next into the SharpStack engine.",
        badge="NEXT MAJOR DATA EPIC",
        sections=[
            {
                "title": "Foundation",
                "items": [
                    ("Team Logo System", "complete"),
                    ("Team Colors", "complete"),
                    ("Shared UI Components", "complete"),
                    ("Dashboard Ready", "complete"),
                ],
            },
            {
                "title": "Data Pipeline",
                "items": [
                    ("Schedule Ingestion", "next"),
                    ("Probable Pitchers", "next"),
                    ("Pitcher Stats", "planned"),
                    ("Team Records", "planned"),
                ],
            },
            {
                "title": "Market Intelligence",
                "items": [
                    ("Live Odds", "planned"),
                    ("Implied Probability", "planned"),
                    ("Line Movement", "planned"),
                    ("Consensus Pricing", "planned"),
                ],
            },
        ],
    )


def render_kbo():
    render_module_dashboard(
        icon="🇰🇷",
        title="KBO Analytics",
        subtitle="Current production league and SharpStack validation environment.",
        badge="LIVE ENGINE",
        sections=[
            {
                "title": "Current Capabilities",
                "items": [
                    ("Schedule Loading", "complete"),
                    ("Pitcher Profiles", "complete"),
                    ("Model Scoring", "complete"),
                    ("JSON Output", "complete"),
                ],
            },
            {
                "title": "Enhancements",
                "items": [
                    ("Odds Feed", "next"),
                    ("Weather", "planned"),
                    ("Bullpen Intelligence", "planned"),
                    ("Line Movement", "planned"),
                ],
            },
        ],
    )


def render_bomb_lab():
    render_module_dashboard(
        icon="💣",
        title="Bomb Lab",
        subtitle="Long ball intelligence for home run hunting.",
        badge="AFTER MLB FOUNDATION",
        sections=[
            {
                "title": "Core Inputs",
                "items": [
                    ("Batter Power Profiles", "planned"),
                    ("Pitcher HR Risk", "planned"),
                    ("Barrel Trends", "planned"),
                    ("Platoon Splits", "planned"),
                ],
            },
            {
                "title": "Boosters",
                "items": [
                    ("Weather Boost", "planned"),
                    ("Park Factor", "planned"),
                    ("Lineup Context", "planned"),
                    ("Odds Overlay", "planned"),
                ],
            },
        ],
    )


def render_props():
    render_module_dashboard(
        icon="🎯",
        title="Props Lab",
        subtitle="Player prop research and edge detection.",
        badge="FUTURE MODULE",
        sections=[
            {
                "title": "Markets",
                "items": [
                    ("Strikeouts", "planned"),
                    ("Hits", "planned"),
                    ("Total Bases", "planned"),
                    ("Home Runs", "planned"),
                    ("Pitching Outs", "planned"),
                ],
            },
            {
                "title": "Model Inputs",
                "items": [
                    ("Player Form", "planned"),
                    ("Opponent Matchup", "planned"),
                    ("Odds Feed", "planned"),
                    ("Historical Hit Rate", "planned"),
                ],
            },
        ],
    )


def render_hall():
    render_module_dashboard(
        icon="🏆",
        title="Hall of Fame",
        subtitle="Historical SharpStack greatness and model performance.",
        badge="PERFORMANCE TRACKING",
        sections=[
            {
                "title": "Leaderboards",
                "items": [
                    ("Biggest Edge", "planned"),
                    ("Highest Confidence", "planned"),
                    ("Largest Upset", "planned"),
                    ("Longest Win Streak", "planned"),
                ],
            },
            {
                "title": "Analytics",
                "items": [
                    ("Lifetime ROI", "planned"),
                    ("Win Rate by Confidence", "planned"),
                    ("Closing Line Value", "planned"),
                    ("Profit by Market", "planned"),
                ],
            },
        ],
    )


def render_settings():
    render_module_dashboard(
        icon="⚙",
        title="Control Center",
        subtitle="Configure SharpStack behavior, integrations, and defaults.",
        badge="ADMIN AREA",
        sections=[
            {
                "title": "Configuration",
                "items": [
                    ("Theme", "planned"),
                    ("League Defaults", "planned"),
                    ("Odds Provider", "planned"),
                    ("Model Weights", "planned"),
                ],
            },
            {
                "title": "Integrations",
                "items": [
                    ("Discord Alerts", "planned"),
                    ("Export Settings", "planned"),
                    ("Experimental Features", "planned"),
                    ("Notification Rules", "planned"),
                ],
            },
        ],
    )

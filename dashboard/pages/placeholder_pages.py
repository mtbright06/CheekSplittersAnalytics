import streamlit as st


def render_feature_grid(items):
    cols = st.columns(3)

    for index, item in enumerate(items):
        with cols[index % 3]:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="feature-icon">{item["icon"]}</div>
                    <div class="feature-title">{item["title"]}</div>
                    <div class="feature-body">{item["body"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_mlb():
    st.markdown('<div class="section-title">⚾ MLB Command Center</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Daily MLB card, pitchers to attack, market edges, and Bomb Lab integrations.</div>',
        unsafe_allow_html=True,
    )

    render_feature_grid([
        {"icon": "📅", "title": "Daily Slate", "body": "Games, probable starters, venues, and start times."},
        {"icon": "🎯", "title": "Best Bets", "body": "Moneyline, first five, totals, props, and value spots."},
        {"icon": "💣", "title": "Bomb Lab Feed", "body": "Top HR candidates linked directly to matchup context."},
        {"icon": "🌬️", "title": "Weather Edge", "body": "Wind, temperature, park factors, and run environment."},
        {"icon": "📈", "title": "Market Intel", "body": "Odds movement, line shopping, and closing-line value."},
        {"icon": "🧠", "title": "Model Notes", "body": "Plain-English explanation of why the model likes a play."},
    ])


def render_kbo():
    st.markdown('<div class="section-title">🇰🇷 KBO Command Center</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Live KBO schedule, starting pitchers, pitcher profiles, and betting card.</div>',
        unsafe_allow_html=True,
    )

    render_feature_grid([
        {"icon": "✅", "title": "Live Starters", "body": "Starter names, records, ERA, WHIP, K/9, BB/9, HR/9."},
        {"icon": "🛡️", "title": "No-Slate Guard", "body": "No fake picks when starters are unavailable."},
        {"icon": "📊", "title": "Pitching Edge", "body": "Model compares ERA, traffic, strikeouts, walks, and HR suppression."},
        {"icon": "🔥", "title": "Daily Card", "body": "Best bet, confidence, edge, signals, and reasons."},
        {"icon": "🧪", "title": "Data Lab", "body": "Parser tests and source validation tools."},
        {"icon": "🚧", "title": "Next Up", "body": "Live offense, bullpen, recent form, and odds."},
    ])


def render_bomb_lab():
    st.markdown('<div class="section-title">💣 Bomb Lab</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Home run targets, pitch mix matchups, weather boosts, and value bombs.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="lab-hero">
            <div class="lab-title">Today’s Bomb Lab</div>
            <div class="lab-subtitle">Baseball Savant if it was built by degenerate gamblers.</div>
            <div class="lab-badge">Coming Soon</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_feature_grid([
        {"icon": "💪", "title": "Hard Contact", "body": "Barrel%, hard-hit%, bat speed, blast contact, and recent power."},
        {"icon": "🎯", "title": "Pitch Mix Fit", "body": "Hitter strengths against today’s pitcher arsenal."},
        {"icon": "🌬️", "title": "Wind Boost", "body": "Direction, speed, park orientation, and HR carry."},
        {"icon": "🏟️", "title": "Park Factors", "body": "Ballpark-specific power environment by handedness."},
        {"icon": "💰", "title": "Odds Value", "body": "Best HR probability versus sportsbook price."},
        {"icon": "🧾", "title": "Official Card", "body": "Final 3–5 HR bets with confidence and reasons."},
    ])


def render_props():
    st.markdown('<div class="section-title">🎯 Props Lab</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Player props, strikeouts, hits, bases, and matchup filters.</div>',
        unsafe_allow_html=True,
    )

    render_feature_grid([
        {"icon": "⚾", "title": "Batter Props", "body": "Hits, total bases, RBIs, runs, and home runs."},
        {"icon": "🔥", "title": "Pitcher Props", "body": "Strikeouts, outs recorded, walks, and earned runs."},
        {"icon": "📉", "title": "Line Shopping", "body": "Compare books and find the best number."},
        {"icon": "🧠", "title": "Prop Model", "body": "Projection versus price, with explainable factors."},
        {"icon": "🚦", "title": "Risk Tags", "body": "Volatility, matchup risk, playing-time risk, and weather risk."},
        {"icon": "🧾", "title": "Prop Card", "body": "Official daily props ranked by edge."},
    ])


def render_hall():
    st.markdown('<div class="section-title">🏆 Hall of Fame</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Big wins, brutal misses, bankroll milestones, and legendary cheek splits.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="hof-card">
            <div class="hof-title">Today’s Entry Candidate</div>
            <div class="hof-big">Two 3-leg HR parlays hit</div>
            <div class="hof-muted">Bankroll momentum: violently upward.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_feature_grid([
        {"icon": "💰", "title": "Big Wins", "body": "Track winning tickets, profit, sport, market, and model signal."},
        {"icon": "🧯", "title": "Bad Beats", "body": "Log losses and what the model missed."},
        {"icon": "📈", "title": "Bankroll Milestones", "body": "Track account balances and growth over time."},
        {"icon": "🧠", "title": "Lessons Learned", "body": "Turn every bet into model feedback."},
        {"icon": "🔥", "title": "Cheek Splitters", "body": "The bets worthy of legend status."},
        {"icon": "📊", "title": "Performance", "body": "ROI, hit rate, CLV, sport, market, and confidence tier."},
    ])


def render_settings():
    st.markdown('<div class="section-title">⚙ Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="muted">Model weights, sportsbook preferences, bankroll settings, and display options.</div>',
        unsafe_allow_html=True,
    )

    render_feature_grid([
        {"icon": "🎚️", "title": "Model Weights", "body": "Tune pitching, offense, bullpen, recent form, and market factors."},
        {"icon": "🏦", "title": "Sportsbooks", "body": "FanDuel, Fanatics, DraftKings, BetMGM, Caesars, and more."},
        {"icon": "💵", "title": "Bankroll", "body": "Track balances, bet sizing, staking style, and daily limits."},
        {"icon": "🎨", "title": "Theme", "body": "Brand assets, logo, mascot, colors, and display mode."},
        {"icon": "🧪", "title": "Debug", "body": "Parser tests, data health checks, and source status."},
        {"icon": "🚀", "title": "Release Info", "body": "Version, sprint history, and roadmap."},
    ])

import streamlit as st

from version import VERSION, BUILD, ENGINE


def _games(card):
    return card.get("games", []) if card else []


def _playable(games):
    return len([g for g in games if (g.get("model", {}).get("edge") or 0) >= 5])


def _best_edge(games):
    return max([g.get("model", {}).get("edge") or 0 for g in games], default=0)


def _avg_edge(games):
    edges = [g.get("model", {}).get("edge") or 0 for g in games]
    if not edges:
        return 0
    return sum(edges) / len(edges)


def render_sidebar(card):
    games = _games(card)

    st.sidebar.markdown("## SHARPSTACK")
    st.sidebar.caption("Command Center")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🍑 Splitter")
    st.sidebar.success("Online")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Today’s Slate")

    st.sidebar.metric("Sport", card.get("sport") if card else "N/A")
    st.sidebar.metric("Games", len(games))
    st.sidebar.metric("Playable", _playable(games))
    st.sidebar.metric("Best Edge", f"{_best_edge(games):.1f}%")
    st.sidebar.metric("Avg Edge", f"{_avg_edge(games):.1f}%")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Build")

    st.sidebar.metric("Version", VERSION)
    st.sidebar.metric("Build", BUILD)
    st.sidebar.caption(ENGINE)

    if card:
        st.sidebar.caption(f"Generated: {card.get('generated_at')}")

    st.sidebar.markdown("---")
    st.sidebar.write("🔥 Status: Operational")
    st.sidebar.write("🍺 Beer: Recommended")

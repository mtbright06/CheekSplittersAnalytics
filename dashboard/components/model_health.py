import streamlit as st


def health_row(label, status):

    icon = "🟢" if status else "⚫"

    st.markdown(
        f"{icon} **{label}**"
    )


def render_model_health():

    st.markdown(
        "### Model Health"
    )

    health_row("Pitching", True)
    health_row("Offense", True)
    health_row("Bullpen", True)
    health_row("Recent Form", False)
    health_row("Weather", False)
    health_row("Odds Feed", False)
    health_row("Bomb Lab", False)

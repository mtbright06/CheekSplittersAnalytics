from __future__ import annotations

import html


STATUS_PILL_TONES = {
    "accent",
    "danger",
    "neutral",
    "success",
    "warning",
}

STATUS_PILL_SIZES = {
    "compact",
}

STATUS_TONE_BY_LABEL = {
    "ACTIVE": "success",
    "BET": "success",
    "COMPLETE": "success",
    "LEAN": "warning",
    "LOSS": "danger",
    "MODEL ONLY": "neutral",
    "PASS": "neutral",
    "PENDING": "warning",
    "PUSH": "warning",
    "REAL MARKET": "accent",
    "WIN": "success",
}


def status_pill_tone(label: str, tone: str = "neutral") -> str:
    """Map known status labels to restrained semantic tones."""

    normalized = str(label or "").strip().upper()
    requested_tone = str(tone or "neutral").strip().lower()

    if requested_tone != "neutral":
        return (
            requested_tone
            if requested_tone in STATUS_PILL_TONES
            else "neutral"
        )

    return STATUS_TONE_BY_LABEL.get(normalized, "neutral")


def status_pill_html(
    label: str,
    tone: str = "neutral",
    *,
    size: str = "compact",
) -> str:
    """Return safe inline HTML for a compact SharpStack status pill."""

    safe_size = (
        size
        if size in STATUS_PILL_SIZES
        else "compact"
    )
    safe_tone = status_pill_tone(label, tone)
    display_label = str(label or "UNKNOWN").strip().upper()

    return (
        "<span class='ss-status-pill "
        f"ss-status-pill--{safe_size} "
        f"ss-status-pill--{safe_tone}'>"
        f"{html.escape(display_label)}</span>"
    )


def render_status_pill(
    label: str,
    tone: str = "neutral",
    *,
    size: str = "compact",
) -> None:
    """Render a compact SharpStack status pill in Streamlit."""

    import streamlit as st

    st.markdown(
        status_pill_html(
            label,
            tone,
            size=size,
        ),
        unsafe_allow_html=True,
    )

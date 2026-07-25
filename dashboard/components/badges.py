import html


def play_grade(edge):
    if edge is None:
        return "NO DATA"

    if edge >= 10:
        return "CHEEK RIPPER 🔥"

    if edge >= 7:
        return "STRONG PLAY"

    if edge >= 5:
        return "PLAYABLE"

    if edge >= 2:
        return "LEAN"

    return "PASS"


def play_badge_class(edge):
    if edge is None:
        return "badge"

    if edge >= 7:
        return "badge badge-green"

    if edge >= 2:
        return "badge badge-gold"

    return "badge"


def recommendation_badge_class(recommendation):
    """Return the shared hero-badge treatment for an existing recommendation."""
    label = str(recommendation or "").upper()

    if "CHEEK RIPPER" in label or "STRONG PLAY" in label:
        return "badge recommendation-badge recommendation-strong"

    if "PLAYABLE" in label:
        return "badge recommendation-badge recommendation-playable"

    if "LEAN" in label:
        return "badge recommendation-badge recommendation-lean"

    return "badge recommendation-badge recommendation-neutral"


def recommendation_stars(recommendation, *, model_only=False, fallback=""):
    """Format presentation stars without changing a recommendation itself."""
    if not model_only:
        return fallback

    label = str(recommendation or "").upper()

    if "CHEEK RIPPER" in label or "STRONG PLAY" in label:
        return "★★★★★"

    if "PLAYABLE" in label:
        return "★★★★☆"

    if "LEAN" in label:
        return "★★★☆☆"

    return "★☆☆☆☆"


def recommendation_badge_html(
    recommendation,
    *,
    model_only=False,
    fallback_stars="",
):
    """Render the shared hero badge used by KBO dashboard and Best Bets cards."""
    stars = recommendation_stars(
        recommendation,
        model_only=model_only,
        fallback=fallback_stars,
    )
    stars_html = (
        f" <span class='recommendation-star-count'>{stars}</span>"
        if stars
        else ""
    )
    return (
        f"<span class='{recommendation_badge_class(recommendation)}'>"
        f"{html.escape(str(recommendation or 'PASS'))}{stars_html}</span>"
    )


def market_value_badge_html(label, tone):
    """Render the presentation-only SSRP value classification badge."""
    normalized_tone = str(tone or "unavailable").strip().lower()
    icon = {
        "elite_value": "💎",
        "strong_value": "💰",
        "positive_value": "📈",
        "fair_price": "➖",
        "market_premium": "⚠️",
        "heavy_premium": "🚫",
        "unavailable": "•",
    }.get(normalized_tone, "•")
    css_tone = normalized_tone if normalized_tone in {
        "elite_value",
        "strong_value",
        "positive_value",
        "fair_price",
        "market_premium",
        "heavy_premium",
        "unavailable",
    } else "unavailable"
    rendered_label = label or "VALUE UNAVAILABLE"

    return (
        "<span class='badge market-value-badge "
        f"market-value-{css_tone}'>"
        f"{icon} {html.escape(str(rendered_label))}</span>"
    )


def status_badge(label, status="neutral"):
    css = {
        "good": "badge badge-green",
        "warning": "badge badge-gold",
        "bad": "badge badge-red",
        "neutral": "badge",
    }.get(status, "badge")

    return f"<span class='{css}'>{label}</span>"

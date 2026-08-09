from __future__ import annotations

from engine.mlb.totals.explanation import (
    ExplanationItem,
    TotalsExplanation,
)


def render_totals_explanation(
    explanation: TotalsExplanation,
    *,
    include_context: bool = False,
) -> str:
    lines = [explanation.summary]

    def emit(title: str, items: list[ExplanationItem]):
        if not items:
            return

        lines.append("")
        lines.append(title)

        for item in sorted(items, key=lambda x: x.priority):
            metric = ""

            if item.metric and item.value is not None:
                if item.unit:
                    metric = f"{item.metric}: {item.value} {item.unit}"
                else:
                    metric = f"{item.metric}: {item.value}"

            if metric:
                lines.append(f"- {item.title} ({metric})")
            else:
                lines.append(f"- {item.title}")

            lines.append(f"  {item.detail}")

    emit("Market", explanation.market)
    emit("Strengths", explanation.strengths)
    emit("Risks", explanation.risks)

    if include_context:
        emit("Context", explanation.context)

    return "\n".join(lines)


def render_totals_explanation_compact(
    explanation: TotalsExplanation,
) -> str:
    pieces = [explanation.summary]

    items = (
        explanation.market
        + explanation.strengths
        + explanation.risks
    )

    seen = set()

    for item in sorted(items, key=lambda x: x.priority):
        if item.id in seen:
            continue

        seen.add(item.id)

        pieces.append(item.title)

        if len(seen) == 3:
            break

    return " | ".join(pieces)

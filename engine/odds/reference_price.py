from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from engine.odds.best_line import quote_to_dict


class ReferencePriceResolver(Protocol):
    def resolve_quote(
        self,
        quote: dict[str, Any],
        league: str,
    ) -> Any: ...


@dataclass(frozen=True)
class ReferenceQuoteResolution:
    current_quote: dict[str, Any]
    reference_quote: dict[str, Any] | None
    reference_status: str
    reference_fields: dict[str, Any]


def resolve_reference_quote(
    current_quote: Any,
    *,
    league: str,
    resolver: ReferencePriceResolver | None,
) -> ReferenceQuoteResolution:
    """Keep current odds intact while producing the locked SSRP edge input."""
    current = quote_to_dict(current_quote)
    current_fields = {
        "current_price": current.get("american_odds"),
        "current_book": current.get("sportsbook"),
        "current_captured_at": current.get("last_updated")
        or current.get("updated_at"),
    }

    if resolver is None:
        return ReferenceQuoteResolution(
            current,
            None,
            "REFERENCE_STORE_UNAVAILABLE",
            current_fields,
        )

    result = resolver.resolve_quote(current, league)
    status = getattr(result, "status", "REFERENCE_STORE_UNAVAILABLE")
    reference = getattr(result, "reference", None)
    fields = {**current_fields, **(reference or {}), "reference_status": status}

    if status != "LOCKED" or not reference:
        return ReferenceQuoteResolution(current, None, status, fields)

    edge_quote = {
        **current,
        "american_odds": reference["reference_price"],
        "implied_probability": reference["reference_implied_probability"],
        "sportsbook": reference["reference_book"],
        "last_updated": reference["reference_captured_at"],
        "source": "sharpstack_reference_price",
        "is_live": False,
    }
    return ReferenceQuoteResolution(current, edge_quote, status, fields)

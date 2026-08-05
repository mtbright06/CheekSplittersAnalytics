from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Iterable

from engine.core.recommendation import (
    Recommendation,
    is_verified_pregame_recommendation,
)
from engine.core.ranking import stable_ranking_identity


class RecommendationRegistry:
    def __init__(
        self,
        recommendations: (
            Iterable[Recommendation] | None
        ) = None,
    ):
        self._recommendations: list[
            Recommendation
        ] = []

        if recommendations:
            self.extend(recommendations)

    def add(
        self,
        recommendation: Recommendation,
    ) -> None:
        if not isinstance(
            recommendation,
            Recommendation,
        ):
            raise TypeError(
                "Registry only accepts "
                "Recommendation objects."
            )

        if not is_verified_pregame_recommendation(
            recommendation
        ):
            return

        existing_index = self._find_index(
            recommendation
        )

        if existing_index is None:
            self._recommendations.append(
                recommendation
            )
        else:
            self._recommendations[
                existing_index
            ] = recommendation

    def extend(
        self,
        recommendations: Iterable[
            Recommendation
        ],
    ) -> None:
        for recommendation in recommendations:
            self.add(recommendation)

    def _find_index(
        self,
        candidate: Recommendation,
    ) -> int | None:
        for index, existing in enumerate(
            self._recommendations
        ):
            same_event = (
                str(existing.event_id)
                == str(candidate.event_id)
            )

            same_market = (
                existing.market
                == candidate.market
            )

            same_selection = (
                existing.selection.lower()
                == candidate.selection.lower()
            )

            same_league = (
                existing.league
                == candidate.league
            )

            if (
                same_event
                and same_market
                and same_selection
                and same_league
            ):
                return index

        return None

    def all(
        self,
    ) -> list[Recommendation]:
        return list(
            self._recommendations
        )

    def filter(
        self,
        *,
        sport: str | None = None,
        league: str | None = None,
        market: str | None = None,
        recommendation: str | None = None,
        actionable_only: bool = False,
        real_market_only: bool = False,
        status: str | None = None,
    ) -> list[Recommendation]:
        results = self._recommendations

        if sport:
            sport_value = sport.upper()

            results = [
                item
                for item in results
                if item.sport
                == sport_value
            ]

        if league:
            league_value = league.upper()

            results = [
                item
                for item in results
                if item.league
                == league_value
            ]

        if market:
            market_value = market.lower()

            results = [
                item
                for item in results
                if item.market
                == market_value
            ]

        if recommendation:
            recommendation_value = (
                recommendation.upper()
            )

            results = [
                item
                for item in results
                if item.recommendation
                == recommendation_value
            ]

        if actionable_only:
            results = [
                item
                for item in results
                if item.actionable
            ]

        if real_market_only:
            results = [
                item
                for item in results
                if item.real_market_loaded
            ]

        if status:
            status_value = status.lower()

            results = [
                item
                for item in results
                if item.status.lower()
                == status_value
            ]

        return list(results)

    def ranked(
        self,
        *,
        limit: int | None = None,
        actionable_only: bool = False,
        real_market_only: bool = False,
        sport: str | None = None,
        league: str | None = None,
        market: str | None = None,
    ) -> list[Recommendation]:
        results = self.filter(
            sport=sport,
            league=league,
            market=market,
            actionable_only=(
                actionable_only
            ),
            real_market_only=(
                real_market_only
            ),
        )

        results.sort(
            key=lambda item: (
                item.ranking_score,
                item.hammer_score,
                stable_ranking_identity(item),
            ),
            reverse=True,
        )

        if limit is not None:
            return results[:limit]

        return results

    def best(
        self,
        **filters,
    ) -> Recommendation | None:
        results = self.ranked(
            limit=1,
            **filters,
        )

        return (
            results[0]
            if results
            else None
        )

    def best_moneyline(
        self,
        *,
        league: str | None = None,
        real_market_only: bool = False,
    ) -> Recommendation | None:
        return self.best(
            league=league,
            market="moneyline",
            actionable_only=True,
            real_market_only=(
                real_market_only
            ),
        )

    def best_total(
        self,
        *,
        league: str | None = None,
        real_market_only: bool = False,
    ) -> Recommendation | None:
        return self.best(
            league=league,
            market="total",
            actionable_only=True,
            real_market_only=(
                real_market_only
            ),
        )

    def best_first5(
        self,
        *,
        league: str | None = None,
        real_market_only: bool = False,
    ) -> Recommendation | None:
        return self.best(
            league=league,
            market="first5_moneyline",
            actionable_only=True,
            real_market_only=(
                real_market_only
            ),
        )

    def best_nrfi(
        self,
        *,
        league: str | None = None,
        real_market_only: bool = False,
    ) -> Recommendation | None:
        return self.best(
            league=league,
            market="nrfi",
            actionable_only=True,
            real_market_only=(
                real_market_only
            ),
        )

    def best_home_run(
        self,
        *,
        league: str | None = None,
        real_market_only: bool = False,
    ) -> Recommendation | None:
        return self.best(
            league=league,
            market="home_run",
            actionable_only=True,
            real_market_only=(
                real_market_only
            ),
        )

    def summary(self) -> dict:
        all_rows = self._recommendations

        return {
            "recommendations": len(
                all_rows
            ),
            "actionable": len(
                [
                    item
                    for item in all_rows
                    if item.actionable
                ]
            ),
            "real_market": len(
                [
                    item
                    for item in all_rows
                    if item.real_market_loaded
                ]
            ),
            "model_only": len(
                [
                    item
                    for item in all_rows
                    if not item.real_market_loaded
                ]
            ),
            "hammers": len(
                [
                    item
                    for item in all_rows
                    if item.recommendation
                    == "HAMMER"
                ]
            ),
            "bets": len(
                [
                    item
                    for item in all_rows
                    if item.recommendation
                    == "BET"
                ]
            ),
            "leans": len(
                [
                    item
                    for item in all_rows
                    if item.recommendation
                    == "LEAN"
                ]
            ),
            "sports": sorted(
                {
                    item.sport
                    for item in all_rows
                    if item.sport
                }
            ),
            "leagues": sorted(
                {
                    item.league
                    for item in all_rows
                    if item.league
                }
            ),
            "markets": sorted(
                {
                    item.market
                    for item in all_rows
                    if item.market
                }
            ),
        }

    def to_dict(self) -> dict:
        ranked_rows = self.ranked()

        return {
            "type": (
                "recommendation_registry"
            ),
            "version": "1.0.0",
            "generated_at": (
                datetime.now().isoformat(
                    timespec="seconds"
                )
            ),
            "summary": self.summary(),
            "recommendations": [
                item.to_dict()
                for item in ranked_rows
            ],
        }

    def save(
        self,
        path: Path,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                self.to_dict(),
                file,
                indent=2,
            )

    @classmethod
    def load(
        cls,
        path: Path,
    ) -> "RecommendationRegistry":
        if not path.exists():
            return cls()

        try:
            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return cls()

        rows = data.get(
            "recommendations",
            [],
        )

        recommendations = [
            Recommendation.from_dict(row)
            for row in rows
            if isinstance(row, dict)
        ]

        return cls(recommendations)

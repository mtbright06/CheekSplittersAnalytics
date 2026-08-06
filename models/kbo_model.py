from engine.edge import EdgeCalculator
from engine.confidence import ConfidenceEngine

from loaders.pitcher_loader import PitcherLoader

from models.model_result import ModelResult

from calculators.mock_odds import MockOddsCalculator
from calculators.starting_pitching import StartingPitchingCalculator
from calculators.offense import OffenseCalculator
from calculators.bullpen import BullpenCalculator
from calculators.recent_form import RecentFormCalculator


class KBOModel:

    MODEL_SCORE_MINIMUM = 42.4
    MODEL_SCORE_MAXIMUM = 59.6

    def __init__(self):

        self.odds = MockOddsCalculator()

        self.calculators = [
            StartingPitchingCalculator(),
            OffenseCalculator(),
            BullpenCalculator(),
            RecentFormCalculator(),
        ]

    def score(self, games):

        scored_games = []

        for i, game in enumerate(games):

            self.odds.apply(game, i)

            PitcherLoader.load(game)

            if self._should_skip_game(game):
                continue

            result = ModelResult()

            result.market = "Moneyline"

            weighted_score = 0

            for calculator in self.calculators:

                score = calculator.score(game, i)
                contribution = round(score * calculator.WEIGHT, 2)

                result.signals.append(
                    (calculator.NAME, contribution)
                )

                weighted_score += contribution

                if score > 0:
                    result.reasons.append(
                        f"{calculator.NAME} +{score}"
                    )

                for reason in calculator.reasons(game, i):
                    result.reasons.append(reason)

            result.model_probability = round(
                50 + (weighted_score * 8),
                1
            )
            result.model_strength = result.model_probability
            result.play = self._selection_from_score(
                weighted_score,
                game,
            )

            (
                result.confidence,
                result.confidence_breakdown,
            ) = ConfidenceEngine.calculate(
                result.model_probability,
                game.away.pitcher,
                game.home.pitcher,
                game.away.offense,
                game.home.offense,
                market_available=False,
            )

            # Mock odds are only a pre-enrichment placeholder. They must not
            # produce a market edge or an actionable KBO recommendation.
            result.edge = 0.0
            result.recommendation = "❌ NO PLAY"

            game.result = result

            scored_games.append(game)

        return scored_games

    def finalize(self, games):
        for game in games:
            result = game.result
            odds = game.odds
            market_available = self._market_available(odds)

            if market_available:
                result.edge = EdgeCalculator.calculate(
                    result.model_probability,
                    self._value(
                        odds,
                        "reference_implied_probability",
                    ),
                )
            else:
                result.edge = None

            result.recommendation = self._model_score_recommendation(
                result.model_probability
            )
            result.confidence = self._model_strength_confidence(
                result.model_probability
            )
            result.model_confidence = result.confidence
            result.confidence_breakdown = {
                "model_strength": result.confidence,
                "basis": "KBO ordinal model score",
            }

        return games

    @staticmethod
    def _market_available(odds):
        return bool(
            KBOModel._value(odds, "reference_status") == "LOCKED"
            and KBOModel._value(
                odds,
                "reference_implied_probability",
            )
            is not None
        )

    @staticmethod
    def _value(source, key):
        if isinstance(source, dict):
            return source.get(key)

        return getattr(source, key, None)

    @staticmethod
    def _selection_from_score(
        weighted_score,
        game,
    ):
        if weighted_score > 0:
            return game.away.name

        if weighted_score < 0:
            return game.home.name

        return None

    @staticmethod
    def _model_score_recommendation(model_score):
        """Return a KBO-only ordinal label when no real market is available."""
        if model_score >= 58.0:
            return "🔥 STRONG PLAY"

        if model_score >= 55.0:
            return "✅ PLAYABLE"

        if model_score >= 52.0:
            return "👀 LEAN"

        return "❌ NO PLAY"

    @classmethod
    def _model_strength_confidence(cls, model_score):
        """Map the active KBO ordinal score range to relative model strength."""
        score = float(model_score or 0)
        span = cls.MODEL_SCORE_MAXIMUM - cls.MODEL_SCORE_MINIMUM
        strength = (
            (score - cls.MODEL_SCORE_MINIMUM)
            / span
            * 100
        )
        return round(max(0.0, min(100.0, strength)), 1)

    def _should_skip_game(self, game):

        away_unknown = (
            game.away.pitcher.name is None or
            game.away.pitcher.name == "Unknown Starter"
        )

        home_unknown = (
            game.home.pitcher.name is None or
            game.home.pitcher.name == "Unknown Starter"
        )

        return away_unknown and home_unknown

from engine.edge import EdgeCalculator

from loaders.pitcher_loader import PitcherLoader

from models.model_result import ModelResult

from calculators.mock_odds import MockOddsCalculator
from calculators.starting_pitching import StartingPitchingCalculator
from calculators.offense import OffenseCalculator
from calculators.bullpen import BullpenCalculator
from calculators.recent_form import RecentFormCalculator
from engine.kbo_shadow import build_supported_component_shadow


class KBOModel:

    MODEL_SCORE_MINIMUM = 42.0
    MODEL_SCORE_MAXIMUM = 58.0

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
            result.inactive_components = []

            weighted_score = 0
            component_scores = {}
            configured_weights = {}

            for calculator in self.calculators:

                score = calculator.score(game, i)
                component_scores[calculator.NAME] = score
                configured_weights[calculator.NAME] = calculator.WEIGHT
                contribution = score * calculator.WEIGHT

                result.signals.append(
                    (calculator.NAME, round(contribution, 2))
                )

                weighted_score += contribution

                if score > 0:
                    result.reasons.append(
                        f"{calculator.NAME} +{score}"
                    )

                for reason in calculator.reasons(game, i):
                    result.reasons.append(reason)

            result.model_strength = round(
                50 + (weighted_score * 8),
                1
            )
            result.component_scores = component_scores
            result.configured_weights = configured_weights
            result.weighted_score = round(weighted_score, 6)
            # Deprecated compatibility alias: this is ordinal model strength,
            # not a calibrated win probability.
            result.model_probability = result.model_strength
            result.play = self._selection_from_score(
                weighted_score,
                game,
            )
            result.shadow_model = build_supported_component_shadow(
                game=game,
                index=i,
                calculators=self.calculators,
                component_scores=component_scores,
                recommendation_fn=self._model_score_recommendation,
                selection_fn=self._selection_from_score,
            )

            (
                result.model_reliability,
                result.reliability_breakdown,
            ) = self._input_reliability(game)
            result.model_confidence = result.model_reliability
            result.confidence = result.model_reliability
            result.confidence_breakdown = result.reliability_breakdown
            result.legacy_model_confidence = self._model_strength_confidence(
                result.model_strength
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

            if getattr(result, "model_strength", None) is None:
                result.model_strength = result.model_probability

            result.recommendation = self._model_score_recommendation(
                result.model_strength
            )
            (
                result.model_reliability,
                result.reliability_breakdown,
            ) = self._input_reliability(game)
            result.confidence = result.model_reliability
            result.model_confidence = result.model_reliability
            result.confidence_breakdown = result.reliability_breakdown
            result.legacy_model_confidence = self._model_strength_confidence(
                result.model_strength
            )

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
        if model_score >= 57.0:
            return "🔥 STRONG PLAY"

        if model_score >= 56.5:
            return "✅ PLAY"

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

    @classmethod
    def _input_reliability(cls, game):
        score = 100.0
        breakdown = {
            "basis": "KBO current input reliability",
            "starter_identity": 0.0,
            "starter_stats": 0.0,
            "starter_role": 0.0,
            "offense": 0.0,
            "bullpen": 0.0,
            "recent_form": 0.0,
            "schedule_mapping": 0.0,
            "provider_quality": 0.0,
            "inactive_components": 0.0,
        }

        for side in (game.away, game.home):
            pitcher = side.pitcher
            if cls._missing_starter(pitcher):
                score -= 20.0
                breakdown["starter_identity"] -= 20.0
            elif getattr(pitcher, "data_source", None) != "starter_profile":
                score -= 8.0
                breakdown["provider_quality"] -= 8.0

            if not cls._has_required_starter_stats(pitcher):
                score -= 12.0
                breakdown["starter_stats"] -= 12.0

            role_context = getattr(pitcher, "role_context", None)
            if role_context == "no_prior_starts":
                score -= 6.0
                breakdown["starter_role"] -= 6.0
            elif role_context == "limited_starting_role":
                score -= 3.0
                breakdown["starter_role"] -= 3.0

            if side.offense.runs_per_game is None:
                score -= 10.0
                breakdown["offense"] -= 10.0
            elif getattr(
                side.offense,
                "offense_source",
                None,
            ) == "STATIC_FALLBACK":
                score -= 5.0
                breakdown["offense"] -= 5.0

            if side.bullpen.era is None or side.bullpen.league_era is None:
                score -= 6.0
                breakdown["bullpen"] -= 6.0

            if (
                side.form.recent_runs_per_game is None
                or side.form.season_runs_per_game is None
                or side.form.recent_games is None
            ):
                score -= 3.0
                breakdown["recent_form"] -= 3.0

        if not game.game_url:
            score -= 5.0
            breakdown["schedule_mapping"] -= 5.0

        breakdown["inactive_components"] = "No inactive KBO model components."

        return round(max(0.0, min(100.0, score)), 1), breakdown

    @staticmethod
    def _missing_starter(pitcher):
        return (
            pitcher.name is None
            or pitcher.name == "Unknown Starter"
            or getattr(pitcher, "starter_confirmed", False) is False
        )

    @staticmethod
    def _has_required_starter_stats(pitcher):
        return (
            pitcher.era is not None
            and pitcher.whip is not None
        )

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

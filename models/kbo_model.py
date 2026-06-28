from engine.edge import EdgeCalculator
from engine.recommendation import RecommendationEngine
from engine.confidence import ConfidenceEngine

from loaders.pitcher_loader import PitcherLoader

from models.model_result import ModelResult

from calculators.mock_odds import MockOddsCalculator
from calculators.starting_pitching import StartingPitchingCalculator
from calculators.offense import OffenseCalculator
from calculators.bullpen import BullpenCalculator
from calculators.recent_form import RecentFormCalculator


class KBOModel:

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

            if i % 2 == 0:
                result.play = game.away.name
            else:
                result.play = game.home.name

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

            result.edge = EdgeCalculator.calculate(
                result.model_probability,
                game.odds.book_probability
            )

            result.confidence = ConfidenceEngine.calculate(
                result.edge,
                len(result.reasons)
            )

            result.recommendation = RecommendationEngine.get_recommendation(
                result.edge
            )

            game.result = result

            scored_games.append(game)

        return scored_games

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

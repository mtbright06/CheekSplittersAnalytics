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

        for i, game in enumerate(games):

            self.odds.apply(game, i)

            PitcherLoader.load(game)

            result = ModelResult()

            result.market = "Moneyline"

            if i % 2 == 0:
                result.play = game.away.name
            else:
                result.play = game.home.name

            weighted_score = 0

            for calculator in self.calculators:

                score = calculator.score(game, i)

                weighted_score += score * calculator.WEIGHT

                if score > 0:
                    result.reasons.append(
                        f"{calculator.NAME} +{score}"
                    )

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

        return games
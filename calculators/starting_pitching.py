from calculators.base import BaseCalculator


class StartingPitchingCalculator(BaseCalculator):

    NAME = "Starting Pitching"

    WEIGHT = 0.35

    def score(self, game, index):

        # Fake for now
        return index - 1
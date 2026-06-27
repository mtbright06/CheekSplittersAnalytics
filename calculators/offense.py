from calculators.base import BaseCalculator


class OffenseCalculator(BaseCalculator):

    NAME = "Offense"

    WEIGHT = 0.25

    def score(self, game, index):

        if index >= 2:
            return 2

        return 0
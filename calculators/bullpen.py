from calculators.base import BaseCalculator


class BullpenCalculator(BaseCalculator):

    NAME = "Bullpen"

    WEIGHT = 0.15

    def score(self, game, index):

        if index >= 1:
            return 1

        return 0
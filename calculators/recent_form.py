from calculators.base import BaseCalculator


class RecentFormCalculator(BaseCalculator):

    NAME = "Recent Form"

    WEIGHT = 0.10

    def score(self, game, index):

        if index >= 3:
            return 1

        return 0
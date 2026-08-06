from calculators.base import BaseCalculator


class RecentFormCalculator(BaseCalculator):

    NAME = "Recent Form"

    WEIGHT = 0.10

    def score(self, game, index):
        return 0.0

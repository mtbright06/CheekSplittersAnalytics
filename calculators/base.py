class BaseCalculator:

    NAME = "Calculator"

    WEIGHT = 0.0

    def score(self, game, index):
        raise NotImplementedError

    def reasons(self, game, index):
        """
        Returns a list of human-readable reasons explaining
        why this calculator scored the game the way it did.

        Child calculators can override this.
        """
        return []

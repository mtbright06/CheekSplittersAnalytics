class MockOddsCalculator:

    NAME = "Mock Odds"
    WEIGHT = 0.0

    def apply(self, game, index):

        game.odds.moneyline = -110
        game.odds.book_probability = 50.0
        game.odds.source = "Mock Odds"

        return game
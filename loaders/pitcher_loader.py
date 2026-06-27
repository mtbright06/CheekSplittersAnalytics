class PitcherLoader:

    @staticmethod
    def load(game):

        #
        # Mock data for now.
        # Tomorrow this becomes MLB/KBO API.
        #

        game.home.pitcher.name = "Home Starter"
        game.home.pitcher.era = 3.42
        game.home.pitcher.whip = 1.09

        game.away.pitcher.name = "Away Starter"
        game.away.pitcher.era = 4.61
        game.away.pitcher.whip = 1.31
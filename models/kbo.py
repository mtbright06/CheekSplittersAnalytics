class KBOModel:

    def score(self, game):

        game.model_probability = 50.0
        game.edge = 0.0

        return game
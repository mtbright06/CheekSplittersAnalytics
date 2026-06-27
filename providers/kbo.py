from engine.provider import Provider
from models.game import Game

from providers.kbo_data_provider import KBODataProvider


class KBOProvider(Provider):

    def load(self):

        live_games = KBODataProvider.get_schedule()

        games = []

        for game in live_games:

            games.append(
                Game(
                    game["away"],
                    game["home"]
                )
            )

        return games

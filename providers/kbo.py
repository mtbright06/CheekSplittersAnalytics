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
                    away=game["away"],
                    home=game["home"],
                    game_url=game.get("url"),
                    venue=game.get("venue"),
                    start_time=game.get("time"),
                    game_date=game.get("game_date"),
                )
            )

        return games

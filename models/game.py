from models.odds import Odds
from models.team import Team


class Game:

    def __init__(
        self,
        away,
        home,
        game_url=None,
        venue=None,
        start_time=None,
        game_date=None,
    ):

        self.away = Team(away)
        self.home = Team(home)

        self.game_url = game_url
        self.venue = venue
        self.start_time = start_time
        self.game_date = game_date

        self.odds = Odds()

        self.result = None

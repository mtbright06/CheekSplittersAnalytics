from models.odds import Odds
from models.team import Team


class Game:

    def __init__(self, away, home):

        self.away = Team(away)
        self.home = Team(home)

        self.odds = Odds()

        self.result = None
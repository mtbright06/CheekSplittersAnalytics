from models.pitcher import Pitcher
from models.offense import Offense
from models.bullpen import Bullpen


class Team:

    def __init__(self, name):

        self.name = name

        self.record = None

        self.form = None

        self.pitcher = Pitcher()

        self.offense = Offense()

        self.bullpen = Bullpen()
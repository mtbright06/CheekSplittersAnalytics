from models.pitcher import Pitcher
from models.offense import Offense
from models.bullpen import Bullpen
from models.recent_form import RecentForm


class Team:

    def __init__(self, name):

        self.name = name

        self.record = None

        self.form = RecentForm()

        self.pitcher = Pitcher()

        self.offense = Offense()

        self.bullpen = Bullpen()

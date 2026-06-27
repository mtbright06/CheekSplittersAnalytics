class BaseProvider:

    NAME = "Base Provider"

    def get_schedule(self):
        raise NotImplementedError

    def get_team_data(self, team_name):
        raise NotImplementedError

    def get_odds(self, game):
        raise NotImplementedError

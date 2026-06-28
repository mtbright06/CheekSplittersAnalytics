from providers.base_provider import BaseProvider

from parsers.schedule_parser import ScheduleParser
from parsers.game_parser import GameParser
from parsers.pitcher_parser import PitcherParser


class KBODataProvider(BaseProvider):

    NAME = "KBO Provider"

    MOCK_TEAMS = {
        "Hanwha Eagles": {"offense": {"runs_per_game": 5.1}},
        "SSG Landers": {"offense": {"runs_per_game": 4.8}},
        "KIA Tigers": {"offense": {"runs_per_game": 5.4}},
        "Doosan Bears": {"offense": {"runs_per_game": 4.6}},
        "KT Wiz": {"offense": {"runs_per_game": 4.7}},
        "Samsung Lions": {"offense": {"runs_per_game": 5.0}},
        "LG Twins": {"offense": {"runs_per_game": 5.3}},
        "Lotte Giants": {"offense": {"runs_per_game": 4.9}},
        "Kiwoom Heroes": {"offense": {"runs_per_game": 4.3}},
        "NC Dinos": {"offense": {"runs_per_game": 5.2}},
    }

    @classmethod
    def get_schedule(cls):
        return ScheduleParser.load()

    @classmethod
    def get_game_details(cls, url):
        return GameParser.load(url)

    @classmethod
    def get_pitcher_details(cls, url):
        return PitcherParser.load(url)

    @classmethod
    def get_team_data(cls, team_name):
        return cls.MOCK_TEAMS.get(team_name)

    def get_odds(self, game):
        raise NotImplementedError

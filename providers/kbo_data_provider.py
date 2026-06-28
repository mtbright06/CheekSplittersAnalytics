from providers.base_provider import BaseProvider

from parsers.schedule_parser import ScheduleParser
from parsers.game_parser import GameParser
from parsers.pitcher_parser import PitcherParser


class KBODataProvider(BaseProvider):

    NAME = "KBO Provider"

    MOCK_TEAMS = {
        "Hanwha Eagles": {
            "pitcher": {"name": "Hanwha Starter", "era": 3.80, "whip": 1.22},
            "offense": {"runs_per_game": 5.1},
        },
        "SSG Landers": {
            "pitcher": {"name": "SSG Starter", "era": 4.10, "whip": 1.30},
            "offense": {"runs_per_game": 4.8},
        },
        "KIA Tigers": {
            "pitcher": {"name": "KIA Starter", "era": 3.65, "whip": 1.18},
            "offense": {"runs_per_game": 5.4},
        },
        "Doosan Bears": {
            "pitcher": {"name": "Doosan Starter", "era": 4.35, "whip": 1.36},
            "offense": {"runs_per_game": 4.6},
        },
        "KT Wiz": {
            "pitcher": {"name": "KT Starter", "era": 4.20, "whip": 1.33},
            "offense": {"runs_per_game": 4.7},
        },
        "Samsung Lions": {
            "pitcher": {"name": "Samsung Starter", "era": 3.95, "whip": 1.27},
            "offense": {"runs_per_game": 5.0},
        },
        "LG Twins": {
            "pitcher": {"name": "LG Starter", "era": 3.50, "whip": 1.14},
            "offense": {"runs_per_game": 5.3},
        },
        "Lotte Giants": {
            "pitcher": {"name": "Lotte Starter", "era": 4.40, "whip": 1.38},
            "offense": {"runs_per_game": 4.9},
        },
        "Kiwoom Heroes": {
            "pitcher": {"name": "Kiwoom Starter", "era": 4.75, "whip": 1.42},
            "offense": {"runs_per_game": 4.3},
        },
        "NC Dinos": {
            "pitcher": {"name": "NC Starter", "era": 3.30, "whip": 1.10},
            "offense": {"runs_per_game": 5.2},
        },
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

from providers.base_provider import BaseProvider

from parsers.schedule_parser import ScheduleParser
from parsers.game_parser import GameParser
from parsers.pitcher_parser import PitcherParser
from parsers.team_splits_parser import TeamSplitsParser


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
    _team_splits_cache = None

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
        live = cls._live_team_data(team_name)

        if live is not None:
            return live

        fallback = cls.MOCK_TEAMS.get(team_name)

        if fallback is None:
            return None

        return {
            "offense": {
                **fallback["offense"],
                "league_runs_per_game": cls._static_league_rpg(),
                "offense_source": "STATIC_FALLBACK",
                "source_url": None,
                "retrieved_at": None,
            }
        }

    @classmethod
    def _live_team_data(cls, team_name):
        dataset = cls._team_splits()

        if dataset is None:
            return None

        team = dataset.teams.get(team_name)

        if team is None:
            return None

        return {
            "offense": {
                "runs_per_game": team["runs_per_game"],
                "league_runs_per_game": dataset.league_rpg,
                "offense_source": team["source"],
                "runs_allowed_per_game": team["runs_allowed_per_game"],
                "league_starting_era": dataset.league_starting_era,
                "bullpen_era": team["bullpen_era"],
                "league_bullpen_era": dataset.league_bullpen_era,
                "bullpen_source": team["source"],
                "last_10_runs_per_game": team["last_10_runs_per_game"],
                "last_10_runs_allowed_per_game": team[
                    "last_10_runs_allowed_per_game"
                ],
                "last_10_games": team["last_10_games"],
                "recent_form_source": team["source"],
                "home_runs_per_game": team["home_runs_per_game"],
                "away_runs_per_game": team["away_runs_per_game"],
                "home_games": team["home_games"],
                "away_games": team["away_games"],
                "source_url": team["source_url"],
                "retrieved_at": team["retrieved_at"],
                "source_row": team["source_row"],
            }
        }

    @classmethod
    def _team_splits(cls):
        if cls._team_splits_cache is False:
            return None

        if cls._team_splits_cache is not None:
            return cls._team_splits_cache

        try:
            cls._team_splits_cache = TeamSplitsParser.load()
        except Exception:
            cls._team_splits_cache = False

        if cls._team_splits_cache is False:
            return None

        return cls._team_splits_cache

    @classmethod
    def _static_league_rpg(cls):
        values = [
            data["offense"]["runs_per_game"]
            for data in cls.MOCK_TEAMS.values()
        ]
        return round(sum(values) / len(values), 3)

    def get_odds(self, game):
        raise NotImplementedError

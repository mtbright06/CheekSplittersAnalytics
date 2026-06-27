import requests
from bs4 import BeautifulSoup

from providers.base_provider import BaseProvider


class KBODataProvider(BaseProvider):

    NAME = "KBO Provider"
    URL = "https://mykbostats.com/"

    TEAM_NAME_MAP = {
        ("Hanwha", "Eagles"): "Hanwha Eagles",
        ("SSG", "Landers"): "SSG Landers",
        ("Kia", "Tigers"): "KIA Tigers",
        ("KIA", "Tigers"): "KIA Tigers",
        ("Doosan", "Bears"): "Doosan Bears",
        ("KT", "Wiz"): "KT Wiz",
        ("Samsung", "Lions"): "Samsung Lions",
        ("LG", "Twins"): "LG Twins",
        ("Lotte", "Giants"): "Lotte Giants",
        ("Kiwoom", "Heroes"): "Kiwoom Heroes",
        ("NC", "Dinos"): "NC Dinos",
    }

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
    def get_team_data(cls, team_name):
        return cls.MOCK_TEAMS.get(team_name)

    @classmethod
    def get_schedule(cls):
        response = requests.get(cls.URL, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        lines = [
            line.strip()
            for line in soup.get_text("\n", strip=True).splitlines()
            if line.strip()
        ]

        start = lines.index("Today’s")
        games_index = start + 3

        games = []
        i = games_index

        while i < len(lines):
            if lines[i] == "Yesterday’s":
                break

            away = cls._normalize_team(lines[i], lines[i + 1])
            game_time = lines[i + 2]
            venue = lines[i + 3]
            home = cls._normalize_team(lines[i + 4], lines[i + 5])

            games.append(
                {
                    "away": away,
                    "home": home,
                    "time": game_time,
                    "venue": venue,
                }
            )

            i += 6

        return games

    @classmethod
    def _normalize_team(cls, first, second):
        return cls.TEAM_NAME_MAP.get((first, second), f"{first} {second}")

    def get_odds(self, game):
        raise NotImplementedError

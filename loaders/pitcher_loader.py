class PitcherLoader:

    MOCK_PITCHERS = {
        "Hanwha Eagles": {
            "name": "Hanwha Starter",
            "era": 3.80,
            "whip": 1.22,
        },
        "SSG Landers": {
            "name": "SSG Starter",
            "era": 4.10,
            "whip": 1.30,
        },
        "KIA Tigers": {
            "name": "KIA Starter",
            "era": 3.65,
            "whip": 1.18,
        },
        "Doosan Bears": {
            "name": "Doosan Starter",
            "era": 4.35,
            "whip": 1.36,
        },
        "KT Wiz": {
            "name": "KT Starter",
            "era": 4.20,
            "whip": 1.33,
        },
        "Samsung Lions": {
            "name": "Samsung Starter",
            "era": 3.95,
            "whip": 1.27,
        },
        "LG Twins": {
            "name": "LG Starter",
            "era": 3.50,
            "whip": 1.14,
        },
        "Lotte Giants": {
            "name": "Lotte Starter",
            "era": 4.40,
            "whip": 1.38,
        },
        "Kiwoom Heroes": {
            "name": "Kiwoom Starter",
            "era": 4.75,
            "whip": 1.42,
        },
        "NC Dinos": {
            "name": "NC Starter",
            "era": 3.30,
            "whip": 1.10,
        },
    }

    @staticmethod
    def load(game):

        PitcherLoader._apply_pitcher(game.away)
        PitcherLoader._apply_pitcher(game.home)

    @staticmethod
    def _apply_pitcher(team):

        data = PitcherLoader.MOCK_PITCHERS.get(team.name)

        if data is None:
            team.pitcher.name = "Unknown Starter"
            team.pitcher.era = None
            team.pitcher.whip = None
            return

        team.pitcher.name = data["name"]
        team.pitcher.era = data["era"]
        team.pitcher.whip = data["whip"]
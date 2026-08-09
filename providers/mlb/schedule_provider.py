from engine.mlb.schedule import fetch_mlb_schedule


class MLBScheduleProvider:
    def __init__(self, target_date=None):
        self.target_date = target_date

    def load(self):
        data = fetch_mlb_schedule(self.target_date)
        games = []

        for day in data.get("dates", []):
            for game in day.get("games", []):
                games.append(game)

        return games

import requests
from bs4 import BeautifulSoup


class ScheduleParser:

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

    @classmethod
    def load(cls):

        response = requests.get(cls.URL, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        games = []

        links = soup.find_all("a", href=True)

        for link in links:

            href = link["href"]

            if not href.startswith("/games/"):
                continue

            # Skip yesterday/final games
            text = link.get_text(" ", strip=True)
            if "Final" in text:
                continue

            lines = [
                x.strip()
                for x in link.get_text("\n", strip=True).splitlines()
                if x.strip()
            ]

            if len(lines) < 6:
                continue

            away = cls._normalize(lines[0], lines[1])
            game_time = lines[2]
            venue = lines[3]
            home = cls._normalize(lines[4], lines[5])

            games.append(
                {
                    "away": away,
                    "home": home,
                    "time": game_time,
                    "venue": venue,
                    "url": f"https://mykbostats.com{href}",
                }
            )

        return games

    @classmethod
    def _normalize(cls, first, second):

        return cls.TEAM_NAME_MAP.get(
            (first, second),
            f"{first} {second}"
        )

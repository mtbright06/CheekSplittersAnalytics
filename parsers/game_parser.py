import requests
from bs4 import BeautifulSoup


class GameParser:

    @classmethod
    def load(cls, url):

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        starters = soup.select(
            "div.away-starter, div.home-starter"
        )

        if len(starters) != 2:
            raise Exception("Unable to locate both starting pitchers.")

        return {
            "away": cls._parse_pitcher(starters[0]),
            "home": cls._parse_pitcher(starters[1]),
        }

    @classmethod
    def _parse_pitcher(cls, starter):

        lines = [
            line.strip()
            for line in starter.get_text("\n", strip=True).splitlines()
            if line.strip()
        ]

        name = lines[0]

        record = None
        era = None

        for i, line in enumerate(lines):

            if line == "Season:":

                if i + 2 < len(lines):
                    record = lines[i + 1]

                if i + 3 < len(lines):
                    era = lines[i + 3]

                break

        return {
            "name": name,
            "record": record,
            "era": era,
        }

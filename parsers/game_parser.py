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
            return {
                "away": cls._unknown_pitcher(),
                "home": cls._unknown_pitcher(),
            }

        return {
            "away": cls._parse_pitcher(starters[0]),
            "home": cls._parse_pitcher(starters[1]),
        }

    @classmethod
    def _parse_pitcher(cls, starter):

        links = starter.select("a.player-link[href]")
        name_link = links[-1] if links else None

        name = name_link.get_text(strip=True) if name_link else "Unknown Starter"

        lines = [
            line.strip()
            for line in starter.get_text("\n", strip=True).splitlines()
            if line.strip()
        ]

        record = None
        era = None

        for i, line in enumerate(lines):

            if line == "Season:":

                if i + 1 < len(lines):
                    record = lines[i + 1]

                if i + 3 < len(lines):
                    era = lines[i + 3]

                break

        profile_url = None

        if name_link:
            href = name_link["href"]

            if href.startswith("http"):
                profile_url = href
            else:
                profile_url = f"https://mykbostats.com{href}"

        return {
            "name": name,
            "record": record,
            "era": era,
            "profile_url": profile_url,
        }

    @classmethod
    def _unknown_pitcher(cls):

        return {
            "name": "Unknown Starter",
            "record": None,
            "era": None,
            "profile_url": None,
        }

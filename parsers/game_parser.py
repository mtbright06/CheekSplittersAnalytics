import requests
from bs4 import BeautifulSoup


class GameParser:

    @classmethod
    def load(cls, url):

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        starters = cls._find_starters(soup)

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
    def _find_starters(cls, soup):

        starters = soup.select(
            ".away-starter, .home-starter"
        )

        if len(starters) == 2:
            return starters

        possible = []

        for div in soup.find_all("div"):
            classes = div.get("class", [])
            class_text = " ".join(classes)

            if "starter" in class_text:
                possible.append(div)

        return possible[:2]

    @classmethod
    def _parse_pitcher(cls, starter):

        lines = [
            line.strip()
            for line in starter.get_text("\n", strip=True).splitlines()
            if line.strip()
        ]

        name = "Unknown Starter"
        record = None
        era = None

        links = starter.find_all("a", href=True)

        player_link = None

        for link in links:
            href = link["href"]
            if "/players/" in href:
                player_link = link
                break

        if player_link:
            name = player_link.get_text(strip=True)

        elif lines:
            name = lines[0]

        for i, line in enumerate(lines):

            if line == "Season:":

                if i + 1 < len(lines):
                    record = lines[i + 1]

                if i + 3 < len(lines):
                    era = lines[i + 3]

                break

        profile_url = None

        if player_link:
            href = player_link["href"]

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

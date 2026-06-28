import requests
from bs4 import BeautifulSoup


class PitcherParser:

    @classmethod
    def load(cls, url):

        response = requests.get(url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        return cls._parse_profile(soup)

    @classmethod
    def _parse_profile(cls, soup):

        data = {
            "name": None,
            "throws": None,
            "bats": None,
            "record": None,
            "era": None,
            "whip": None,
            "ip": None,
            "so": None,
            "bb": None,
            "hr_allowed": None,
            "k_rate": None,
            "bb_rate": None,
            "hr9": None,
        }

        h1 = soup.find("h1")

        if h1:
            title = h1.get_text(" ", strip=True)
            data["name"] = title.split("(")[0].strip()

            if "RHP" in title:
                data["throws"] = "R"
            elif "LHP" in title:
                data["throws"] = "L"

        text = soup.get_text("\n", strip=True)
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        for i, line in enumerate(lines):
            if line == "Throws / Bats" and i + 1 < len(lines):
                parts = lines[i + 1].split("/")
                if len(parts) == 2:
                    data["throws"] = cls._normalize_hand(parts[0])
                    data["bats"] = cls._normalize_hand(parts[1])

        table = soup.find("table")

        if not table:
            return data

        rows = table.find_all("tr")

        if len(rows) < 2:
            return data

        headers = [
            header.get_text(strip=True)
            for header in rows[0].find_all(["th", "td"])
        ]

        values = [
            value.get_text(strip=True)
            for value in rows[1].find_all(["th", "td"])
        ]

        stat_map = dict(zip(headers, values))

        wins = stat_map.get("W")
        losses = stat_map.get("L")

        if wins is not None and losses is not None:
            data["record"] = f"{wins}-{losses}"

        data["era"] = cls._to_float(stat_map.get("ERA"))
        data["whip"] = cls._to_float(stat_map.get("WHIP"))
        data["ip"] = cls._to_float(stat_map.get("IP"))
        data["so"] = cls._to_int(stat_map.get("SO"))
        data["bb"] = cls._to_int(stat_map.get("BB"))
        data["hr_allowed"] = cls._to_int(stat_map.get("HR"))

        if data["ip"] and data["ip"] > 0:
            if data["so"] is not None:
                data["k_rate"] = round((data["so"] / data["ip"]) * 9, 2)

            if data["bb"] is not None:
                data["bb_rate"] = round((data["bb"] / data["ip"]) * 9, 2)

            if data["hr_allowed"] is not None:
                data["hr9"] = round((data["hr_allowed"] / data["ip"]) * 9, 2)

        return data

    @classmethod
    def _normalize_hand(cls, value):

        value = value.strip().lower()

        if value.startswith("right"):
            return "R"

        if value.startswith("left"):
            return "L"

        return value.upper()

    @classmethod
    def _to_float(cls, value):

        if value is None or value == "":
            return None

        try:
            return float(value)
        except ValueError:
            return None

    @classmethod
    def _to_int(cls, value):

        if value is None or value == "":
            return None

        try:
            return int(value)
        except ValueError:
            return None

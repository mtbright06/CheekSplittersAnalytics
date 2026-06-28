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

        cls._parse_name_and_hands(soup, data)
        cls._parse_season_table(soup, data)
        cls._calculate_rates(data)

        return data

    @classmethod
    def _parse_name_and_hands(cls, soup, data):

        h1 = soup.find("h1")

        if h1:
            title = h1.get_text(" ", strip=True)
            data["name"] = title.split("(")[0].strip()

        lines = cls._lines(soup)

        for i, line in enumerate(lines):

            if line == "Throws / Bats" and i + 1 < len(lines):
                parts = lines[i + 1].split("/")

                if len(parts) == 2:
                    data["throws"] = cls._normalize_hand(parts[0])
                    data["bats"] = cls._normalize_hand(parts[1])

    @classmethod
    def _parse_season_table(cls, soup, data):

        tables = soup.find_all("table")

        for table in tables:

            rows = table.find_all("tr")

            if len(rows) < 2:
                continue

            headers = [
                cell.get_text(strip=True)
                for cell in rows[0].find_all(["th", "td"])
            ]

            needed = {"ERA", "WHIP", "W", "L", "IP", "SO", "BB", "HR"}

            if not needed.intersection(set(headers)):
                continue

            values = [
                cell.get_text(strip=True)
                for cell in rows[1].find_all(["th", "td"])
            ]

            stat_map = dict(zip(headers, values))

            wins = stat_map.get("W")
            losses = stat_map.get("L")

            if wins is not None and losses is not None:
                data["record"] = f"{wins}-{losses}"

            data["era"] = cls._to_float(stat_map.get("ERA"))
            data["whip"] = cls._to_float(stat_map.get("WHIP"))
            data["ip"] = cls._innings_to_float(stat_map.get("IP"))
            data["so"] = cls._to_int(stat_map.get("SO"))
            data["bb"] = cls._to_int(stat_map.get("BB"))
            data["hr_allowed"] = cls._to_int(stat_map.get("HR"))

            return

    @classmethod
    def _calculate_rates(cls, data):

        ip = data.get("ip")

        if not ip or ip <= 0:
            return

        if data.get("so") is not None:
            data["k_rate"] = round((data["so"] / ip) * 9, 2)

        if data.get("bb") is not None:
            data["bb_rate"] = round((data["bb"] / ip) * 9, 2)

        if data.get("hr_allowed") is not None:
            data["hr9"] = round((data["hr_allowed"] / ip) * 9, 2)

    @classmethod
    def _lines(cls, soup):

        return [
            line.strip()
            for line in soup.get_text("\n", strip=True).splitlines()
            if line.strip()
        ]

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
            return int(float(value))
        except ValueError:
            return None

    @classmethod
    def _innings_to_float(cls, value):

        if value is None or value == "":
            return None

        text = str(value).strip()

        if "." not in text:
            return cls._to_float(text)

        whole, partial = text.split(".", 1)

        try:
            whole = int(whole)
            partial = int(partial)
        except ValueError:
            return None

        if partial == 1:
            return whole + (1 / 3)

        if partial == 2:
            return whole + (2 / 3)

        return float(text)

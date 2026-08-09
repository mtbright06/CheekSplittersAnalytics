import requests
from bs4 import BeautifulSoup


URL = "https://mykbostats.com/games/13645-LG-vs-Lotte-20260628"


def main():
    response = requests.get(URL, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    starters = soup.select("div.starters div.away-starter, div.starters div.home-starter")

    print("=" * 60)
    print("KBO GAME STARTER PROBE")
    print("=" * 60)

    for starter in starters:
        name_link = starter.select_one("a.player-link")
        name = name_link.get_text(strip=True) if name_link else "Unknown"

        text_lines = [
            line.strip()
            for line in starter.get_text("\n", strip=True).splitlines()
            if line.strip()
        ]

        print("")
        print(f"Starter: {name}")

        for line in text_lines:
            print(line)

        print("-" * 60)


if __name__ == "__main__":
    main()

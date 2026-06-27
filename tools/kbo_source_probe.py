import requests
from bs4 import BeautifulSoup


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


def normalize_team(first, second):
    return TEAM_NAME_MAP.get((first, second), f"{first} {second}")


def main():
    response = requests.get(URL, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    lines = [line.strip() for line in soup.get_text("\n", strip=True).splitlines() if line.strip()]

    start = lines.index("Today’s")
    games_index = start + 3

    games = []
    i = games_index

    while i < len(lines):
        if lines[i] == "Yesterday’s":
            break

        away = normalize_team(lines[i], lines[i + 1])
        game_time = lines[i + 2]
        venue = lines[i + 3]
        home = normalize_team(lines[i + 4], lines[i + 5])

        games.append((away, home, game_time, venue))
        i += 6

    print("=" * 60)
    print("TODAY'S KBO SCHEDULE")
    print("=" * 60)

    for away, home, game_time, venue in games:
        print(f"{away} @ {home} | {game_time} | {venue}")


if __name__ == "__main__":
    main()

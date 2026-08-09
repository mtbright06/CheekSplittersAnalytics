import requests
from bs4 import BeautifulSoup

URL = "https://mykbostats.com/"


def main():

    response = requests.get(URL, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    print("=" * 80)
    print("ALL LINKS CONTAINING '/games/'")
    print("=" * 80)

    links = soup.find_all("a", href=True)

    found = 0

    for link in links:

        href = link["href"]

        if "/games/" in href:

            found += 1

            print()
            print("TEXT :", link.get_text(" ", strip=True))
            print("LINK :", href)
            print("-" * 80)

    print()
    print(f"Found {found} game links.")


if __name__ == "__main__":
    main()

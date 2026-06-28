from parsers.game_parser import GameParser
from providers.kbo_data_provider import KBODataProvider


GAME_URL = "https://mykbostats.com/games/13645-LG-vs-Lotte-20260628"

details = GameParser.load(GAME_URL)

for side in ["away", "home"]:
    summary = details[side]
    print("=" * 60)
    print(side.upper())
    print(summary)

    profile_url = summary.get("profile_url")

    if profile_url:
        profile = KBODataProvider.get_pitcher_details(profile_url)
        print(profile)

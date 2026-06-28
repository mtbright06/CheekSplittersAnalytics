from parsers.pitcher_parser import PitcherParser


PITCHER_URL = "https://mykbostats.com/players/1051-Lee-Sangkyu-Hanwha-Eagles"

profile = PitcherParser.load(PITCHER_URL)

print(profile)

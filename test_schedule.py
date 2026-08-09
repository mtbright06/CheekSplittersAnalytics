from parsers.schedule_parser import ScheduleParser

games = ScheduleParser.load()

for g in games:
    print(g)

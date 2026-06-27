from engine.logger import Logger


class Pipeline:

    def __init__(self, provider, model, report):

        self.provider = provider
        self.model = model
        self.report = report

    def run(self, sport=None, version=None):

        logger = Logger()

        if version:
            logger.write(f"Version: {version}")

        if sport:
            logger.write(f"Sport: {sport}")

        logger.write("-" * 60)
        logger.write("")

        games = self.provider.load()

        games = self.model.score(games)

        self.report.print_schedule(games, logger)

        logger.save()
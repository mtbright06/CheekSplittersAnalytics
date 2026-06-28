from engine.logger import Logger
from exporters.json_exporter import JsonExporter


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

        output_path = JsonExporter.export(
            games,
            sport=sport,
            version=version
        )

        logger.write("")
        logger.write(f"JSON export saved to: {output_path}")

        logger.save()

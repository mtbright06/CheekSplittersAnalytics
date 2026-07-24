from venv import logger

from engine.enrichers.odds_enricher import OddsEnricher
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

        from engine.enrichers.odds_enricher import OddsEnricher

        try:

            enricher = OddsEnricher(sport)

            games = enricher.enrich(games)

        except Exception as ex:

            logger.write(f"Odds enrichment skipped: {ex}")

        if hasattr(self.model, "finalize"):
            games = self.model.finalize(games)

        self.report.print_schedule(games, logger)

        output_path = JsonExporter.export(
            games,
            sport=sport,
            version=version
        )

        logger.write("")
        logger.write(f"JSON export saved to: {output_path}")

        logger.save()

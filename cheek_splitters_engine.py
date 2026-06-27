from config.settings import SPORT, VERSION

from engine.banner import print_banner
from engine.pipeline import Pipeline
from engine.factory import ProviderFactory
from engine.model_factory import ModelFactory

from reports.console import ConsoleReport


def main():

    print_banner(VERSION, SPORT)

    print(f"Loading {SPORT} schedule...\n")

    pipeline = Pipeline(
        provider=ProviderFactory.create(SPORT),
        model=ModelFactory.create(),
        report=ConsoleReport()
    )

    pipeline.run(
        sport=SPORT,
        version=VERSION
    )


if __name__ == "__main__":
    main()
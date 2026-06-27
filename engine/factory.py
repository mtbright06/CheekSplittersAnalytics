from providers.kbo import KBOProvider


class ProviderFactory:

    @staticmethod
    def create(sport):

        if sport.upper() == "KBO":
            return KBOProvider()

        raise ValueError(f"Unsupported sport: {sport}")
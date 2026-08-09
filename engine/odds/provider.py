from abc import ABC, abstractmethod


class OddsProvider(ABC):
    @abstractmethod
    def get_moneylines(self, league: str):
        pass

    def get_spreads(self, league: str):
        return []

    def get_totals(self, league: str):
        return []

    def get_props(self, league: str):
        return []


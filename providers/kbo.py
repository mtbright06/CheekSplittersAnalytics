from engine.provider import Provider
from models.game import Game


class KBOProvider(Provider):

    def load(self):

        return [

            Game("Hanwha Eagles","SSG Landers"),
            Game("KIA Tigers","Doosan Bears"),
            Game("KT Wiz","Samsung Lions"),
            Game("LG Twins","Lotte Giants"),
            Game("Kiwoom Heroes","NC Dinos")

        ]
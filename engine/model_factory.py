from config.settings import SPORT

from models.kbo_model import KBOModel


class ModelFactory:

    @staticmethod
    def create():

        if SPORT == "KBO":
            return KBOModel()

        raise ValueError(f"No model configured for {SPORT}")
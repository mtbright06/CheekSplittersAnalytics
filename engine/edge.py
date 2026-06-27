class EdgeCalculator:

    @staticmethod
    def calculate(model_probability, book_probability):

        return round(
            model_probability - book_probability,
            1
        )
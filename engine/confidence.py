class ConfidenceEngine:

    @staticmethod
    def calculate(
        model_probability,
        away_pitcher,
        home_pitcher,
        away_offense,
        home_offense,
        market_available,
    ):
        breakdown = {
            "base": 45.0,
            "matchup_strength": 0.0,
            "data_quality": 0.0,
            "starter_certainty": 0.0,
        }

        probability = ConfidenceEngine._to_float(
            model_probability
        )

        if probability is not None:
            breakdown["matchup_strength"] = min(
                abs(probability - 50.0) * 1.1,
                30.0,
            )

        inputs = [
            ConfidenceEngine._starter_data_available(
                away_pitcher
            ),
            ConfidenceEngine._starter_data_available(
                home_pitcher
            ),
            ConfidenceEngine._value(away_offense, "runs_per_game")
            is not None,
            ConfidenceEngine._value(home_offense, "runs_per_game")
            is not None,
        ]
        breakdown["data_quality"] = (
            sum(inputs) / len(inputs)
        ) * 20.0

        unknown_count = sum([
            ConfidenceEngine._unknown_starter(
                away_pitcher
            ),
            ConfidenceEngine._unknown_starter(
                home_pitcher
            ),
        ])

        if unknown_count == 1:
            breakdown["starter_certainty"] = -10.0
        elif unknown_count == 2:
            breakdown["starter_certainty"] = -20.0

        confidence = sum(breakdown.values())
        confidence = max(35.0, min(95.0, confidence))

        return (
            round(confidence, 1),
            {
                key: round(value, 1)
                for key, value in breakdown.items()
            },
        )

    @staticmethod
    def _starter_data_available(pitcher):
        return (
            not ConfidenceEngine._unknown_starter(pitcher)
            and ConfidenceEngine._value(pitcher, "era")
            is not None
            and ConfidenceEngine._value(pitcher, "whip")
            is not None
        )

    @staticmethod
    def _unknown_starter(pitcher):
        name = ConfidenceEngine._value(pitcher, "name")

        return not name or name == "Unknown Starter"

    @staticmethod
    def _value(source, key):
        if isinstance(source, dict):
            return source.get(key)

        return getattr(source, key, None)

    @staticmethod
    def _to_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

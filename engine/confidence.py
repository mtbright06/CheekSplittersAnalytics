class ConfidenceEngine:

    @staticmethod
    def calculate(edge, reason_count):

        confidence = 50

        confidence += edge * 3
        confidence += reason_count * 5

        confidence = max(0, min(100, confidence))

        return round(confidence, 1)
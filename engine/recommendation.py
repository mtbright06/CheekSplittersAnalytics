class RecommendationEngine:

    @staticmethod
    def get_recommendation(edge):

        if edge >= 8:
            return "🔥 BET"

        elif edge >= 5:
            return "👀 LEAN"

        return "❌ NO PLAY"
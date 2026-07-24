class ModelResult:

    def __init__(self):

        self.market = None
        self.play = None

        self.model_probability = None
        self.edge = None
        self.confidence = None
        self.confidence_breakdown = {}

        self.recommendation = None

        # Human-readable explanations
        self.reasons = []

        # Numeric contribution from each calculator
        self.signals = []

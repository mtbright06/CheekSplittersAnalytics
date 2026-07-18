from dataclasses import dataclass


@dataclass
class FatigueResult:
    innings_last3: float
    fatigue_score: float
    rating: str


def calculate_fatigue(innings_last3: float) -> FatigueResult:
    if innings_last3 <= 6:
        return FatigueResult(
            innings_last3,
            0.00,
            "RESTED",
        )

    if innings_last3 <= 10:
        return FatigueResult(
            innings_last3,
            0.10,
            "NORMAL",
        )

    if innings_last3 <= 14:
        return FatigueResult(
            innings_last3,
            0.25,
            "HEAVY",
        )

    return FatigueResult(
        innings_last3,
        0.45,
        "OVERWORKED",
    )

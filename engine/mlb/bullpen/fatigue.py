from dataclasses import dataclass


@dataclass
class FatigueResult:
    innings_last3: float
    innings_last5: float | None
    high_leverage_concerns: int
    fatigue_score: float
    rating: str


def calculate_fatigue(
    innings_last3: float,
    innings_last5: float | None = None,
    high_leverage_concerns: int = 0,
) -> FatigueResult:
    innings_last5_value = (
        innings_last5
        if innings_last5 is not None
        else innings_last3
    )

    if innings_last3 <= 2 and innings_last5_value <= 3:
        return FatigueResult(
            innings_last3,
            innings_last5,
            high_leverage_concerns,
            0.00,
            "RESTED",
        )

    if innings_last3 <= 4 and innings_last5_value <= 5:
        return FatigueResult(
            innings_last3,
            innings_last5,
            high_leverage_concerns,
            round(
                0.08 + (high_leverage_concerns * 0.03),
                2,
            ),
            "LIGHT",
        )

    if innings_last3 <= 6 and innings_last5_value <= 8:
        return FatigueResult(
            innings_last3,
            innings_last5,
            high_leverage_concerns,
            round(
                0.18 + (high_leverage_concerns * 0.04),
                2,
            ),
            "HEAVY",
        )

    return FatigueResult(
        innings_last3,
        innings_last5,
        high_leverage_concerns,
        round(
            min(
                0.35,
                0.30 + (high_leverage_concerns * 0.05),
            ),
            2,
        ),
        "OVERWORKED",
    )

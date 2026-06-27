from calculators.base import BaseCalculator


class StartingPitchingCalculator(BaseCalculator):

    NAME = "Starting Pitching"
    WEIGHT = 0.35

    def score(self, game, index=None):

        score = 0

        away_pitcher = game.away.pitcher
        home_pitcher = game.home.pitcher

        if away_pitcher.era is None or home_pitcher.era is None:
            return score

        if away_pitcher.era < home_pitcher.era:
            score += 1
        elif home_pitcher.era < away_pitcher.era:
            score -= 1

        if away_pitcher.whip is not None and home_pitcher.whip is not None:

            if away_pitcher.whip < home_pitcher.whip:
                score += 1
            elif home_pitcher.whip < away_pitcher.whip:
                score -= 1

        return score

    def reasons(self, game, index=None):

        reasons = []

        away_pitcher = game.away.pitcher
        home_pitcher = game.home.pitcher

        if away_pitcher.era is None or home_pitcher.era is None:
            return reasons

        if away_pitcher.era < home_pitcher.era:
            reasons.append(
                f"{game.away.name} has the starting ERA advantage "
                f"({away_pitcher.era:.2f} vs {home_pitcher.era:.2f})"
            )
        elif home_pitcher.era < away_pitcher.era:
            reasons.append(
                f"{game.home.name} has the starting ERA advantage "
                f"({home_pitcher.era:.2f} vs {away_pitcher.era:.2f})"
            )

        if away_pitcher.whip is not None and home_pitcher.whip is not None:

            if away_pitcher.whip < home_pitcher.whip:
                reasons.append(
                    f"{game.away.name} has the starting WHIP advantage "
                    f"({away_pitcher.whip:.2f} vs {home_pitcher.whip:.2f})"
                )
            elif home_pitcher.whip < away_pitcher.whip:
                reasons.append(
                    f"{game.home.name} has the starting WHIP advantage "
                    f"({home_pitcher.whip:.2f} vs {away_pitcher.whip:.2f})"
                )

        return reasons

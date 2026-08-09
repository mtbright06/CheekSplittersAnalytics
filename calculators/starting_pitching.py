from calculators.base import BaseCalculator


class StartingPitchingCalculator(BaseCalculator):

    NAME = "Starting Pitching"
    WEIGHT = 0.55

    METRIC_WEIGHTS = {
        "era": 0.45,
        "whip": 0.30,
        "k_minus_bb": 0.15,
        "hr9": 0.10,
    }

    def score(self, game, index):

        if (
            self._missing_starter(game.away.pitcher)
            or self._missing_starter(game.home.pitcher)
        ):
            return 0.0

        away_score = self._pitcher_score(game.away.pitcher)
        home_score = self._pitcher_score(game.home.pitcher)

        return round(
            self._clamp(
                (away_score - home_score) / 2,
                -1.0,
                1.0,
            ),
            3,
        )

    def reasons(self, game, index):

        away = game.away
        home = game.home

        reasons = []

        comparisons = [
            ("ERA", away.pitcher.era, home.pitcher.era, "lower"),
            ("WHIP", away.pitcher.whip, home.pitcher.whip, "lower"),
            ("K/9", away.pitcher.k_rate, home.pitcher.k_rate, "higher"),
            ("BB/9", away.pitcher.bb_rate, home.pitcher.bb_rate, "lower"),
            ("HR/9", away.pitcher.hr9, home.pitcher.hr9, "lower"),
        ]

        for label, away_value, home_value, direction in comparisons:
            reason = self._comparison_reason(
                label,
                away.name,
                away_value,
                home.name,
                home_value,
                direction,
            )

            if reason:
                reasons.append(reason)

        if not reasons:
            reasons.append("Starting pitching data unavailable or even")

        return reasons

    def _pitcher_score(self, pitcher):

        if self._missing_starter(pitcher):
            return 0.0

        metrics = []

        self._add_metric(
            metrics,
            "era",
            self._lower_better(
                pitcher.era,
                center=self._value_or_default(pitcher.league_era, 4.50),
                scale=1.50,
            ),
        )
        self._add_metric(
            metrics,
            "whip",
            self._lower_better(pitcher.whip, center=1.40, scale=0.30),
        )

        if pitcher.k_rate is not None and pitcher.bb_rate is not None:
            self._add_metric(
                metrics,
                "k_minus_bb",
                self._higher_better(
                    pitcher.k_rate - pitcher.bb_rate,
                    center=4.00,
                    scale=3.00,
                ),
            )

        self._add_metric(
            metrics,
            "hr9",
            self._lower_better(pitcher.hr9, center=1.00, scale=0.75),
        )

        if not metrics:
            return 0.0

        total_weight = sum(weight for _, weight in metrics)
        quality = sum(value * weight for value, weight in metrics) / total_weight

        stabilized_quality = quality * self._sample_stabilizer(pitcher.ip)

        return round(
            self._clamp(
                stabilized_quality + self._context_adjustment(pitcher),
                -1.0,
                1.0,
            ),
            3,
        )

    def _add_metric(self, metrics, name, value):
        if value is None:
            return

        metrics.append((value, self.METRIC_WEIGHTS[name]))

    def _lower_better(self, value, *, center, scale):
        if value is None:
            return None

        return self._clamp((center - float(value)) / scale, -1.0, 1.0)

    def _higher_better(self, value, *, center, scale):
        if value is None:
            return None

        return self._clamp((float(value) - center) / scale, -1.0, 1.0)

    def _sample_stabilizer(self, innings):
        if innings is None:
            return 0.75

        return self._clamp(float(innings) / 80.0, 0.25, 1.0)

    def _context_adjustment(self, pitcher):
        adjustment = 0.0

        if pitcher.days_rest is not None:
            if pitcher.days_rest <= 3:
                adjustment -= 0.08
            elif pitcher.days_rest >= 7:
                adjustment += 0.03

        if (
            pitcher.previous_start_ip is not None
            and pitcher.previous_start_ip >= 7.0
            and pitcher.days_rest is not None
            and pitcher.days_rest <= 4
        ):
            adjustment -= 0.04

        return self._clamp(adjustment, -0.10, 0.05)

    @staticmethod
    def _value_or_default(value, default):
        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp(value, minimum, maximum):
        return max(minimum, min(maximum, value))

    @staticmethod
    def _missing_starter(pitcher):
        return (
            pitcher.name is None
            or pitcher.name == "Unknown Starter"
            or getattr(pitcher, "starter_confirmed", False) is False
        )

    def _comparison_reason(
        self,
        label,
        away_name,
        away_value,
        home_name,
        home_value,
        direction,
    ):

        if away_value is None or home_value is None:
            return None

        if direction == "lower":
            if away_value < home_value:
                return f"{away_name} has the {label} advantage ({away_value:.2f} vs {home_value:.2f})"

            if home_value < away_value:
                return f"{home_name} has the {label} advantage ({home_value:.2f} vs {away_value:.2f})"

        if direction == "higher":
            if away_value > home_value:
                return f"{away_name} has the {label} advantage ({away_value:.2f} vs {home_value:.2f})"

            if home_value > away_value:
                return f"{home_name} has the {label} advantage ({home_value:.2f} vs {away_value:.2f})"

        return None

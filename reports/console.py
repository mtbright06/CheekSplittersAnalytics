class ConsoleReport:

    def print_schedule(self, games, logger):

        if not games:
            logger.write("=" * 60)
            logger.write("🔥 SHARPSTACK DAILY CARD")
            logger.write("=" * 60)
            logger.write("")
            logger.write("No confirmed KBO games with listed starters found.")
            logger.write("No card generated.")
            logger.write("=" * 60)
            return

        games = sorted(
            games,
            key=lambda g: g.result.edge,
            reverse=True
        )

        logger.write("=" * 60)
        logger.write("🔥 SHARPSTACK DAILY CARD")
        logger.write("=" * 60)
        logger.write("")

        best = games[0]

        logger.write("🔥 BET OF THE DAY")
        logger.write(f"{best.result.play} ({best.result.market})")
        logger.write(f"Edge: {best.result.edge}%")
        logger.write(f"Confidence: {best.result.confidence}/100")
        logger.write(self._play_rating(best.result.edge))
        logger.write("")

        logger.write("=" * 60)

        for game in games:

            logger.write("")
            logger.write(f"{game.away.name} @ {game.home.name}")
            logger.write("")
            logger.write("STARTING PITCHING")
            logger.write("")

            self._write_pitcher_block(
                logger,
                game.away.name,
                game.away.pitcher
            )

            logger.write("")

            self._write_pitcher_block(
                logger,
                game.home.name,
                game.home.pitcher
            )

            logger.write("")
            logger.write(f"Market: {game.result.market}")
            logger.write(f"Play: {game.result.play}")
            logger.write(f"Odds: {game.odds.moneyline}")
            logger.write(f"Book: {game.odds.book_probability}%")
            logger.write(f"Model: {game.result.model_probability}%")
            logger.write(f"Edge: {game.result.edge}%")
            logger.write(f"Confidence: {game.result.confidence}/100")
            logger.write(f"{game.result.recommendation}")

            logger.write("")
            logger.write(self._play_rating(game.result.edge))

            if game.result.reasons:

                logger.write("")
                logger.write("Why SharpStack likes this play:")

                for reason in game.result.reasons:

                    logger.write(f"  ✓ {reason}")

            logger.write("-" * 60)

    def _write_pitcher_block(self, logger, team_name, pitcher):

        logger.write(f"{team_name}: {self._pitcher_name_line(pitcher)}")

        if pitcher.name is None or pitcher.name == "Unknown Starter":
            logger.write("  Data unavailable")
            return

        logger.write(f"  Throws/Bats: {self._value(pitcher.throws)}/{self._value(pitcher.bats)}")
        logger.write(f"  Record: {self._value(pitcher.record)}")
        logger.write(f"  ERA: {self._number(pitcher.era)}")
        logger.write(f"  WHIP: {self._number(pitcher.whip)}")
        logger.write(f"  IP: {self._number(pitcher.ip)}")
        logger.write(f"  SO: {self._value(pitcher.so)}")
        logger.write(f"  BB: {self._value(pitcher.bb)}")
        logger.write(f"  HR Allowed: {self._value(pitcher.hr_allowed)}")
        logger.write(f"  K/9: {self._number(pitcher.k_rate)}")
        logger.write(f"  BB/9: {self._number(pitcher.bb_rate)}")
        logger.write(f"  HR/9: {self._number(pitcher.hr9)}")

    def _pitcher_name_line(self, pitcher):

        if not pitcher.name:
            return "Unknown Starter"

        parts = []

        if pitcher.throws:
            parts.append(f"{pitcher.throws}HP")

        if pitcher.record:
            parts.append(pitcher.record)

        if pitcher.era is not None:
            parts.append(f"{pitcher.era:.2f} ERA")

        if pitcher.whip is not None:
            parts.append(f"{pitcher.whip:.2f} WHIP")

        if parts:
            return f"{pitcher.name} ({' | '.join(parts)})"

        return pitcher.name

    def _number(self, value):

        if value is None:
            return "N/A"

        return f"{value:.2f}"

    def _value(self, value):

        if value is None:
            return "N/A"

        return str(value)

    def _play_rating(self, edge):

        if edge >= 10:
            return "★★★★★ ELITE PLAY"

        if edge >= 7:
            return "★★★★☆ STRONG PLAY"

        if edge >= 5:
            return "★★★☆☆ PLAYABLE"

        if edge >= 2:
            return "★★☆☆☆ LEAN"

        return "★☆☆☆☆ PASS"

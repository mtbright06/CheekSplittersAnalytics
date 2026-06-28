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

            away_pitcher = self._format_pitcher(game.away.pitcher)
            home_pitcher = self._format_pitcher(game.home.pitcher)

            logger.write(
                f"Pitching: {away_pitcher} vs {home_pitcher}"
            )

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

    def _format_pitcher(self, pitcher):

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

        if pitcher.k_rate is not None:
            parts.append(f"{pitcher.k_rate:.2f} K/9")

        if pitcher.bb_rate is not None:
            parts.append(f"{pitcher.bb_rate:.2f} BB/9")

        if pitcher.hr9 is not None:
            parts.append(f"{pitcher.hr9:.2f} HR/9")

        if parts:
            return f"{pitcher.name} ({' | '.join(parts)})"

        return pitcher.name

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

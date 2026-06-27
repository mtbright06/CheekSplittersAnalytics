class ConsoleReport:

    def print_schedule(self, games, logger):

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

        if pitcher.record:
            return f"{pitcher.name} ({pitcher.record}, {pitcher.era:.2f})"

        return f"{pitcher.name} ({pitcher.era:.2f})"

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

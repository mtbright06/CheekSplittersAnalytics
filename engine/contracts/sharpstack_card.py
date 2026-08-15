def get_value(obj, key, default=None):
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def normalize_card(card):
    sport = (get_value(card, "sport") or "unknown").lower()

    return {
        "sport": get_value(card, "sport"),
        "version": get_value(card, "version"),
        "generated_at": get_value(card, "generated_at"),
        "games": [
            normalize_game(game, sport)
            for game in get_value(card, "games", [])
        ],
    }


def normalize_game(game, sport):
    if (
        get_value(game, "matchup") is not None
        and get_value(game, "model") is not None
        and get_value(game, "pitching") is not None
    ):
        return normalize_new_game(game, sport)

    return normalize_legacy_kbo_game(game, sport)


def normalize_new_game(game, sport):
    teams = get_value(game, "teams", {})

    return {
        **to_dict(game),
        "sport": (get_value(game, "sport") or sport).lower(),
        "matchup": get_value(game, "matchup", {}),
        "teams": {
            "away": normalize_team(get_value(teams, "away", {})),
            "home": normalize_team(get_value(teams, "home", {})),
        },
        "model": normalize_model(get_value(game, "model", {})),
        "pitching": {
            "away": normalize_pitcher(get_value(get_value(game, "pitching", {}), "away", {})),
            "home": normalize_pitcher(get_value(get_value(game, "pitching", {}), "home", {})),
        },
        "odds": normalize_odds(get_value(game, "odds", {})),
        "market_edge": get_value(game, "market_edge", {}),
    }


def normalize_legacy_kbo_game(game, sport):
    away = get_value(game, "away", {})
    home = get_value(game, "home", {})
    result = get_value(game, "result", {})

    away_name = get_value(away, "name") or "Away"
    home_name = get_value(home, "name") or "Home"

    return {
        "sport": (get_value(game, "sport") or sport).lower(),
        "game_id": get_value(game, "game_id") or get_value(game, "game_url"),
        "game_date": get_value(game, "game_date"),
        "venue": get_value(game, "venue"),
        "start_time": get_value(game, "start_time"),
        "status": get_value(game, "status"),
        "matchup": {
            "away": away_name,
            "home": home_name,
        },
        "pitching": {
            "away": normalize_pitcher(get_value(away, "pitcher", {})),
            "home": normalize_pitcher(get_value(home, "pitcher", {})),
        },
        "teams": {
            "away": normalize_team(away),
            "home": normalize_team(home),
        },
        "model": normalize_model({
            "market": get_value(result, "market") or "Moneyline",
            "play": get_value(result, "play") or home_name,
            "model_win_strength": get_value(
                result,
                "model_win_strength",
            ),
            "model_probability": get_value(result, "model_probability"),
            "selected_team_model_strength": get_value(
                result,
                "selected_team_model_strength",
            ),
            "edge": get_value(result, "edge"),
            "model_confidence": get_value(result, "model_confidence"),
            "confidence": get_value(result, "confidence"),
            "confidence_breakdown": get_value(
                result,
                "confidence_breakdown",
                {},
            ),
            "recommendation": get_value(result, "recommendation"),
            "reasons": get_value(result, "reasons", []),
            "signals": get_value(result, "signals", []),
            "component_scores": get_value(result, "component_scores", {}),
            "configured_weights": get_value(result, "configured_weights", {}),
            "weighted_score": get_value(result, "weighted_score"),
            "shadow_model": get_value(result, "shadow_model"),
        }),
        "odds": normalize_odds(get_value(game, "odds", {})),
        "market_edge": get_value(game, "market_edge", {}),
    }


def normalize_team(team):
    return {
        **to_dict(team),
        "name": get_value(team, "name"),
        "record": get_value(team, "record"),
        "form": get_value(team, "form"),
        "offense": normalize_offense(get_value(team, "offense", {})),
        "bullpen": get_value(team, "bullpen", {}),
    }


def normalize_model(model):
    model_win_strength = (
        get_value(model, "model_win_strength")
        if get_value(model, "model_win_strength") is not None
        else get_value(model, "model_probability")
    )
    model_confidence = (
        get_value(model, "model_confidence")
        if get_value(model, "model_confidence") is not None
        else first_present(
            get_value(model, "model_reliability"),
            get_value(model, "reliability"),
            get_value(model, "confidence"),
        )
    )
    model_reliability = first_present(
        get_value(model, "model_reliability"),
        get_value(model, "reliability"),
        model_confidence,
    )

    return {
        **to_dict(model),
        "market": get_value(model, "market") or "Moneyline",
        "play": get_value(model, "play") or "No Play",
        "model_win_strength": model_win_strength,
        "model_strength": first_present(
            get_value(model, "model_strength"),
            model_win_strength,
        ),
        "model_probability": model_win_strength,
        "edge": get_value(model, "edge"),
        "model_reliability": model_reliability,
        "reliability": model_reliability,
        "model_confidence": model_confidence,
        "confidence": model_confidence,
        "legacy_model_confidence": get_value(
            model,
            "legacy_model_confidence",
        ),
        "confidence_breakdown": get_value(
            model,
            "confidence_breakdown",
            {},
        ),
        "recommendation": get_value(model, "recommendation"),
        "reasons": get_value(model, "reasons", []),
        "signals": normalize_signals(get_value(model, "signals", [])),
        "component_scores": get_value(model, "component_scores", {}),
    }


def normalize_pitcher(pitcher):
    return {
        **to_dict(pitcher),
        "id": get_value(pitcher, "id"),
        "name": get_value(pitcher, "name") or "Unknown Starter",
        "throws": get_value(pitcher, "throws"),
        "bats": get_value(pitcher, "bats"),
        "record": get_value(pitcher, "record"),
        "era": get_value(pitcher, "era"),
        "whip": get_value(pitcher, "whip"),
        "ip": get_value(pitcher, "ip"),
        "so": get_value(pitcher, "so"),
        "bb": get_value(pitcher, "bb"),
        "hr_allowed": get_value(pitcher, "hr_allowed"),
        "k_rate": get_value(pitcher, "k_rate"),
        "bb_rate": get_value(pitcher, "bb_rate"),
        "hr9": get_value(pitcher, "hr9"),
    }


def normalize_offense(offense):
    return {
        "runs_per_game": get_value(offense, "runs_per_game"),
        "league_runs_per_game": get_value(
            offense,
            "league_runs_per_game",
        ),
        "offense_source": get_value(offense, "offense_source"),
        "runs_allowed_per_game": get_value(
            offense,
            "runs_allowed_per_game",
        ),
        "home_runs_per_game": get_value(
            offense,
            "home_runs_per_game",
        ),
        "away_runs_per_game": get_value(
            offense,
            "away_runs_per_game",
        ),
        "home_games": get_value(offense, "home_games"),
        "away_games": get_value(offense, "away_games"),
        "source_url": get_value(offense, "source_url"),
        "retrieved_at": get_value(offense, "retrieved_at"),
        "source_row": get_value(offense, "source_row"),
        "avg": get_value(offense, "avg"),
        "obp": get_value(offense, "obp"),
        "slg": get_value(offense, "slg"),
        "ops": get_value(offense, "ops"),
        "hr": get_value(offense, "hr"),
        "hr_per_game": get_value(offense, "hr_per_game"),
        "bb": get_value(offense, "bb"),
        "so": get_value(offense, "so"),
        "bb_rate": get_value(offense, "bb_rate"),
        "k_rate": get_value(offense, "k_rate"),
        "iso": get_value(offense, "iso"),
        "woba": get_value(offense, "woba"),
        "wrc_plus": get_value(offense, "wrc_plus"),
    }


def normalize_odds(odds):
    return {
        **to_dict(odds),
        "provider": get_value(odds, "provider"),
        "sportsbook": get_value(odds, "sportsbook") or get_value(odds, "source") or "Unavailable",
        "market": get_value(odds, "market") or "Moneyline",
        "selection": get_value(odds, "selection"),
        "moneyline": first_present(get_value(odds, "moneyline"), get_value(odds, "american_odds")),
        "american_odds": first_present(get_value(odds, "american_odds"), get_value(odds, "moneyline")),
        "book_probability": first_present(get_value(odds, "book_probability"), get_value(odds, "implied_probability")),
        "implied_probability": first_present(get_value(odds, "implied_probability"), get_value(odds, "book_probability")),
        "last_updated": get_value(odds, "last_updated"),
    }


def normalize_signals(signals):
    normalized = []

    if not signals:
        return normalized

    for index, signal in enumerate(signals):
        if isinstance(signal, dict):
            normalized.append({
                "name": signal.get("name") or f"Signal {index + 1}",
                "value": signal.get("value", 0),
            })
        elif isinstance(signal, (list, tuple)) and len(signal) >= 2:
            normalized.append({
                "name": str(signal[0]),
                "value": signal[1] or 0,
            })
        else:
            normalized.append({
                "name": str(signal),
                "value": 0,
            })

    return normalized


def first_present(*values):
    for value in values:
        if value is not None:
            return value

    return None


def to_dict(obj):
    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj

    if hasattr(obj, "__dict__"):
        return {
            key: value
            for key, value in obj.__dict__.items()
            if not key.startswith("_")
        }

    return {}

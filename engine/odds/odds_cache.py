import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "output" / "odds_cache"


def cache_path(provider, league, market):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{provider}_{league}_{market}.json".lower()


def write_cache(provider, league, market, data):
    path = cache_path(provider, league, market)

    payload = {
        "provider": provider,
        "league": league,
        "market": market,
        "cached_at": datetime.now().isoformat(timespec="seconds"),
        "data": data,
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return path


def read_cache(provider, league, market):
    path = cache_path(provider, league, market)

    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

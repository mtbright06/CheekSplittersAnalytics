"""Local-only, sport-aware player imagery. No provider imports or requests."""
from functools import lru_cache
import json
from pathlib import Path
import re
from PIL import Image

ASSET_ROOT = Path(__file__).resolve().parents[1] / 'assets' / 'players'


@lru_cache(maxsize=2048)
def _valid_image(path: str, modified: int) -> bool:
    try:
        with Image.open(path) as image:
            image.verify()
        return True
    except (OSError, ValueError, Image.DecompressionBombError):
        return False


def _readable(path: Path) -> bool:
    try:
        return path.is_file() and _valid_image(str(path), path.stat().st_mtime_ns)
    except OSError:
        return False


@lru_cache(maxsize=16)
def _manifest(path: str, modified: int) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        return value.get('players', {}) if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def get_player_headshot(sport: str, player_id: str, *, asset_root=ASSET_ROOT) -> Path | None:
    """Return a manifest-backed image, sport fallback, or None for initials UI."""
    root = Path(asset_root)
    sport = str(sport).lower()
    if not re.fullmatch(r'[a-z0-9_-]+', sport):
        return None
    directory = root / sport
    fallback = directory / 'fallback.png'
    fallback = fallback if _readable(fallback) else None
    try:
        path = directory / 'manifest.json'
        entries = _manifest(str(path), path.stat().st_mtime_ns)
        entry = entries.get(str(player_id), {})
        if not isinstance(entry, dict) or entry.get('status') != 'available':
            return fallback
        filename = entry.get('filename')
        if not isinstance(filename, str):
            return fallback
        image = (directory / filename).resolve()
        if not image.is_relative_to(directory.resolve()) or image.suffix.lower() not in {'.png', '.webp', '.jpg', '.jpeg'}:
            return fallback
        return image if _readable(image) else fallback
    except (OSError, ValueError, AttributeError, TypeError):
        return fallback

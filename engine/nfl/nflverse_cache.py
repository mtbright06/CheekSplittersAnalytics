from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time
import uuid
from typing import Callable

import requests


DEFAULT_CACHE_DIR = Path("data/nfl/cache/nflverse")
NEGATIVE_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class NFLVerseCacheResult:
    text: str | None
    source: str


class NFLVerseBulkCache:
    """Known-good disk cache for public nflverse bulk CSV assets."""

    def __init__(
        self,
        *,
        cache_dir: Path | str = DEFAULT_CACHE_DIR,
        fetcher=requests.get,
        clock=time.time,
        negative_ttl_seconds: int = NEGATIVE_CACHE_TTL_SECONDS,
    ) -> None:
        self._cache_dir = Path(cache_dir)
        self._fetcher = fetcher
        self._clock = clock
        self._negative_ttl_seconds = int(negative_ttl_seconds)

    def load_csv(
        self,
        *,
        key: str,
        url: str,
        validator: Callable[[str], bool],
        max_age_seconds: int,
    ) -> NFLVerseCacheResult:
        cache_path = self._cache_dir / f"{key}.csv"
        negative_path = self._cache_dir / f"{key}.unavailable"
        cached = self._valid_cached_text(cache_path, validator)
        if cached is not None and self._age(cache_path) < max_age_seconds:
            return NFLVerseCacheResult(cached, "disk")
        if cached is None and self._age(negative_path) < self._negative_ttl_seconds:
            return NFLVerseCacheResult(None, "negative_cache")

        try:
            response = self._fetcher(
                url,
                timeout=30,
                headers={"User-Agent": "SharpStack/1.0 personal analytics"},
            )
            response.raise_for_status()
            expected_length = getattr(response, "headers", {}).get("Content-Length")
            if expected_length is not None and int(expected_length) != len(response.content):
                raise ValueError("partial_nflverse_download")
            text = str(response.text or "")
            if not validator(text):
                raise ValueError("invalid_nflverse_csv")
        except Exception:
            if cached is not None:
                return NFLVerseCacheResult(cached, "stale_disk")
            try:
                self._atomic_write(negative_path, str(int(self._clock())))
            except OSError:
                pass
            return NFLVerseCacheResult(None, "unavailable")

        try:
            self._atomic_write(cache_path, text)
        except OSError:
            return NFLVerseCacheResult(text, "network")
        try:
            negative_path.unlink(missing_ok=True)
        except OSError:
            pass
        return NFLVerseCacheResult(text, "network")

    def _valid_cached_text(
        self, path: Path, validator: Callable[[str], bool]
    ) -> str | None:
        try:
            text = path.read_text(encoding="utf-8")
            return text if validator(text) else None
        except (OSError, UnicodeError):
            return None

    def _age(self, path: Path) -> float:
        try:
            return max(0.0, self._clock() - path.stat().st_mtime)
        except OSError:
            return float("inf")

    @staticmethod
    def _atomic_write(path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_text(text, encoding="utf-8")
            os.replace(temporary, path)
        finally:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

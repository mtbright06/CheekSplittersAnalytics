"""Build local NFL headshots from nflverse identity and weekly roster CSVs.

nflverse data: https://github.com/nflverse/nflverse-data (CC BY 4.0).
Photo source attribution is recorded per image; the data license does not
represent a separate license grant for NFL photography.
Run: python3 tools_build_nfl_player_assets.py --season 2026
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, UTC
from io import BytesIO, StringIO
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit
import uuid

from PIL import Image, ImageDraw, ImageOps
import requests

from app.player_assets import ASSET_ROOT
from engine.nfl.nflverse_cache import NFLVerseBulkCache
from engine.nfl.players import PLAYERS_URL
from engine.nfl.rosters import WEEKLY_ROSTERS_URL
from engine.nfl.teams import normalize_nfl_abbreviation


def candidates(players, rosters, season, week=None):
    rows = [r for r in rosters if r.get('season') == str(season)]
    weeks = [int(r['week']) for r in rows if str(r.get('week', '')).isdigit()]
    if not weeks:
        raise ValueError('No weekly roster context available')
    week = max(weeks) if week is None else week
    registry = {r['gsis_id']: r for r in players if r.get('gsis_id')}
    selected = {}
    for row in rows:
        if str(row.get('week')) != str(week) or row.get('position') not in {'QB', 'RB', 'WR', 'TE'}:
            continue
        if row.get('status') in {'CUT', 'RET'}:
            continue
        player_id = row.get('gsis_id', '')
        if not re.fullmatch(r'\d{2}-\d{7}', player_id):
            continue
        identity = registry.get(player_id, {})
        entry = dict(player_id=player_id, display_name=identity.get('display_name') or row.get('full_name'),
                     team=normalize_nfl_abbreviation(row.get('team')), position=row['position'],
                     source_url=identity.get('headshot') or row.get('headshot_url') or None)
        # Stable tie-break for duplicate membership rows; no identity is created by name.
        if player_id not in selected or str(entry['team']) < str(selected[player_id]['team']):
            selected[player_id] = entry
    return week, [selected[key] for key in sorted(selected)]


def image_bytes(content):
    with Image.open(BytesIO(content)) as probe:
        if probe.format not in {'PNG', 'WEBP', 'JPEG'}:
            raise ValueError('Unsupported image format')
        probe.verify()
    with Image.open(BytesIO(content)) as source:
        source.load()
        original = dict(source_dimensions=list(source.size), source_format=source.format)
        image = ImageOps.exif_transpose(source).convert('RGBA')
        image.thumbnail((512, 512), Image.Resampling.LANCZOS)
        output = BytesIO()
        image.save(output, format='WEBP', quality=90, method=4)
        return output.getvalue(), original


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def request_url(url):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname:
        raise ValueError('Expected HTTPS image URL')
    if parts.hostname == 'static.www.nfl.com' and '/image/upload/' in parts.path:
        return urlunsplit(parts._replace(path=parts.path.replace(
            '/image/upload/', '/image/upload/c_limit,w_512,h_512/', 1)))
    return url


def acquire(entry, directory, previous=None, *, fetcher=requests.get, refresh=False):
    entry = dict(entry)
    path = directory / 'headshots' / (entry['player_id'] + '.webp')
    previous = previous or {}
    valid = False
    if path.is_file():
        try:
            image_bytes(path.read_bytes())
            valid = True
        except Exception:
            pass
    if valid and not refresh and previous.get('source_url') == entry['source_url']:
        return {**previous, **entry, 'status': 'available', 'filename': path.relative_to(directory).as_posix()}, 'reused'
    failure = 'no_source'
    if entry['source_url']:
        try:
            url = request_url(entry['source_url'])
            with fetcher(url, timeout=20, stream=True) as response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(65536):
                    content.extend(chunk)
                    if len(content) > 10 * 1024 * 1024:
                        raise ValueError('Image download exceeds 10 MiB')
            try:
                data, metadata = image_bytes(content)
            except Exception:
                failure = 'invalid_image'
            else:
                atomic_write(path, data)
                return {**entry, **metadata, 'status': 'available',
                        'filename': path.relative_to(directory).as_posix(), 'request_url': url,
                        'retrieved_at': datetime.now(UTC).isoformat()}, 'downloaded'
        except Exception:
            failure = 'download_failed'
    if valid and previous.get('status') == 'available':
        return {**previous, 'refresh_status': failure}, failure
    return {**entry, 'status': failure, 'filename': None, 'retrieved_at': None}, failure


def build(*, season, week=None, output=ASSET_ROOT / 'nfl', cache=None, refresh=False, limit=None):
    cache = cache or NFLVerseBulkCache()
    def load(key, url, fields):
        result = cache.load_csv(key=key, url=url, max_age_seconds=86400,
            validator=lambda text: fields <= set(csv.DictReader(StringIO(text)).fieldnames or ()))
        if not result.text:
            raise ValueError(f'{key} unavailable; existing manifest preserved')
        return list(csv.DictReader(StringIO(result.text)))
    players = load('players', PLAYERS_URL, {'gsis_id', 'headshot'})
    rosters = load(f'weekly_roster_{season}', WEEKLY_ROSTERS_URL.format(season=season), {'gsis_id', 'week', 'season'})
    week, entries = candidates(players, rosters, season, week)
    if not entries:
        raise ValueError('Empty candidate universe; manifest preserved')
    if limit:
        entries = entries[:limit]
    output = Path(output)
    manifest = output / 'manifest.json'
    previous = json.loads(manifest.read_text())['players'] if manifest.exists() else {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda e: acquire(e, output, previous.get(e['player_id']), refresh=refresh), entries))
    updated = {**previous, **{e['player_id']: e for e, _ in results}}
    payload = dict(schema_version=1, sport='nfl', season=season, week=week,
                   source=PLAYERS_URL, players=updated)
    atomic_write(manifest, (json.dumps(payload, indent=2, sort_keys=True) + '\n').encode())
    fallback = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fallback)
    draw.ellipse((43, 16, 85, 58), fill='#8fa3b7')
    draw.rounded_rectangle((23, 67, 105, 125), radius=28, fill='#8fa3b7')
    buffer = BytesIO()
    fallback.save(buffer, format='PNG')
    atomic_write(output / 'fallback.png', buffer.getvalue())
    sizes = [p.stat().st_size for p in (output / 'headshots').glob('*.webp')]
    report = dict(candidates=len(entries), week=week, counts=dict(Counter(s for _, s in results)),
                  total_bytes=sum(p.stat().st_size for p in output.rglob('*') if p.is_file()),
                  average_headshot_bytes=int(sum(sizes) / len(sizes)) if sizes else 0,
                  largest_headshot_bytes=max(sizes, default=0))
    print(json.dumps(report, indent=2), flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season', type=int, required=True)
    parser.add_argument('--week', type=int)
    parser.add_argument('--output', type=Path, default=ASSET_ROOT / 'nfl')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--limit', type=int)
    build(**vars(parser.parse_args()))

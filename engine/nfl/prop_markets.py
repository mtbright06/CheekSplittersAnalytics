"""NFL event-scoped player quotes from The Odds API v4.

Contract: https://the-odds-api.com/liveapi/guides/v4/#get-event-odds
Markets: https://the-odds-api.com/sports-odds-data/betting-markets.html
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
import math
import os
import re
from threading import RLock
import unicodedata
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from engine.nfl.models import NFLGame, NFLRosterEntry
from engine.nfl.prop_trends import (
    ANYTIME_TOUCHDOWN, PASSING_TOUCHDOWNS, PASSING_YARDS,
    RECEIVING_YARDS, RECEPTIONS, RUSHING_YARDS,
)

BASE_URL = 'https://api.the-odds-api.com/v4/sports/americanfootball_nfl'
MARKET_KEYS = {
    PASSING_YARDS: 'player_pass_yds',
    PASSING_TOUCHDOWNS: 'player_pass_tds',
    RUSHING_YARDS: 'player_rush_yds',
    RECEIVING_YARDS: 'player_reception_yds',
    RECEPTIONS: 'player_receptions',
    ANYTIME_TOUCHDOWN: 'player_anytime_td',
}
BOOKS = ('fanduel', 'fanatics')
MARKET_TTL = 300


@dataclass(frozen=True)
class NFLPlayerPropMarket:
    game_id: str
    event_id: str
    commence_time: datetime
    market: str
    provider_market: str
    player_name: str
    sportsbook: str
    book_key: str
    line: float | None
    over_price: int | None
    under_price: int | None
    updated_at: datetime | None
    retrieved_at: datetime
    roster_entry: NFLRosterEntry | None = None
    source: str = 'the_odds_api'
    concerns: tuple[str, ...] = ()

    @property
    def research_line(self) -> float:
        # Yes/No anytime scorer is equivalent to exceeding 0.5 factual TDs.
        if self.market == ANYTIME_TOUCHDOWN:
            return 0.5
        if self.line is None:
            raise ValueError('Numeric market has no quoted line')
        return self.line

    @property
    def player_id(self) -> str | None:
        return self.roster_entry.player_id if self.roster_entry else None


@dataclass(frozen=True)
class NFLPropMarketBatch:
    quotes: tuple[NFLPlayerPropMarket, ...] = ()
    concerns: tuple[str, ...] = ()


def _timestamp(value) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        return parsed.astimezone(UTC) if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def _number(value) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _name(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).casefold()
    return ''.join(c for c in value if c.isalnum())


def _without_suffix(value: str) -> str:
    # Suffix omission is accepted only when unique within the event's roster.
    return _name(re.sub(r'\s+(jr\.?|sr\.?|ii|iii|iv)$', '', value.strip(), flags=re.I))


def resolve_market_player(name: str, entries) -> tuple[NFLRosterEntry | None, str | None]:
    entries = tuple(e for e in entries if e.player_id and e.player)
    exact = {(e.player_id, e.team_abbreviation): e for e in entries if _name(e.player.name) == _name(name)}
    if not exact:
        exact = {(e.player_id, e.team_abbreviation): e for e in entries
                 if _without_suffix(e.player.name) == _without_suffix(name)}
    if len(exact) == 1:
        return next(iter(exact.values())), None
    return None, 'player_identity_ambiguous' if exact else 'player_identity_unresolved'


def normalize_prop_markets(payload, game: NFLGame, market: str, entries, now: datetime) -> NFLPropMarketBatch:
    if not isinstance(payload, dict) or not payload.get('id') or market not in MARKET_KEYS:
        return NFLPropMarketBatch(concerns=('market_payload_invalid',))
    start = _timestamp(payload.get('commence_time'))
    if not start or not _matches_game(payload, game):
        return NFLPropMarketBatch(concerns=('event_identity_mismatch',))
    entries = tuple(e for e in entries if e.season == game.season and e.week == game.week
                    and e.game_type in (None, 'REG') and e.team_abbreviation in
                    {game.away_team.abbreviation, game.home_team.abbreviation})
    quotes, concerns = [], []
    for book in _records(payload.get('bookmakers')):
        if book.get('key') not in BOOKS:
            continue
        for raw_market in _records(book.get('markets')):
            if raw_market.get('key') != MARKET_KEYS.get(market):
                continue
            groups = {}
            for outcome in _records(raw_market.get('outcomes')):
                name = outcome.get('description')
                side = str(outcome.get('name', '')).lower()
                anytime = market == ANYTIME_TOUCHDOWN
                price = _number(outcome.get('price'))
                line = None if anytime else _number(outcome.get('point'))
                if not name or price is None or abs(price) < 100 or price != int(price):
                    concerns.append('malformed_outcome'); continue
                if side not in (('yes', 'no') if anytime else ('over', 'under')) or (not anytime and (line is None or line < 0)):
                    concerns.append(f'unsupported_outcome:{name}'); continue
                group = groups.setdefault((name, line), {})
                if side in group and group[side] != int(price):
                    group['conflict'] = True
                group[side] = int(price)
            for (name, line), prices in groups.items():
                if prices.get('conflict'):
                    concerns.append(f'conflicting_quote:{name}'); continue
                entry, issue = resolve_market_player(name, entries)
                updated = _timestamp(raw_market.get('last_update') or book.get('last_update'))
                quote_concerns = [issue] if issue else []
                if updated is None:
                    quote_concerns.append('market_timestamp_unknown')
                elif (now - updated).total_seconds() > MARKET_TTL:
                    quote_concerns.append('market_stale')
                over = prices.get('yes' if market == ANYTIME_TOUCHDOWN else 'over')
                under = prices.get('no' if market == ANYTIME_TOUCHDOWN else 'under')
                if over is None or under is None:
                    quote_concerns.append('one_sided_quote')
                quotes.append(NFLPlayerPropMarket(
                    game.source_game_id, str(payload['id']), start, market, MARKET_KEYS[market],
                    name, 'FanDuel' if book['key'] == 'fanduel' else 'Fanatics', book['key'],
                    line, over, under, updated, now, entry, concerns=tuple(quote_concerns),
                ))
    # Never choose an arbitrary alternate if a provider sends multiple main lines.
    grouped = {}
    for quote in quotes:
        key = (quote.player_id or _name(quote.player_name), quote.market, quote.book_key)
        grouped.setdefault(key, []).append(quote)
    unique = []
    for group in grouped.values():
        if len({q.line for q in group}) != 1:
            concerns.append(f'ambiguous_main_line:{group[0].player_name}'); continue
        unique.append(group[0])
    preferred = {}
    for quote in sorted(unique, key=lambda q: (BOOKS.index(q.book_key), q.player_name)):
        preferred.setdefault((quote.player_id or _name(quote.player_name), quote.market), quote)
    return NFLPropMarketBatch(tuple(preferred.values()), tuple(dict.fromkeys(concerns)))


def _records(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _matches_game(event, game: NFLGame) -> bool:
    start = _timestamp(event.get('commence_time'))
    return bool(start and start.astimezone(ZoneInfo('America/New_York')).date() == game.game_date
                and _name(event.get('away_team', '')) == _name(game.away_team.full_name)
                and _name(event.get('home_team', '')) == _name(game.home_team.full_name))


class NFLPropMarketProvider:
    """Short-lived, process-local, event/market cache; failures never serve old quotes."""

    def __init__(self, *, api_key=None, fetcher=requests.get, clock=None):
        load_dotenv()
        self._api_key = api_key if api_key is not None else os.getenv('ODDS_API_KEY')
        self._fetcher = fetcher
        self._clock = clock or (lambda: datetime.now(UTC))
        self._cache = {}
        self._lock = RLock()

    def _get(self, path, params, *, refresh=False):
        key = (path, tuple(sorted(params.items())))
        with self._lock:
            now = self._clock()
            cached = self._cache.get(key)
            if cached and (now - cached[0]).total_seconds() < (60 if cached[2] else MARKET_TTL) and not refresh:
                return cached[1], cached[2], cached[0]
            if not self._api_key:
                return None, 'odds_api_key_missing', now
            try:
                response = self._fetcher(BASE_URL + path, params={**params, 'apiKey': self._api_key}, timeout=20)
                if response.status_code != 200:
                    raise ValueError(f'odds_http_{response.status_code}')
                payload = response.json()
                if not isinstance(payload, list if path == '/events' else dict):
                    raise ValueError('odds_payload_invalid')
                concern = None
            except (requests.RequestException, ValueError):
                # Exception strings can contain credential-bearing URLs.
                payload, concern = None, 'odds_provider_unavailable'
            self._cache[key] = (now, payload, concern)
            return payload, concern, now

    def load_game(self, game: NFLGame, market: str, entries, *, refresh=False) -> NFLPropMarketBatch:
        if market not in MARKET_KEYS:
            return NFLPropMarketBatch(concerns=('unsupported_market',))
        if game.game_date < self._clock().astimezone(ZoneInfo('America/New_York')).date():
            return NFLPropMarketBatch(concerns=('historical_market_quotes_unavailable',))
        events, issue, _ = self._get('/events', {}, refresh=False)
        if issue:
            return NFLPropMarketBatch(concerns=(issue,))
        matches = [e for e in _records(events) if _matches_game(e, game) and e.get('id')]
        if len(matches) != 1:
            return NFLPropMarketBatch(concerns=('market_event_unresolved',))
        event_id = matches[0]['id']
        payload, issue, retrieved = self._get(f'/events/{event_id}/odds', {
            'markets': MARKET_KEYS[market], 'bookmakers': ','.join(BOOKS), 'oddsFormat': 'american',
        }, refresh=refresh)
        if issue:
            return NFLPropMarketBatch(concerns=(issue,))
        if payload.get('id') != event_id:
            return NFLPropMarketBatch(concerns=('event_identity_mismatch',))
        batch = normalize_prop_markets(payload, game, market, entries, self._clock())
        return replace(batch, quotes=tuple(replace(q, retrieved_at=retrieved) for q in batch.quotes))

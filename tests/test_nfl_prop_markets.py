from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from engine.nfl.models import NFLGame, NFLPlayer, NFLRosterEntry, NFLPlayerGameLog
from engine.nfl.teams import nfl_team_from_abbreviation
from engine.nfl.prop_markets import (
    NFLPropMarketProvider, MARKET_KEYS, normalize_prop_markets, resolve_market_player,
)
from engine.nfl.player_game_logs import NFLPlayerGameLogBatch
from engine.nfl.prop_trend_service import NFLPropTrendReadService
from engine.nfl.prop_trends import RUSHING_YARDS, ANYTIME_TOUCHDOWN

NOW = datetime(2026, 9, 9, 12, tzinfo=UTC)


def game():
    return NFLGame('2026_01_NE_SEA', 2026, 1, 'REG', date(2026, 9, 9),
                   datetime(2026, 9, 10, 0, tzinfo=UTC),
                   nfl_team_from_abbreviation('NE'), nfl_team_from_abbreviation('SEA'), 'SCHEDULED')


def entries():
    return [NFLRosterEntry(pid, 'SEA', 2026, week=1, game_type='REG', position='RB',
                           player=NFLPlayer(pid, name, position='RB'))
            for pid, name in [('01', 'Alpha Runner Jr.'), ('02', 'Beta Runner'), ('03', 'No Market')]]


def payload(book='fanduel', lines=(27.5, 68.5), market=RUSHING_YARDS):
    outcomes = []
    for name, line in zip(('Alpha Runner Jr.', 'Beta Runner'), lines):
        for side, price in [('Over', -110), ('Under', 105)]:
            outcomes.append(dict(name=side, description=name, price=price, point=line))
    return dict(id='event1', away_team='New England Patriots', home_team='Seattle Seahawks',
                commence_time='2026-09-10T00:00:00Z', bookmakers=[{
                    'key': book, 'title': book, 'markets': [{'key': MARKET_KEYS[market],
                    'last_update': NOW.isoformat(), 'outcomes': outcomes}]}])


def test_distinct_lines_paired_prices_and_book_priority():
    data = payload()
    data['bookmakers'] += payload('fanatics', (30.5, 70.5))['bookmakers']
    batch = normalize_prop_markets(data, game(), RUSHING_YARDS, entries(), NOW)
    assert len(batch.quotes) == 2
    assert [q.line for q in batch.quotes] == [27.5, 68.5]
    assert {q.sportsbook for q in batch.quotes} == {'FanDuel'}
    assert {(q.over_price, q.under_price) for q in batch.quotes} == {(-110, 105)}
    assert {q.player_id for q in batch.quotes} == {'01', '02'}


def test_fanatics_fallback_never_combines_books():
    data = payload('fanatics')
    batch = normalize_prop_markets(data, game(), RUSHING_YARDS, entries(), NOW)
    assert all(q.sportsbook == 'Fanatics' for q in batch.quotes)


def test_different_lines_do_not_pair_over_under_or_choose_arbitrary_line():
    data = payload()
    data['bookmakers'][0]['markets'][0]['outcomes'][1]['point'] = 99.5
    batch = normalize_prop_markets(data, game(), RUSHING_YARDS, entries(), NOW)
    assert [q.player_id for q in batch.quotes] == ['02']
    assert any('ambiguous_main_line' in c for c in batch.concerns)


def test_identity_suffix_punctuation_and_ambiguity():
    assert resolve_market_player('Alpha Runner Jr', entries())[0].player_id == '01'
    assert resolve_market_player('Alpha Runner', entries())[0].player_id == '01'
    extra = replace(entries()[0], player_id='other', player=NFLPlayer('other', 'Alpha Runner Sr.'))
    assert resolve_market_player('Alpha Runner', [*entries(), extra]) == (None, 'player_identity_ambiguous')
    assert resolve_market_player('Alfa Runner', entries()) == (None, 'player_identity_unresolved')
    assert resolve_market_player("DAndre Swift", [replace(entries()[0], player=NFLPlayer('01', "D'Andre Swift"))])[0]


def test_unmatched_and_wrong_week_remain_observable():
    batch = normalize_prop_markets(payload(), game(), RUSHING_YARDS,
                                   [replace(e, week=2) for e in entries()], NOW)
    assert len(batch.quotes) == 2
    assert all(q.player_id is None and 'player_identity_unresolved' in q.concerns for q in batch.quotes)


def test_anytime_yes_is_not_a_fabricated_numeric_book_line():
    data = payload(market=ANYTIME_TOUCHDOWN)
    data['bookmakers'][0]['markets'][0]['outcomes'] = [
        {'name': 'Yes', 'description': 'Beta Runner', 'price': 155}]
    quote = normalize_prop_markets(data, game(), ANYTIME_TOUCHDOWN, entries(), NOW).quotes[0]
    assert quote.line is None
    assert quote.research_line == 0.5
    assert quote.over_price == 155 and quote.under_price is None
    assert 'one_sided_quote' in quote.concerns


def test_timestamp_stale_and_invalid_event_are_explicit():
    batch = normalize_prop_markets(payload(), game(), RUSHING_YARDS, entries(), NOW + timedelta(minutes=6))
    assert all('market_stale' in q.concerns for q in batch.quotes)
    data = payload()
    data['home_team'] = 'Kansas City Chiefs'
    assert normalize_prop_markets(data, game(), RUSHING_YARDS, entries(), NOW).concerns == ('event_identity_mismatch',)


def test_cache_ttl_failure_cooldown_recovery_and_refresh():
    calls, now = [], [NOW]
    fail = [False]

    class Response:
        status_code = 200
        def __init__(self, value):
            self.value = value
            if fail[0]: self.status_code = 429
        def json(self): return self.value

    def fetch(url, **kwargs):
        calls.append((url, kwargs['params']))
        return Response([payload()] if url.endswith('/events') else payload())

    provider = NFLPropMarketProvider(api_key='test', fetcher=fetch, clock=lambda: now[0])
    first = provider.load_game(game(), RUSHING_YARDS, entries())
    assert len(calls) == 2
    assert provider.load_game(game(), RUSHING_YARDS, entries()) == first
    assert len(calls) == 2
    provider.load_game(game(), RUSHING_YARDS, entries(), refresh=True)
    assert len(calls) == 3
    now[0] += timedelta(minutes=6)
    fail[0] = True
    assert not provider.load_game(game(), RUSHING_YARDS, entries()).quotes
    count = len(calls)
    provider.load_game(game(), RUSHING_YARDS, entries())
    assert len(calls) == count
    fail[0] = False
    now[0] += timedelta(seconds=61)
    assert provider.load_game(game(), RUSHING_YARDS, entries()).quotes


def test_no_credentials_and_historical_date_never_fetch():
    def fail(*args, **kwargs): raise AssertionError('network forbidden')
    provider = NFLPropMarketProvider(api_key='', fetcher=fail, clock=lambda: NOW)
    assert provider.load_game(game(), RUSHING_YARDS, entries()).concerns == ('odds_api_key_missing',)
    old = replace(game(), game_date=date(2025, 9, 9))
    assert provider.load_game(old, RUSHING_YARDS, entries()).concerns == ('historical_market_quotes_unavailable',)


class History:
    def __init__(self): self.calls = 0
    def load_player_game_logs(self, *, season, game_type, player_ids):
        self.calls += 1
        logs = tuple(NFLPlayerGameLog(
            e.player_id, e.player, e.player.name, f'2025_01_{e.player_id}', date(2025, 9, 9),
            2025, 1, 'REG', 'SEA', 'NE', 'HOME', rushing_yards=50,
            rushing_touchdowns=0, receiving_touchdowns=0, special_teams_touchdowns=0,
        ) for e in entries() if e.player_id in player_ids) if season == 2025 else ()
        return NFLPlayerGameLogBatch(season, game_type, logs)


def test_own_line_drives_trends_no_usage_gate_and_no_refetch_for_alternates():
    quotes = normalize_prop_markets(payload(), game(), RUSHING_YARDS, entries(), NOW).quotes
    history = History()
    service = NFLPropTrendReadService(game_log_provider=history)
    rows = service.build_market_rows(quotes, selected_season=2026, before_date=game().game_date)
    assert len(rows) == 2  # No-market roster player never enters.
    assert [r.trend.last_10.hit_rate for r in rows] == [1.0, 0.0]
    assert [r.trend.selected_line for r in rows] == [27.5, 68.5]
    assert all(r.trend.season.hit_rate is None for r in rows)
    assert all(r.trend.previous_season.games_considered == 1 for r in rows)
    assert history.calls == 2
    nearby = service.nearby_thresholds(rows[0].trend, [27.5, 50, 68.5])
    assert nearby[50]['LAST_10'].pushes == 1
    assert nearby[50]['LAST_10'].hit_rate is None
    assert quotes[0].line == 27.5
    service.build_market_rows(quotes, selected_season=2026)
    assert history.calls == 2


def test_market_without_history_remains_na_not_zero():
    class Empty(History):
        def load_player_game_logs(self, **kwargs):
            return NFLPlayerGameLogBatch(kwargs['season'], kwargs['game_type'])
    quotes = normalize_prop_markets(payload(), game(), RUSHING_YARDS, entries(), NOW).quotes
    rows = NFLPropTrendReadService(game_log_provider=Empty()).build_market_rows(quotes, selected_season=2026)
    assert all(r.trend.last_10.hit_rate is None for r in rows)


@pytest.mark.parametrize('market', list(MARKET_KEYS))
def test_all_documented_market_contracts(market):
    data = payload(market=market)
    if market == ANYTIME_TOUCHDOWN:
        for outcome in data['bookmakers'][0]['markets'][0]['outcomes']:
            outcome['name'] = 'Yes' if outcome['name'] == 'Over' else 'No'
            outcome.pop('point')
    batch = normalize_prop_markets(data, game(), market, entries(), NOW)
    assert len(batch.quotes) == 2
    assert all(q.market == market and q.provider_market == MARKET_KEYS[market] for q in batch.quotes)


@pytest.mark.parametrize('bad', [None, [], {}, {'id': 'event1', 'bookmakers': None}])
def test_malformed_payload_is_safe(bad):
    assert not normalize_prop_markets(bad, game(), RUSHING_YARDS, entries(), NOW).quotes


def test_market_history_excludes_same_day_and_future_games():
    quotes = normalize_prop_markets(payload(), game(), RUSHING_YARDS, entries(), NOW).quotes
    service = NFLPropTrendReadService(game_log_provider=History())
    rows = service.build_market_rows(quotes, selected_season=2026, before_date=date(2025, 9, 9))
    assert all(r.trend.last_10.games_considered == 0 for r in rows)

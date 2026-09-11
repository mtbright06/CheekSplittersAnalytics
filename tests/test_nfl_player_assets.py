from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image
import pytest

from app.player_assets import get_player_headshot
from tools_build_nfl_player_assets import acquire, candidates, image_bytes


def png():
    buffer = BytesIO()
    Image.new('RGBA', (80, 40), (20, 30, 40, 128)).save(buffer, format='PNG')
    return buffer.getvalue()


def setup_assets(tmp_path):
    directory = tmp_path / 'nfl'
    (directory / 'headshots').mkdir(parents=True)
    (directory / 'fallback.png').write_bytes(png())
    (directory / 'headshots/00-0033280.png').write_bytes(png())
    (directory / 'manifest.json').write_text(json.dumps({'players': {
        '00-0033280': {'status': 'available', 'filename': 'headshots/00-0033280.png'},
        'bad': {'status': 'available', 'filename': '../../secret.png'},
    }}))
    return directory


def test_local_resolution_fallback_and_no_network(tmp_path, monkeypatch):
    import requests
    monkeypatch.setattr(requests, 'get', lambda *a, **kw: pytest.fail('runtime network request'))
    directory = setup_assets(tmp_path)
    assert get_player_headshot('nfl', '00-0033280', asset_root=tmp_path) == directory / 'headshots/00-0033280.png'
    for player_id in ('missing', 'bad', '../secret'):
        assert get_player_headshot('nfl', player_id, asset_root=tmp_path) == directory / 'fallback.png'
    assert get_player_headshot('unknown', '00-0033280', asset_root=tmp_path) is None
    assert get_player_headshot('../../', '00-0033280', asset_root=tmp_path) is None


def test_malformed_manifest_and_corrupt_image_fail_safely(tmp_path):
    directory = setup_assets(tmp_path)
    (directory / 'headshots/00-0033280.png').write_bytes(b'not an image')
    assert get_player_headshot('nfl', '00-0033280', asset_root=tmp_path) == directory / 'fallback.png'
    (directory / 'manifest.json').write_text('not json')
    assert get_player_headshot('nfl', '00-0033280', asset_root=tmp_path) == directory / 'fallback.png'


def test_manifest_update_is_seen_without_process_restart(tmp_path):
    directory = setup_assets(tmp_path)
    assert get_player_headshot('nfl', 'new', asset_root=tmp_path) == directory / 'fallback.png'
    (directory / 'manifest.json').write_text(json.dumps({'players': {
        'new': {'status': 'available', 'filename': 'headshots/00-0033280.png'}}}))
    assert get_player_headshot('nfl', 'new', asset_root=tmp_path) == directory / 'headshots/00-0033280.png'


def test_candidate_identity_roster_context_and_canonical_source():
    rows = [{'gsis_id': '00-0033280', 'team': 'LA', 'week': '1', 'season': '2026',
             'position': 'QB', 'status': 'ACT', 'headshot_url': 'https://fallback/photo'}]
    registry = [{'gsis_id': '00-0033280', 'display_name': 'Player', 'headshot': 'https://canonical/photo'}]
    week, result = candidates(registry, rows * 2 + [dict(rows[0], gsis_id='00-0000002', status='CUT')], 2026)
    assert week == 1
    assert len(result) == 1
    assert result[0]['player_id'] == '00-0033280'
    assert result[0]['team'] == 'LAR'
    assert result[0]['source_url'] == 'https://canonical/photo'
    assert candidates([], rows, 2026)[1][0]['source_url'] == 'https://fallback/photo'


def test_image_normalization_preserves_alpha_and_aspect_ratio():
    data, metadata = image_bytes(png())
    with Image.open(BytesIO(data)) as image:
        assert image.size == (80, 40)
        assert image.mode == 'RGBA'
        assert image.getpixel((0, 0))[3] == 128
    assert metadata['source_format'] == 'PNG'
    with pytest.raises(Exception):
        image_bytes(b'<html>error</html>')


class Response:
    def __init__(self, content, failed=False):
        self.content, self.failed = content, failed
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def raise_for_status(self):
        if self.failed: raise RuntimeError('HTTP failure')
    def iter_content(self, size): yield self.content


def test_acquisition_reuse_and_failed_refresh_preserves_known_good(tmp_path):
    entry = dict(player_id='00-0033280', source_url='https://example.com/photo')
    first, status = acquire(entry, tmp_path, fetcher=lambda *a, **kw: Response(png()))
    assert status == 'downloaded'
    original = (tmp_path / first['filename']).read_bytes()
    second, status = acquire(entry, tmp_path, first, fetcher=lambda *a, **kw: pytest.fail('refetched'))
    assert status == 'reused'
    failed, status = acquire(entry, tmp_path, second, refresh=True,
                             fetcher=lambda *a, **kw: Response(b'error', failed=True))
    assert status == 'download_failed'
    assert failed['status'] == 'available'
    assert (tmp_path / first['filename']).read_bytes() == original


def test_invalid_and_missing_images_have_explicit_status(tmp_path):
    entry = dict(player_id='00-0033280', source_url='https://example.com/photo')
    result, status = acquire(entry, tmp_path, fetcher=lambda *a, **kw: Response(b'<html>error</html>'))
    assert status == result['status'] == 'invalid_image'
    result, status = acquire(dict(entry, source_url=None), tmp_path)
    assert status == result['status'] == 'no_source'


def test_team_logo_uses_existing_pack_and_alias():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
    from components.logos import team_logo_path
    assert team_logo_path('LA', 'nfl') == team_logo_path('LAR', 'nfl')
    assert team_logo_path('LA', 'nfl').name == 'lar.png'
    assert team_logo_path('LA', 'nfl').is_file()
    assert team_logo_path('LAC', 'nfl').name == 'lac.png'


def test_modal_identity_uses_canonical_local_asset_without_network(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
    from components import nfl_props
    from streamlit.testing.v1 import AppTest
    import requests
    directory = setup_assets(tmp_path)
    calls = []
    def resolve(sport, player_id):
        calls.append((sport, player_id))
        return get_player_headshot(sport, player_id, asset_root=tmp_path)
    monkeypatch.setattr(nfl_props, 'get_player_headshot', resolve)
    monkeypatch.setattr(requests, 'get', lambda *a, **kw: pytest.fail('renderer network request'))
    at = AppTest.from_string('''from components.nfl_props import render_player_identity
render_player_identity(player="Player", player_id="00-0033280", team="LA", position="QB",
                      opponent="SF", market="Passing Yards", game_context="Week 1", source_context="Local")
''').run()
    assert not at.exception
    assert calls == [('nfl', '00-0033280')]
    assert any('class="nfl-headshot"' in item.value and 'data:image/png;base64,' in item.value
               for item in at.markdown)
    assert directory.exists()

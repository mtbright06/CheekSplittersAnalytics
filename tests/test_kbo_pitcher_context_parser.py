from bs4 import BeautifulSoup

from parsers.game_parser import GameParser
from parsers.pitcher_parser import PitcherParser


def test_pitcher_parser_extracts_role_and_previous_start_context():
    html = """
    <h1>Test Starter (테스트) KT Wiz #1 | RHP</h1>
    <p>Throws / Bats</p><p>Right / Right</p>
    <table>
      <tr><th>Year</th><th>ERA</th><th>WHIP</th><th>W</th><th>L</th>
      <th>G</th><th>GS</th><th>IP</th><th>SO</th><th>BB</th><th>HR</th></tr>
      <tr><td>2026</td><td>3.50</td><td>1.20</td><td>8</td><td>4</td>
      <td>18</td><td>16</td><td>96</td><td>80</td><td>25</td><td>8</td></tr>
    </table>
    <table>
      <tr><th>Date</th><th>Opp</th><th>Role</th><th>Dec</th><th>ERA</th>
      <th>WHIP</th><th>IP</th><th>NP</th><th>R</th><th>ER</th><th>H</th>
      <th>HR</th><th>SO</th><th>BB</th><th>HB</th><th>GS</th></tr>
      <tr><td>2026-08-01</td><td>vs. LG</td><td>RP</td><td></td><td></td>
      <td>1.00</td><td>1</td><td></td><td>0</td><td>0</td><td>1</td>
      <td>0</td><td>1</td><td>0</td><td>0</td><td></td></tr>
      <tr><td>2026-07-27</td><td>@ NC</td><td>SP</td><td>W</td><td></td>
      <td>1.17</td><td>7</td><td>91</td><td>1</td><td>1</td><td>6</td>
      <td>0</td><td>5</td><td>1</td><td>0</td><td>72</td></tr>
    </table>
    """

    data = PitcherParser._parse_profile(BeautifulSoup(html, "html.parser"))

    assert data["games"] == 18
    assert data["games_started"] == 16
    assert data["last_role"] == "RP"
    assert data["previous_appearance_date"] == "2026-08-01"
    assert data["previous_start_date"] == "2026-07-27"
    assert data["previous_start_ip"] == 7.0
    assert data["previous_start_pitch_count"] == 91


def test_game_parser_extracts_game_date():
    html = """
    <html><body>
    <p>August 08, 2026 6:00pm · Seoul-Jamsil</p>
    </body></html>
    """

    game_date = GameParser._parse_game_date(BeautifulSoup(html, "html.parser"))

    assert game_date == "2026-08-08"

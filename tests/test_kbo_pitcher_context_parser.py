from bs4 import BeautifulSoup
from unittest.mock import patch

from models.game import Game
from models.kbo_model import KBOModel
from parsers.game_parser import GameParser
from parsers.pitcher_parser import PitcherParser
from parsers.schedule_parser import ScheduleParser


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


def test_game_parser_current_starter_markup_resolves_distinct_starters():
    html = """
    <html><body>
      <div class="starter-comparison">
        <div class="starter-comparison__pitcher starter-comparison__pitcher--away">
          <a class="player-link" href="/players/2944-Owen-White-Hanwha-Eagles">
            <img src="/photos/player/2944.jpg" />
          </a>
          <a class="player-link" href="/players/2944-Owen-White-Hanwha-Eagles">
            Owen White
          </a>
        </div>
        <div class="starter-comparison__pitcher starter-comparison__pitcher--home">
          <a class="player-link" href="/players/2402-Wes-Benjamin-Doosan-Bears">
            <img src="/photos/player/2402.jpg" />
          </a>
          <a class="player-link" href="/players/2402-Wes-Benjamin-Doosan-Bears">
            Wes Benjamin
          </a>
        </div>
      </div>
    </body></html>
    """

    soup = BeautifulSoup(html, "html.parser")
    starters = GameParser._find_starters(soup)

    assert len(starters) == 2
    assert GameParser._parse_pitcher(starters[0])["name"] == "Owen White"
    assert GameParser._parse_pitcher(starters[1])["name"] == "Wes Benjamin"


def test_game_parser_ignores_image_only_player_link_for_pitcher_name():
    html = """
    <div class="starter-comparison__pitcher starter-comparison__pitcher--away">
      <a class="player-link" href="/players/2944-Owen-White-Hanwha-Eagles">
        <img src="/photos/player/2944.jpg" />
      </a>
      <a class="player-link" href="/players/2944-Owen-White-Hanwha-Eagles">
        Owen White
      </a>
    </div>
    """

    pitcher = GameParser._parse_pitcher(BeautifulSoup(html, "html.parser").div)

    assert pitcher["name"] == "Owen White"
    assert pitcher["profile_url"].endswith("/players/2944-Owen-White-Hanwha-Eagles")


def test_schedule_parser_current_row_with_weather_uses_time_and_venue():
    game = ScheduleParser._parse_game_lines(
        lines=[
            "Hanwha",
            "Eagles",
            "Doosan",
            "Bears",
            "27°",
            "7:00pm",
            "Seoul-Jamsil",
            "Starters:",
            "White vs. Benjamin",
        ],
        href="/games/13807-Hanwha-vs-Doosan-20260812",
    )

    assert game["away"] == "Hanwha Eagles"
    assert game["home"] == "Doosan Bears"
    assert game["time"] == "7:00pm"
    assert game["venue"] == "Seoul-Jamsil"
    assert game["game_date"] == "2026-08-12"


def test_duplicate_starter_guard_still_rejects_true_duplicate_mapping():
    game = Game("Hanwha Eagles", "Doosan Bears")
    game.away.pitcher.name = "Same Starter"
    game.away.pitcher.profile_url = "https://mykbostats.com/players/1-Same"
    game.home.pitcher.name = "Same Starter"
    game.home.pitcher.profile_url = "https://mykbostats.com/players/1-Same"

    from loaders.pitcher_loader import PitcherLoader

    PitcherLoader._guard_distinct_starters(game.away.pitcher, game.home.pitcher)

    assert game.away.pitcher.name == "Unknown Starter"
    assert game.home.pitcher.name == "Unknown Starter"
    assert game.away.pitcher.data_source == "starter_mapping_unverified"
    assert game.home.pitcher.data_source == "starter_mapping_unverified"


def test_current_style_kbo_fixture_does_not_skip_all_games_when_starters_present():
    games = []
    for index in range(5):
        game = Game(f"Away {index}", f"Home {index}")
        for team in (game.away, game.home):
            team.pitcher.name = f"{team.name} Starter"
            team.pitcher.era = 3.50
            team.pitcher.whip = 1.20
            team.pitcher.data_source = "starter_profile"
            team.pitcher.starter_confirmed = True
            team.offense.runs_per_game = 5.0
            team.offense.league_runs_per_game = 5.0
            team.bullpen.era = 4.0
            team.bullpen.league_era = 4.0
            team.form.season_runs_per_game = 5.0
            team.form.recent_runs_per_game = 5.0
            team.form.recent_games = 10
        games.append(game)

    with patch("models.kbo_model.PitcherLoader.load"):
        scored = KBOModel().score(games)

    assert len(scored) == 5


def test_windows_kbo_script_forces_utf8_for_python_output():
    script = open("scripts/Update-KBO.ps1", encoding="utf-8").read()

    assert "[Console]::OutputEncoding" in script
    assert "$env:PYTHONUTF8 = \"1\"" in script
    assert "$env:PYTHONIOENCODING = \"utf-8\"" in script

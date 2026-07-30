from pathlib import Path
import sys


DASHBOARD = Path(__file__).resolve().parents[1] / "dashboard"

if str(DASHBOARD) not in sys.path:
    sys.path.insert(0, str(DASHBOARD))

import components.cards as cards
import components.mlb.workstation as workstation


def _game():
    return {
        "sport": "mlb",
        "game_id": "1",
        "commence_time": "2026-07-29T23:10:00Z",
        "venue": "Angel Stadium",
        "matchup": {"away": "Houston Astros", "home": "Los Angeles Angels"},
        "model": {
            "play": "Houston Astros",
            "market": "Moneyline",
            "recommendation": "LEAN",
            "model_probability": 0.574,
            "confidence": 70.2,
            "edge": 0.88,
            "market_value_label": "POSITIVE VALUE",
            "market_value_tone": "positive_value",
        },
        "odds": {
            "moneyline": -126,
            "book_probability": 0.558,
            "reference_price": -130,
            "market_status": "MARKET READY",
            "real_market_loaded": True,
        },
        "totals_model": {
            "recommendation": "PASS",
            "selection": "UNDER",
            "projected_total": 9.4,
            "market_total": 9.5,
            "edge": -0.1,
            "confidence": 72,
            "reasons": ["Model projects 9.40 runs versus market total of 9.50."],
        },
    }


def test_mlb_workstation_renders_approved_top_half(monkeypatch):
    rendered = []
    buttons = []

    monkeypatch.setattr(
        workstation.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )
    monkeypatch.setattr(workstation.st, "button", lambda label, **kwargs: buttons.append(label) and False)

    class Column:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        workstation.st,
        "columns",
        lambda count, **kwargs: [Column() for _ in range(count if isinstance(count, int) else len(count))],
    )

    workstation.render_mlb_workstation_game(_game())
    html = "".join(rendered)

    assert "mlb-matchup-workstation" in html
    assert "Houston Astros" in html
    assert "Los Angeles Angels" in html
    assert "Angel Stadium" in html
    assert "SharpStack Decision" in html
    assert "Pick" in html
    assert "Market Edge" in html
    assert "LEAN" in html
    assert "70.2 / 100" in html
    assert "Moneyline" in html
    assert "Totals" in html
    assert "mlb-analytics-controls" in html
    assert buttons == [
        "Pitchers · Starting",
        "Bullpen · Relievers",
        "Decision · Builder",
        "Model View · Components",
        "Weather · Conditions",
    ]
    assert "Houston Astros Starter" not in html
    assert "-126" in html
    assert "Fair Price" in html
    assert "Book Probability" in html
    assert "Model Win Probability" in html
    assert "Projected Total" in html
    assert "Market Total" in html
    hero_html = html.split("Moneyline", 1)[0]
    assert "LEAN" not in hero_html
    assert "Market Status" not in hero_html
    assert "Model Win %" not in hero_html
    assert "mlb-strip-badge" not in hero_html
    assert "mlb-decision-summary" in hero_html
    assert "Metric</span>" not in html
    assert "Edge / Info" not in html
    assert "<em>-" not in html


def test_mlb_workstation_omits_unavailable_fields(monkeypatch):
    rendered = []
    game = _game()
    game["odds"]["reference_price"] = None

    monkeypatch.setattr(
        workstation.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )
    monkeypatch.setattr(workstation.st, "button", lambda *args, **kwargs: False)

    class Column:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(
        workstation.st,
        "columns",
        lambda count, **kwargs: [Column() for _ in range(count if isinstance(count, int) else len(count))],
    )

    workstation.render_mlb_workstation_game(game)
    html = "".join(rendered)

    assert "Fair Price" not in html
    assert "Unavailable" not in html


def test_mlb_workspace_button_toggles_active_section(monkeypatch):
    rendered = []
    game = _game()
    key = f"mlb_analytics_workspace_{game['game_id']}"
    workstation.st.session_state[key] = None

    monkeypatch.setattr(
        workstation.st,
        "markdown",
        lambda html, **kwargs: rendered.append(html),
    )

    class Column:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(workstation.st, "columns", lambda count, **kwargs: [Column() for _ in range(count)])

    clicks = {"Pitchers · Starting": True}
    monkeypatch.setattr(
        workstation.st,
        "button",
        lambda label, **kwargs: clicks.pop(label, False),
    )

    workstation.render_analytics_workspace(game)
    assert workstation.st.session_state[key] == "Pitchers"

    clicks = {"Pitchers · Starting": True}
    monkeypatch.setattr(
        workstation.st,
        "button",
        lambda label, **kwargs: clicks.pop(label, False),
    )

    workstation.render_analytics_workspace(game)
    assert workstation.st.session_state[key] is None


def test_mlb_render_path_uses_workstation_component(monkeypatch):
    called = {}
    explorer = {}

    monkeypatch.setattr(
        cards,
        "render_mlb_workstation_game",
        lambda game: called.update(game=game),
    )
    monkeypatch.setattr(cards, "splitter_commentary", lambda game: "")
    monkeypatch.setattr(
        cards,
        "render_recommendation_explorer",
        lambda *args, **kwargs: explorer.update(called=True),
    )
    monkeypatch.setattr(cards.st, "markdown", lambda *args, **kwargs: None)

    game = _game()
    cards.render_game(game)

    assert called["game"] is game
    assert explorer == {}

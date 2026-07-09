import requests


EXCLUDED_POSITIONS = {"P", "SP", "RP", "CP"}


def fetch_active_roster(team_id):
    if not team_id:
        return []

    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=active"

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    players = []

    for item in data.get("roster", []):
        person = item.get("person", {})
        position = item.get("position", {})

        pos = position.get("abbreviation")
        pos_type = position.get("type")

        if pos in EXCLUDED_POSITIONS or pos_type == "Pitcher":
            continue

        players.append(
            {
                "player_id": person.get("id"),
                "name": person.get("fullName"),
                "position": pos,
                "position_type": pos_type,
            }
        )

    return players


def roster_id_set(players):
    return {
        int(p["player_id"])
        for p in players
        if p.get("player_id") is not None
    }


def roster_name_map(players):
    return {
        int(p["player_id"]): p.get("name")
        for p in players
        if p.get("player_id") is not None
    }


def roster_position_map(players):
    return {
        int(p["player_id"]): p.get("position")
        for p in players
        if p.get("player_id") is not None
    }

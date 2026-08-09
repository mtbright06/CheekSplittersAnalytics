def line_movement(opening_odds, current_odds):
    if opening_odds is None or current_odds is None:
        return None

    try:
        return int(current_odds) - int(opening_odds)
    except Exception:
        return None


def movement_label(movement):
    if movement is None:
        return "No movement data"

    if movement > 0:
        return f"Moved {movement} cents toward bettor"

    if movement < 0:
        return f"Moved {abs(movement)} cents away from bettor"

    return "No movement"

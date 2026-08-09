def statcast_barrel_flag(row):
    """Return 1 when Statcast's native launch-speed-angle class is barrel."""
    try:
        return int(row.get("launch_speed_angle") == 6)
    except Exception:
        return 0

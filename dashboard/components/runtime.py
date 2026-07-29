"""Dashboard-only runtime setup helpers."""

from __future__ import annotations

from pathlib import Path
import sys


def ensure_project_root() -> None:
    """Prefer the repository package over the Streamlit script directory."""

    root = Path(__file__).resolve().parents[2]
    root_text = str(root)
    if root_text in sys.path:
        sys.path.remove(root_text)
    sys.path.insert(0, root_text)

from __future__ import annotations

from pathlib import Path


def load_web_ui_html() -> str:
    path = Path(__file__).resolve().parents[3] / "frontend" / "web" / "index.html"
    return path.read_text(encoding="utf-8")

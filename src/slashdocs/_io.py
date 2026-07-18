"""Private write-if-changed helper shared by the stateless outputs (json_out, page)."""

from __future__ import annotations

from pathlib import Path


def write_if_changed(path: Path, text: str) -> bool:
    """Write `text` to `path` only if its current content differs. Returns True if written."""
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except (FileNotFoundError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True

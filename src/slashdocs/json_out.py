"""Renders a Manifest as a stable commands.json for custom /commands frontends.

Stateless by design: callers byte-compare against the file on disk, so a deleted
or hand-edited file is simply regenerated on the next run.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .model import Manifest

logger = logging.getLogger("slashdocs")


def render_json(manifest: Manifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n"


def write_json(path: Path, manifest: Manifest) -> bool:
    """Write commands.json if its content would change. Returns True if written."""
    text = render_json(manifest)
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except (FileNotFoundError, UnicodeDecodeError):
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    logger.info("slashdocs: wrote %s", path)
    return True

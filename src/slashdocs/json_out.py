"""Renders a Manifest as a stable commands.json for custom /commands frontends.

Stateless by design: callers byte-compare against the file on disk, so a deleted
or hand-edited file is simply regenerated on the next run.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ._io import write_if_changed
from .model import Manifest

logger = logging.getLogger("slashdocs")


def render_json(manifest: Manifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n"


def write_json(path: Path, manifest: Manifest) -> bool:
    """Write commands.json if its content would change. Returns True if written."""
    written = write_if_changed(path, render_json(manifest))
    if written:
        logger.info("slashdocs: wrote %s", path)
    return written

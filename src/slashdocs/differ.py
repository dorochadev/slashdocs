"""Hash-based change detection between the live manifest and the stored state."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .model import Manifest

STATE_FILENAME = ".slashdocs-manifest.json"

logger = logging.getLogger("slashdocs")


@dataclass(frozen=True)
class Diff:
    added: tuple[str, ...] = ()
    changed: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.changed or self.removed)


def compute_diff(old: Manifest | None, new: Manifest) -> Diff:
    new_hashes = {c.slug: c.content_hash() for c in new.commands}
    if old is None:
        return Diff(added=tuple(sorted(new_hashes)))
    old_hashes = {c.slug: c.content_hash() for c in old.commands}
    prefix_changed = old.prefix != new.prefix  # prefix is rendered into every page
    return Diff(
        added=tuple(sorted(s for s in new_hashes if s not in old_hashes)),
        changed=tuple(
            sorted(
                s
                for s in new_hashes
                if s in old_hashes and (prefix_changed or new_hashes[s] != old_hashes[s])
            )
        ),
        removed=tuple(sorted(s for s in old_hashes if s not in new_hashes)),
    )


def load_state(out_dir: Path) -> Manifest | None:
    path = out_dir / STATE_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = Manifest.from_dict(data["manifest"])
        # Old-schema fields are additive-only (Manifest/CommandDoc.from_dict default
        # anything missing), so this still parses and stays diffable — that's what lets
        # compute_diff notice slugs a later slugify() change renamed, and clean them up.
        if manifest.schema_version != Manifest().schema_version:
            logger.info(
                "slashdocs: state %s is schema v%d; migrating", path, manifest.schema_version
            )
        return manifest
    except FileNotFoundError:
        return None
    except Exception:
        logger.warning("slashdocs: state file %s is unreadable; regenerating all docs", path)
        return None


def save_state(out_dir: Path, manifest: Manifest) -> None:
    payload = {"manifest": manifest.to_dict()}
    path = out_dir / STATE_FILENAME
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

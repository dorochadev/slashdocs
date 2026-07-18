"""attach() — the one-line entry point that hooks docs generation into bot startup."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .differ import Diff, compute_diff, load_state, save_state
from .walker import walk_bot
from .writer import write_docs

logger = logging.getLogger("slashdocs")

_ATTACHED_ATTR = "_slashdocs_attached"


def generate(
    bot: Any, out: str | Path, *, base_slug: str = "/commands", clean: bool = True
) -> Diff:
    out_dir = Path(out)
    manifest = walk_bot(bot)
    previous = load_state(out_dir)
    diff = compute_diff(previous, manifest)
    if previous is not None and diff.is_empty:
        logger.info("slashdocs: docs up to date (%d commands)", len(manifest.commands))
        return diff
    write_docs(out_dir, manifest, diff, clean=clean, base_slug=base_slug)
    save_state(out_dir, manifest)
    logger.info(
        "slashdocs: %d added, %d changed, %d removed -> %s",
        len(diff.added),
        len(diff.changed),
        len(diff.removed),
        out_dir,
    )
    return diff


def attach(
    bot: Any,
    out: str | Path = "docs/commands",
    *,
    base_slug: str = "/commands",
    clean: bool = True,
    fmt: str = "mdx",
) -> None:
    """Register a run-once on_ready listener that generates the docs.

    Generation failures are logged, never raised — docs must not take the bot down.
    """
    if fmt != "mdx":
        raise ValueError(f"unsupported fmt {fmt!r}: only 'mdx' is supported in v1")
    if getattr(bot, _ATTACHED_ATTR, False):
        return
    setattr(bot, _ATTACHED_ATTR, True)
    ran = False

    async def _slashdocs_on_ready() -> None:
        nonlocal ran
        if ran:
            return
        ran = True
        try:
            generate(bot, out, base_slug=base_slug, clean=clean)
        except Exception:
            logger.exception("slashdocs: docs generation failed; the bot continues unaffected")

    bot.add_listener(_slashdocs_on_ready, "on_ready")

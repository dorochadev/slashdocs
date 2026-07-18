"""attach() — the one-line entry point that hooks docs generation into bot startup."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

from .differ import Diff, compute_diff, load_state, save_state
from .json_out import write_json
from .model import Manifest
from .outputs import JsonOutput, MdxOutput, Output, PageOutput, mdx
from .page import write_page
from .walker import walk_bot
from .writer import write_docs

logger = logging.getLogger("slashdocs")

_ATTACHED_ATTR = "_slashdocs_attached"


class OutputGenerationError(RuntimeError):
    """Raised by generate() after attempting every output, if any failed."""

    def __init__(self, failures: Sequence[tuple[Output, BaseException]]) -> None:
        self.failures = tuple(failures)
        outputs = ", ".join(str(output) for output, _exc in self.failures)
        super().__init__(f"{len(self.failures)} output(s) failed: {outputs}")


def _resolve_outputs(
    out: str | Path | None,
    outputs: Sequence[Output] | None,
    *,
    base_slug: str,
    clean: bool,
) -> tuple[Output, ...]:
    if out is not None and outputs is not None:
        raise ValueError("pass either out= or outputs=, not both")
    if outputs is not None:
        if not outputs:
            raise ValueError("outputs= must contain at least one output")
        return tuple(outputs)
    return (mdx(out if out is not None else "docs/commands", base_slug=base_slug, clean=clean),)


def _run_mdx(output: MdxOutput, manifest: Manifest) -> Diff:
    previous = load_state(output.path)
    diff = compute_diff(previous, manifest)
    if previous is not None and diff.is_empty:
        logger.info("slashdocs: docs up to date (%d commands)", len(manifest.commands))
        return diff
    skipped = write_docs(
        output.path,
        manifest,
        diff,
        clean=output.clean,
        base_slug=output.base_slug,
        sweep=previous is None,
    )
    # A slug the overwrite guard skipped must not be recorded as settled — otherwise
    # it's never retried, even after the conflicting hand-written file goes away.
    to_save = manifest
    if skipped:
        kept = tuple(c for c in manifest.commands if c.slug not in skipped)
        to_save = replace(manifest, commands=kept)
    save_state(output.path, to_save)
    logger.info(
        "slashdocs: %d added, %d changed, %d removed -> %s",
        len(diff.added),
        len(diff.changed),
        len(diff.removed),
        output.path,
    )
    return diff


def generate(
    bot: Any,
    out: str | Path | None = None,
    *,
    outputs: Sequence[Output] | None = None,
    prefix: str | None = None,
    base_slug: str = "/commands",
    clean: bool = True,
) -> Diff:
    """Walk the bot once and render every configured output.

    Every output is attempted even if another fails. If any failed, raises
    OutputGenerationError once all have been attempted (see attach(), which
    catches this so generation failures never take the bot down).
    Returns the Diff of the first MDX output (an empty Diff if there is none).
    """
    resolved = _resolve_outputs(out, outputs, base_slug=base_slug, clean=clean)
    manifest = walk_bot(bot, prefix=prefix)
    result: Diff | None = None
    failures: list[tuple[Output, BaseException]] = []
    for output in resolved:
        try:
            if isinstance(output, MdxOutput):
                diff = _run_mdx(output, manifest)
                if result is None:
                    result = diff
            elif isinstance(output, JsonOutput):
                write_json(output.path, manifest)
            elif isinstance(output, PageOutput):
                write_page(output.path, manifest, title=output.title, accent=output.accent)
        except Exception as exc:
            logger.exception("slashdocs: output %s failed; continuing with the rest", output)
            failures.append((output, exc))
    if failures:
        raise OutputGenerationError(failures)
    return result if result is not None else Diff()


def attach(
    bot: Any,
    out: str | Path | None = None,
    *,
    outputs: Sequence[Output] | None = None,
    prefix: str | None = None,
    base_slug: str = "/commands",
    clean: bool = True,
) -> None:
    """Register a run-once on_ready listener that generates the docs off the event loop.

    Generation failures are logged, never raised — docs must not take the bot down.
    """
    resolved = _resolve_outputs(out, outputs, base_slug=base_slug, clean=clean)
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
            await asyncio.to_thread(generate, bot, outputs=resolved, prefix=prefix)
        except Exception:
            logger.exception("slashdocs: docs generation failed; the bot continues unaffected")

    bot.add_listener(_slashdocs_on_ready, "on_ready")

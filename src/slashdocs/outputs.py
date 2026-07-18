"""Output configurations for attach()/generate(). One walk feeds any number of these."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MdxOutput:
    path: Path
    base_slug: str = "/commands"
    clean: bool = True


@dataclass(frozen=True)
class JsonOutput:
    path: Path


@dataclass(frozen=True)
class PageOutput:
    path: Path
    title: str = "Commands"
    accent: str = "#5865F2"


Output = MdxOutput | JsonOutput | PageOutput


def mdx(path: str | Path, *, base_slug: str = "/commands", clean: bool = True) -> MdxOutput:
    """MDX pages for a docs framework (Fumadocs, Nextra, Docusaurus, Starlight)."""
    return MdxOutput(Path(path), base_slug=base_slug, clean=clean)


def commands_json(path: str | Path) -> JsonOutput:
    """Stable commands.json for a custom /commands frontend."""
    return JsonOutput(Path(path))


def commands_page(
    path: str | Path, *, title: str = "Commands", accent: str = "#5865F2"
) -> PageOutput:
    """Self-contained, searchable commands.html — no site framework required."""
    return PageOutput(Path(path), title=title, accent=accent)

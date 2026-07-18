"""Renders a Manifest into MDX files. CommonMark-only bodies so output renders
identically in Fumadocs, Nextra, Docusaurus, and Astro Starlight."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from .differ import Diff
from .model import CommandDoc, Manifest, ParamDoc

GENERATED_MARKER = "generated_by: slashdocs"
_JSON_GENERATED_MARKER = '"generated_by": "slashdocs"'
_ESCAPED_PIPE = "\\|"
_BACKTICK_RUN_RE = re.compile("`+")

logger = logging.getLogger("slashdocs")


def _yaml_str(value: str) -> str:
    return json.dumps(value)  # JSON string escaping is valid YAML


def _escape_text(text: str) -> str:
    """Escape characters MDX would parse as JSX ('<' opens an element, '{' an expression)."""
    return text.replace("\\", "\\\\").replace("<", "\\<").replace("{", "\\{")


def _cell(text: str) -> str:
    """Table cells must be one line and pipe-free: first non-empty line, escaped."""
    first = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return _escape_text(first).replace("|", _ESCAPED_PIPE)


def _code_span(text: str) -> str:
    """Wrap in a CommonMark code span with a fence long enough that a backtick
    embedded in `text` can never close the span early and leak the rest raw."""
    longest_run = max((len(run) for run in _BACKTICK_RUN_RE.findall(text)), default=0)
    fence = "`" * (longest_run + 1)
    if text == "" or text.startswith("`") or text.endswith("`"):
        return f"{fence} {text} {fence}"
    return f"{fence}{text}{fence}"


def _display_name(doc: CommandDoc, prefix: str) -> str:
    return f"{prefix if doc.kind == 'prefix' else '/'}{doc.name}"


def _usage(doc: CommandDoc, prefix: str) -> str:
    parts = [_display_name(doc, prefix)]
    parts += [f"<{p.name}>" if p.required else f"[{p.name}]" for p in doc.params]
    return " ".join(parts)


def _usage_variants(doc: CommandDoc, prefix: str) -> list[str]:
    """Hybrid commands are invocable both ways, so show both usage forms."""
    args = [f"<{p.name}>" if p.required else f"[{p.name}]" for p in doc.params]
    if doc.kind != "hybrid":
        return [" ".join([_display_name(doc, prefix), *args])]
    return [
        " ".join([f"/{doc.name}", *args]),
        " ".join([f"{prefix}{doc.name}", *args]),
    ]


def _cooldown_text(doc: CommandDoc) -> str:
    return f"{doc.cooldown_rate}/{doc.cooldown_per:g}s"


def _badges(doc: CommandDoc) -> str:
    parts = []
    if doc.permissions:
        parts.append("**Requires:** " + ", ".join(_escape_text(p) for p in doc.permissions))
    if doc.cooldown_rate:
        parts.append(f"**Cooldown:** {_cooldown_text(doc)}")
    if doc.tier:
        parts.append(f"👑 {_escape_text(doc.tier)}")
    return " · ".join(parts)


def _param_desc_cell(p: ParamDoc) -> str:
    parts = []
    if p.description:
        parts.append(_cell(p.description))
    if p.choices:
        choices = ", ".join(_code_span(c.replace("|", _ESCAPED_PIPE)) for c in p.choices)
        parts.append("One of: " + choices)
    return " — ".join(parts)


def _params_table(params: tuple[ParamDoc, ...], *, heading: bool = True) -> list[str]:
    lines = ["## Parameters", ""] if heading else []
    lines += [
        "| Name | Type | Required | Description |",
        "| ---- | ---- | -------- | ----------- |",
    ]
    for p in params:
        required = "yes" if p.required else "no"
        lines.append(f"| {_cell(p.name)} | {_cell(p.type)} | {required} | {_param_desc_cell(p)} |")
    lines.append("")
    return lines


def _frontmatter(doc: CommandDoc, prefix: str) -> list[str]:
    lines = [
        "---",
        f"title: {_yaml_str(_display_name(doc, prefix))}",
        f"description: {_yaml_str(doc.description)}",
        f"category: {_yaml_str(doc.category)}",
    ]
    if doc.permissions:
        lines.append("permissions: [" + ", ".join(_yaml_str(p) for p in doc.permissions) + "]")
    if doc.cooldown_rate:
        lines.append(f'cooldown: "{_cooldown_text(doc)}"')
    if doc.tier:
        lines.append(f"tier: {_yaml_str(doc.tier)}")
    lines.append(GENERATED_MARKER)
    if doc.params:
        lines.append("params:")
        for p in doc.params:
            lines.append(f"  - name: {_yaml_str(p.name)}")
            lines.append(f"    type: {_yaml_str(p.type)}")
            lines.append(f"    required: {'true' if p.required else 'false'}")
            if p.description:
                lines.append(f"    description: {_yaml_str(p.description)}")
            if p.choices:
                choices = ", ".join(_yaml_str(c) for c in p.choices)
                lines.append(f"    choices: [{choices}]")
    lines.append("---")
    return lines


def _body(doc: CommandDoc, prefix: str) -> list[str]:
    lines: list[str] = [""]
    if doc.description:
        lines += [_escape_text(doc.description), ""]
    badges = _badges(doc)
    if badges:
        lines += [badges, ""]
    lines += ["## Usage", ""]
    for usage in doc.examples or _usage_variants(doc, prefix):
        lines += [_code_span(usage), ""]
    if doc.params:
        lines += _params_table(doc.params)
    if doc.aliases:
        aliases = ", ".join(_code_span(a) for a in doc.aliases)
        lines += [f"**Aliases:** {aliases}", ""]
    if doc.subcommands:
        lines += ["## Subcommands", ""]
        for sub in doc.subcommands:
            lines += [f"### {_escape_text(_display_name(sub, prefix))}", ""]
            if sub.description:
                lines += [_escape_text(sub.description), ""]
            sub_badges = _badges(sub)
            if sub_badges:
                lines += [sub_badges, ""]
            for usage in _usage_variants(sub, prefix):
                lines += [_code_span(usage), ""]
            if sub.params:
                lines += _params_table(sub.params, heading=False)
    if doc.notes:
        lines += [_escape_text(doc.notes), ""]
    return lines


def render_command(doc: CommandDoc, *, prefix: str = "!") -> str:
    text = "\n".join(_frontmatter(doc, prefix) + _body(doc, prefix))
    return text.rstrip("\n") + "\n"


def render_index(manifest: Manifest, *, base_slug: str = "/commands") -> str:
    lines = [
        "---",
        'title: "Commands"',
        'description: "All commands, grouped by category."',
        GENERATED_MARKER,
        "---",
        "",
    ]
    by_category: dict[str, list[CommandDoc]] = {}
    for cmd in manifest.commands:
        by_category.setdefault(cmd.category, []).append(cmd)
    for category in sorted(by_category):
        lines += [f"## {category}", "", "| Command | Description |", "| ------- | ----------- |"]
        for cmd in sorted(by_category[category], key=lambda c: c.name):
            link = f"[{_display_name(cmd, manifest.prefix)}]({base_slug}/{cmd.slug})"
            lines.append(f"| {link} | {_cell(cmd.description)} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_meta(manifest: Manifest) -> str:
    ordered = sorted(manifest.commands, key=lambda c: (c.category, c.name))
    payload = {"generated_by": "slashdocs", "pages": ["index", *(c.slug for c in ordered)]}
    return json.dumps(payload, indent=2) + "\n"


def _has_marker(path: Path, marker: str) -> bool:
    try:
        return marker in path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False  # not text we could have generated; treat as someone else's file


def _write_page(path: Path, text: str, *, marker: str = GENERATED_MARKER) -> bool:
    """Refuse to overwrite a file we didn't generate (missing marker). Returns True if written."""
    if path.exists() and not _has_marker(path, marker):
        logger.warning("slashdocs: %s exists but was not generated by slashdocs; skipping", path)
        return False
    path.write_text(text, encoding="utf-8")
    return True


def write_docs(
    out_dir: Path,
    manifest: Manifest,
    diff: Diff,
    *,
    clean: bool = True,
    base_slug: str = "/commands",
) -> frozenset[str]:
    """Write pages, index, and sidebar meta. Returns the added/changed slugs whose
    page was skipped by the overwrite guard — callers must not treat these as
    settled, or a hand-written file at that path can never be retried."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_slug = {c.slug: c for c in manifest.commands}
    skipped = frozenset(
        slug
        for slug in (*diff.added, *diff.changed)
        if not _write_page(
            out_dir / f"{slug}.mdx", render_command(by_slug[slug], prefix=manifest.prefix)
        )
    )
    if clean:
        for slug in diff.removed:
            path = out_dir / f"{slug}.mdx"
            if path.exists() and _has_marker(path, GENERATED_MARKER):
                path.unlink()
    _write_page(out_dir / "index.mdx", render_index(manifest, base_slug=base_slug))
    _write_page(out_dir / "meta.json", render_meta(manifest), marker=_JSON_GENERATED_MARKER)
    return skipped

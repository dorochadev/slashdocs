"""Renders a Manifest into MDX files. CommonMark-only bodies so output renders
identically in Fumadocs, Nextra, Docusaurus, and Astro Starlight."""

from __future__ import annotations

import json
from pathlib import Path

from .differ import Diff
from .model import CommandDoc, Manifest, ParamDoc

GENERATED_MARKER = "generated_by: slashdocs"


def _yaml_str(value: str) -> str:
    return json.dumps(value)  # JSON string escaping is valid YAML


def _display_name(doc: CommandDoc) -> str:
    prefix = "!" if doc.kind == "prefix" else "/"
    return f"{prefix}{doc.name}"


def _usage(doc: CommandDoc) -> str:
    parts = [_display_name(doc)]
    parts += [f"<{p.name}>" if p.required else f"[{p.name}]" for p in doc.params]
    return " ".join(parts)


def _param_desc_cell(p: ParamDoc) -> str:
    parts = []
    if p.description:
        parts.append(p.description)
    if p.choices:
        parts.append("One of: " + ", ".join(f"`{c}`" for c in p.choices))
    return " — ".join(parts)


def _params_table(params: tuple[ParamDoc, ...], *, heading: bool = True) -> list[str]:
    lines = ["## Parameters", ""] if heading else []
    lines += [
        "| Name | Type | Required | Description |",
        "| ---- | ---- | -------- | ----------- |",
    ]
    for p in params:
        required = "yes" if p.required else "no"
        lines.append(f"| {p.name} | {p.type} | {required} | {_param_desc_cell(p)} |")
    lines.append("")
    return lines


def _frontmatter(doc: CommandDoc) -> list[str]:
    lines = [
        "---",
        f"title: {_yaml_str(_display_name(doc))}",
        f"description: {_yaml_str(doc.description)}",
        f"category: {_yaml_str(doc.category)}",
        GENERATED_MARKER,
    ]
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


def _body(doc: CommandDoc) -> list[str]:
    lines: list[str] = [""]
    if doc.description:
        lines += [doc.description, ""]
    lines += ["## Usage", ""]
    for usage in doc.examples or (_usage(doc),):
        lines += [f"`{usage}`", ""]
    if doc.params:
        lines += _params_table(doc.params)
    if doc.aliases:
        aliases = ", ".join(f"`{a}`" for a in doc.aliases)
        lines += [f"**Aliases:** {aliases}", ""]
    if doc.subcommands:
        lines += ["## Subcommands", ""]
        for sub in doc.subcommands:
            lines += [f"### {_display_name(sub)}", ""]
            if sub.description:
                lines += [sub.description, ""]
            lines += [f"`{_usage(sub)}`", ""]
            if sub.params:
                lines += _params_table(sub.params, heading=False)
    if doc.notes:
        lines += [doc.notes, ""]
    return lines


def render_command(doc: CommandDoc, *, base_slug: str = "/commands") -> str:
    text = "\n".join(_frontmatter(doc) + _body(doc))
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
            link = f"[{_display_name(cmd)}]({base_slug}/{cmd.slug})"
            lines.append(f"| {link} | {cmd.description} |")
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_meta(manifest: Manifest) -> str:
    ordered = sorted(manifest.commands, key=lambda c: (c.category, c.name))
    return json.dumps({"pages": ["index", *(c.slug for c in ordered)]}, indent=2) + "\n"


def write_docs(
    out_dir: Path,
    manifest: Manifest,
    diff: Diff,
    *,
    clean: bool = True,
    base_slug: str = "/commands",
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    by_slug = {c.slug: c for c in manifest.commands}
    for slug in (*diff.added, *diff.changed):
        path = out_dir / f"{slug}.mdx"
        path.write_text(render_command(by_slug[slug], base_slug=base_slug), encoding="utf-8")
    if clean:
        for slug in diff.removed:
            path = out_dir / f"{slug}.mdx"
            if path.exists() and GENERATED_MARKER in path.read_text(encoding="utf-8"):
                path.unlink()
    (out_dir / "index.mdx").write_text(
        render_index(manifest, base_slug=base_slug), encoding="utf-8"
    )
    (out_dir / "meta.json").write_text(render_meta(manifest), encoding="utf-8")

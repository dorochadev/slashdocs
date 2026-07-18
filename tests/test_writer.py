from pathlib import Path

from slashdocs.differ import Diff
from slashdocs.model import CommandDoc, Manifest, ParamDoc
from slashdocs.writer import (
    GENERATED_MARKER,
    render_command,
    render_index,
    render_meta,
    write_docs,
)

COINFLIP = CommandDoc(
    name="coinflip",
    slug="coinflip",
    kind="slash",
    description="Bet money on a coin flip.",
    category="Economy",
    params=(
        ParamDoc(name="amount", type="integer", required=True, description="Amount to bet"),
        ParamDoc(
            name="side",
            type="string",
            required=True,
            description="Which side to bet on",
            choices=("heads", "tails"),
        ),
    ),
    examples=("/coinflip 500 heads",),
)

EXPECTED_COINFLIP = """---
title: "/coinflip"
description: "Bet money on a coin flip."
category: "Economy"
generated_by: slashdocs
params:
  - name: "amount"
    type: "integer"
    required: true
    description: "Amount to bet"
  - name: "side"
    type: "string"
    required: true
    description: "Which side to bet on"
    choices: ["heads", "tails"]
---

Bet money on a coin flip.

## Usage

`/coinflip 500 heads`

## Parameters

| Name | Type | Required | Description |
| ---- | ---- | -------- | ----------- |
| amount | integer | yes | Amount to bet |
| side | string | yes | Which side to bet on — One of: `heads`, `tails` |
"""


def test_render_command_matches_golden_output() -> None:
    assert render_command(COINFLIP) == EXPECTED_COINFLIP


def test_render_command_without_examples_synthesizes_usage() -> None:
    doc = CommandDoc(
        name="pay",
        slug="pay",
        kind="slash",
        description="Send money.",
        params=(
            ParamDoc(name="user", type="user", required=True),
            ParamDoc(name="note", type="string", required=False),
        ),
    )
    out = render_command(doc)
    assert "`/pay <user> [note]`" in out


def test_render_prefix_command_shows_bang_and_aliases() -> None:
    doc = CommandDoc(
        name="ping",
        slug="ping",
        kind="prefix",
        description="Check latency.",
        aliases=("pong",),
    )
    out = render_command(doc)
    assert 'title: "!ping"' in out
    assert "**Aliases:** `pong`" in out


def test_render_subcommands_section() -> None:
    doc = CommandDoc(
        name="config",
        slug="config",
        kind="slash",
        description="Server configuration.",
        subcommands=(
            CommandDoc(
                name="config set",
                slug="",
                kind="slash",
                description="Set a value.",
                params=(ParamDoc(name="key", type="string", required=True),),
            ),
        ),
    )
    out = render_command(doc)
    assert "## Subcommands" in out
    assert "### /config set" in out
    assert "`/config set <key>`" in out


def test_render_index_groups_by_category() -> None:
    manifest = Manifest(
        commands=(
            COINFLIP,
            CommandDoc(name="ping", slug="ping", kind="prefix", description="Check latency."),
        )
    )
    out = render_index(manifest)
    assert "## Economy" in out and "## General" in out
    assert "[/coinflip](/commands/coinflip)" in out
    assert "[!ping](/commands/ping)" in out
    assert GENERATED_MARKER in out


def test_render_meta_lists_index_first() -> None:
    manifest = Manifest(commands=(COINFLIP,))
    assert '"index"' in render_meta(manifest)
    assert render_meta(manifest).index('"index"') < render_meta(manifest).index('"coinflip"')


def test_write_docs_writes_and_marker_guards_deletion(tmp_path: Path) -> None:
    manifest = Manifest(commands=(COINFLIP,))
    write_docs(tmp_path, manifest, Diff(added=("coinflip",)))
    assert (tmp_path / "coinflip.mdx").read_text(encoding="utf-8") == EXPECTED_COINFLIP
    assert (tmp_path / "index.mdx").exists() and (tmp_path / "meta.json").exists()

    # A user-owned file must never be deleted, even if listed as removed
    (tmp_path / "handwritten.mdx").write_text("# mine\n", encoding="utf-8")
    write_docs(tmp_path, Manifest(), Diff(removed=("handwritten", "coinflip")))
    assert (tmp_path / "handwritten.mdx").exists()
    assert not (tmp_path / "coinflip.mdx").exists()  # generated file: deleted


def test_write_docs_clean_false_keeps_removed_files(tmp_path: Path) -> None:
    manifest = Manifest(commands=(COINFLIP,))
    write_docs(tmp_path, manifest, Diff(added=("coinflip",)))
    write_docs(tmp_path, Manifest(), Diff(removed=("coinflip",)), clean=False)
    assert (tmp_path / "coinflip.mdx").exists()

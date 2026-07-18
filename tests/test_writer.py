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


def test_mdx_significant_characters_are_escaped_in_body() -> None:
    doc = CommandDoc(
        name="roll",
        slug="roll",
        kind="prefix",
        description="Rolls {dice}, e.g. <2d6>.",
        notes="Mention <user> to target {them}.",
    )
    out = render_command(doc)
    assert "Rolls \\{dice}, e.g. \\<2d6>." in out
    assert "Mention \\<user> to target \\{them}." in out


def test_table_cells_are_single_line_and_pipe_safe() -> None:
    doc = CommandDoc(
        name="kick",
        slug="kick",
        kind="prefix",
        description="Kick a member | fast.\n\nLong second paragraph.",
        params=(ParamDoc(name="who", type="user", required=True, description="a|b"),),
    )
    out = render_index(Manifest(commands=(doc,)))
    row = next(line for line in out.splitlines() if "!kick" in line)
    assert row == "| [!kick](/commands/kick) | Kick a member \\| fast. |"
    page = render_command(doc)
    assert "| who | user | yes | a\\|b |" in page


def test_overwrite_guard_protects_handwritten_pages(tmp_path: Path) -> None:
    (tmp_path / "coinflip.mdx").write_text("# mine\n", encoding="utf-8")
    (tmp_path / "index.mdx").write_text("# my index\n", encoding="utf-8")
    write_docs(tmp_path, Manifest(commands=(COINFLIP,)), Diff(added=("coinflip",)))
    assert (tmp_path / "coinflip.mdx").read_text(encoding="utf-8") == "# mine\n"
    assert (tmp_path / "index.mdx").read_text(encoding="utf-8") == "# my index\n"
    assert (tmp_path / "meta.json").exists()


def test_prefix_comes_from_manifest(tmp_path: Path) -> None:
    doc = CommandDoc(name="ping", slug="ping", kind="prefix", description="d")
    manifest = Manifest(commands=(doc,), prefix="?")
    write_docs(tmp_path, manifest, Diff(added=("ping",)))
    assert 'title: "?ping"' in (tmp_path / "ping.mdx").read_text(encoding="utf-8")
    assert "[?ping]" in (tmp_path / "index.mdx").read_text(encoding="utf-8")


def test_permission_cooldown_and_tier_badges() -> None:
    doc = CommandDoc(
        name="ban",
        slug="ban",
        kind="prefix",
        description="Ban someone.",
        permissions=("Ban Members", "Booster Only"),
        cooldown_rate=1,
        cooldown_per=5.0,
        tier="Premium",
    )
    out = render_command(doc)
    assert 'permissions: ["Ban Members", "Booster Only"]' in out
    assert 'cooldown: "1/5s"' in out
    assert 'tier: "Premium"' in out
    assert "**Requires:** Ban Members, Booster Only · **Cooldown:** 1/5s · 👑 Premium" in out


def test_badges_are_mdx_escaped() -> None:
    doc = CommandDoc(
        name="vip",
        slug="vip",
        kind="prefix",
        description="d",
        permissions=("<3 fans",),
        tier="{Premium}",
    )
    out = render_command(doc)
    badges_line = next(line for line in out.splitlines() if line.startswith("**Requires:**"))
    assert badges_line == "**Requires:** \\<3 fans · 👑 \\{Premium}"


def test_params_table_name_and_type_are_escaped() -> None:
    doc = CommandDoc(
        name="weird",
        slug="weird",
        kind="slash",
        params=(ParamDoc(name="a|b<c", type="str|int<foo", required=True),),
    )
    out = render_command(doc)
    assert "| a\\|b\\<c | str\\|int\\<foo | yes |" in out

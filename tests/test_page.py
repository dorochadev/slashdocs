import json
import shutil
from pathlib import Path

import pytest

from slashdocs.model import CommandDoc, Manifest, ParamDoc
from slashdocs.page import render_page, write_page

requires_node = pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")


def _manifest() -> Manifest:
    return Manifest(
        prefix="?",
        commands=(
            CommandDoc(
                name="ban",
                slug="ban",
                kind="slash",
                description="Ban someone.",
                category="Moderation",
                permissions=("Ban Members",),
                tier="Premium",
                params=(ParamDoc(name="user", type="user", required=True),),
                subcommands=(
                    CommandDoc(name="ban temp", slug="", kind="slash", description="Temp ban."),
                ),
            ),
            CommandDoc(
                name="ping",
                slug="ping",
                kind="prefix",
                description="Check latency.",
                category="General",
                aliases=("pong",),
                cooldown_rate=1,
                cooldown_per=5.0,
            ),
        ),
    )


def test_page_embeds_parseable_data_island() -> None:
    html = render_page(_manifest())
    start = html.index('<script id="slashdocs-data" type="application/json">')
    payload = html[start:].split(">", 1)[1].split("</script>", 1)[0]
    data = json.loads(payload)
    assert data["prefix"] == "?"
    assert [c["name"] for c in data["commands"]] == ["ban", "ping"]


def test_page_data_island_cannot_be_broken_out_of() -> None:
    doc = CommandDoc(
        name="evil", slug="evil", kind="slash", description="</script><script>alert(1)</script>"
    )
    html = render_page(Manifest(commands=(doc,)))
    payload_zone = html.split('<script id="slashdocs-data"', 1)[1]
    island = payload_zone.split("</script>", 1)[0]
    # No literal '</' may survive inside the island — the parser would close the
    # script element there; escaped as '<\/' the payload stays inert JSON.
    assert "</" not in island
    assert "<\\/script><script>alert(1)<\\/script>" in island


def test_page_is_self_contained_and_customizable() -> None:
    html = render_page(_manifest(), title="MyBot Commands", accent="#ff0066")
    assert "<title>MyBot Commands</title>" in html
    assert "#ff0066" in html
    for external in ('src="http', "src='http", 'href="http', "@import", "//cdn"):
        assert external not in html


def test_write_page_only_writes_on_change(tmp_path: Path) -> None:
    path = tmp_path / "public" / "commands.html"
    assert write_page(path, _manifest()) is True
    assert write_page(path, _manifest()) is False
    path.unlink()
    assert write_page(path, _manifest()) is True


def test_title_or_accent_containing_a_placeholder_token_does_not_corrupt_output() -> None:
    html = render_page(Manifest(), title="My __ACCENT__ Bot", accent="#123456")
    assert "<h1>My __ACCENT__ Bot</h1>" in html
    assert "--accent: #123456" in html


def _extract_js_function(html: str, name: str) -> str:
    """Pull one top-level `function name(...) { ... }` out of the embedded script,
    by brace-matching from the `function name(` marker."""
    start = html.index(f"function {name}(")
    depth = 0
    end = start
    for i, ch in enumerate(html[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return html[start:end]


@requires_node
def test_hybrid_commands_show_both_forms_in_the_browser() -> None:
    import json
    import subprocess

    html = render_page(_manifest())
    displayname_src = _extract_js_function(html, "displayName")
    script = f"""
    {displayname_src}
    var prefix = "?";
    console.log(JSON.stringify([
      displayName({{kind: "hybrid", name: "balance"}}),
      displayName({{kind: "slash", name: "ban"}}),
      displayName({{kind: "prefix", name: "ping"}}),
    ]));
    """
    result = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, timeout=10, check=True
    )
    names = json.loads(result.stdout)
    assert names == ["/balance  ·  ?balance", "/ban", "?ping"]

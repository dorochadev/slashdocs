import json
from pathlib import Path

from slashdocs.model import CommandDoc, Manifest, ParamDoc
from slashdocs.page import render_page, write_page


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

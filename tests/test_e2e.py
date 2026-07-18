"""End-to-end: a real (offline) discord.py bot through all three outputs, twice."""

import json
from pathlib import Path

from conftest import make_bot
from slashdocs import commands_json, commands_page, mdx
from slashdocs.runtime import generate


def _mtimes(root: Path) -> dict[str, int]:
    return {str(p): p.stat().st_mtime_ns for p in root.rglob("*") if p.is_file()}


def test_all_outputs_end_to_end_and_idempotent(tmp_path: Path) -> None:
    outputs = [
        mdx(tmp_path / "docs"),
        commands_json(tmp_path / "site" / "commands.json"),
        commands_page(tmp_path / "site" / "commands.html", title="Noctaly-style"),
    ]
    generate(make_bot(), outputs=outputs)

    data = json.loads((tmp_path / "site" / "commands.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 2
    names = {c["name"] for c in data["commands"]}
    assert {"balance", "coinflip", "config", "ping"} <= names
    balance = next(c for c in data["commands"] if c["name"] == "balance")
    assert balance["permissions"] == ["Booster Only"]
    assert balance["tier"] == "Premium"
    assert balance["params"][0]["description"] == "Whose balance to view"

    html = (tmp_path / "site" / "commands.html").read_text(encoding="utf-8")
    assert "slashdocs-data" in html and "Noctaly-style" in html

    index = (tmp_path / "docs" / "index.mdx").read_text(encoding="utf-8")
    assert "[/balance](/commands/balance)" in index
    assert (tmp_path / "docs" / "balance.mdx").exists()

    # Second run with an unchanged bot writes nothing anywhere.
    snapshot = _mtimes(tmp_path)
    generate(make_bot(), outputs=outputs)
    assert _mtimes(tmp_path) == snapshot

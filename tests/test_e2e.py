"""End-to-end: a real (offline) discord.py bot through all three outputs, twice."""

import json
from pathlib import Path

from conftest import make_bot
from slashdocs import commands_json, commands_page, mdx
from slashdocs.differ import STATE_FILENAME
from slashdocs.runtime import generate
from slashdocs.writer import GENERATED_MARKER


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


def test_upgrade_cleans_up_a_slug_that_sanitization_renamed(tmp_path: Path) -> None:
    """A pre-0.2.0 install wrote raw-name slugs (no sanitization). After upgrading,
    the sanitized slug for the same command differs, and the stale page under the
    old slug must be swept away rather than orphaned forever."""
    docs = tmp_path / "docs"
    docs.mkdir()
    old_page = docs / "coin_flip.mdx"  # pretend v1's raw-name slug was "coin_flip"
    old_page.write_text(f"---\n{GENERATED_MARKER}\n---\nstale\n", encoding="utf-8")
    v1_state = {
        "manifest": {
            "schema_version": 1,
            "commands": [{"name": "coinflip", "slug": "coin_flip", "kind": "slash"}],
        }
    }
    (docs / STATE_FILENAME).write_text(json.dumps(v1_state), encoding="utf-8")

    generate(make_bot(), outputs=[mdx(docs)])

    assert not old_page.exists()  # orphaned old-slug page is cleaned up
    assert (docs / "coinflip.mdx").exists()  # sanitized slug: no rename needed here


def test_orphan_cleaned_up_even_when_state_is_completely_lost(tmp_path: Path) -> None:
    """No baseline at all (missing/corrupt state) — compute_diff can't produce a
    'removed' list, so write_docs must fall back to sweeping the directory itself."""
    docs = tmp_path / "docs"
    docs.mkdir()
    orphan = docs / "deleted-command.mdx"
    orphan.write_text(f"---\n{GENERATED_MARKER}\n---\nstale\n", encoding="utf-8")
    # No .slashdocs-manifest.json at all: state was never written, or the file was lost.

    generate(make_bot(), outputs=[mdx(docs)])

    assert not orphan.exists()
    assert (docs / "coinflip.mdx").exists()  # the real, current commands still write fine

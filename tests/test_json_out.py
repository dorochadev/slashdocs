import json
from pathlib import Path

from slashdocs.json_out import render_json, write_json
from slashdocs.model import CommandDoc, Manifest, ParamDoc


def _manifest() -> Manifest:
    return Manifest(
        prefix="?",
        commands=(
            CommandDoc(
                name="ban",
                slug="ban",
                kind="slash",
                description="Ban someone.",
                permissions=("Ban Members",),
                subcommands=(
                    CommandDoc(
                        name="ban temp",
                        slug="",
                        kind="slash",
                        params=(ParamDoc(name="days", type="integer", required=True),),
                    ),
                ),
            ),
        ),
    )


def test_render_json_is_valid_and_complete() -> None:
    data = json.loads(render_json(_manifest()))
    assert data["schema_version"] == 2
    assert data["prefix"] == "?"
    (ban,) = data["commands"]
    assert ban["permissions"] == ["Ban Members"]
    assert ban["subcommands"][0]["params"][0]["name"] == "days"


def test_render_json_is_deterministic() -> None:
    assert render_json(_manifest()) == render_json(_manifest())
    assert render_json(_manifest()).endswith("\n")


def test_write_json_only_writes_on_change(tmp_path: Path) -> None:
    path = tmp_path / "site" / "commands.json"
    assert write_json(path, _manifest()) is True  # created (parents included)
    before = path.stat().st_mtime_ns
    assert write_json(path, _manifest()) is False  # unchanged: not rewritten
    assert path.stat().st_mtime_ns == before


def test_write_json_recreates_deleted_file(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    write_json(path, _manifest())
    path.unlink()
    assert write_json(path, _manifest()) is True
    assert json.loads(path.read_text(encoding="utf-8"))["prefix"] == "?"

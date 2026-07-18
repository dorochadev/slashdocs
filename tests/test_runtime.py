import logging
from pathlib import Path

import pytest

from conftest import make_bot
from slashdocs.runtime import attach, generate


def _mtimes(path: Path) -> dict[str, int]:
    return {p.name: p.stat().st_mtime_ns for p in path.iterdir()}


def test_generate_writes_docs_then_is_idempotent(tmp_path: Path) -> None:
    bot = make_bot()
    first = generate(bot, tmp_path)
    assert not first.is_empty
    assert (tmp_path / "coinflip.mdx").exists()
    assert (tmp_path / "index.mdx").exists()
    assert (tmp_path / "meta.json").exists()
    assert (tmp_path / ".slashdocs-manifest.json").exists()

    snapshot = _mtimes(tmp_path)
    second = generate(bot, tmp_path)
    assert second.is_empty
    assert _mtimes(tmp_path) == snapshot  # zero writes on the second run


def test_generate_detects_a_new_command(tmp_path: Path) -> None:
    bot = make_bot()
    generate(bot, tmp_path)

    @bot.command(name="roulette", help="Spin the wheel.")
    async def roulette(ctx) -> None: ...  # type: ignore[no-untyped-def]

    diff = generate(bot, tmp_path)
    assert diff.added == ("roulette",)
    assert not diff.changed and not diff.removed
    assert (tmp_path / "roulette.mdx").exists()


async def test_attach_registers_a_single_run_once_listener(tmp_path: Path) -> None:
    bot = make_bot()
    attach(bot, out=tmp_path)
    attach(bot, out=tmp_path)  # second attach is a no-op
    listeners = bot.extra_events.get("on_ready", [])
    assert len(listeners) == 1

    await listeners[0]()
    assert (tmp_path / "index.mdx").exists()

    marker = tmp_path / "index.mdx"
    before = marker.stat().st_mtime_ns
    await listeners[0]()  # run-once: second ready event does nothing at all
    assert marker.stat().st_mtime_ns == before


async def test_attach_listener_never_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    bot = make_bot()
    attach(bot, out=tmp_path)

    import slashdocs.runtime as runtime

    def boom(_bot) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("walker exploded")

    monkeypatch.setattr(runtime, "walk_bot", boom)
    with caplog.at_level(logging.ERROR, logger="slashdocs"):
        await bot.extra_events["on_ready"][0]()  # must not raise
    assert any("docs generation failed" in r.message for r in caplog.records)


def test_attach_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        attach(make_bot(), out=tmp_path, fmt="html")

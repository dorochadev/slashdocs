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

    def boom(*_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("walker exploded")

    monkeypatch.setattr(runtime, "walk_bot", boom)
    with caplog.at_level(logging.ERROR, logger="slashdocs"):
        await bot.extra_events["on_ready"][0]()  # must not raise
    assert any("docs generation failed" in r.message for r in caplog.records)


def test_attach_rejects_conflicting_output_configs(tmp_path: Path) -> None:
    from slashdocs.outputs import mdx

    with pytest.raises(ValueError):
        attach(make_bot(), out=tmp_path, outputs=[mdx(tmp_path)])
    with pytest.raises(ValueError):
        attach(make_bot(), outputs=[])


async def test_attach_outputs_produce_all_artifacts(tmp_path: Path) -> None:
    from slashdocs import commands_json, commands_page, mdx

    bot = make_bot()
    attach(
        bot,
        outputs=[
            mdx(tmp_path / "docs"),
            commands_json(tmp_path / "site" / "commands.json"),
            commands_page(tmp_path / "site" / "commands.html", title="MyBot Commands"),
        ],
    )
    await bot.extra_events["on_ready"][0]()
    assert (tmp_path / "docs" / "index.mdx").exists()
    assert (tmp_path / "site" / "commands.json").exists()
    html = (tmp_path / "site" / "commands.html").read_text(encoding="utf-8")
    assert "<title>MyBot Commands</title>" in html


async def test_on_ready_offloads_generation_to_a_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    offloaded: list[str] = []
    orig = asyncio.to_thread

    async def spy(fn, *args, **kwargs):  # type: ignore[no-untyped-def]
        offloaded.append(fn.__name__)
        return await orig(fn, *args, **kwargs)

    import slashdocs.runtime as runtime

    monkeypatch.setattr(runtime.asyncio, "to_thread", spy)
    bot = make_bot()
    attach(bot, out=tmp_path)
    await bot.extra_events["on_ready"][0]()
    assert offloaded == ["generate"]
    assert (tmp_path / "index.mdx").exists()


def test_one_failing_output_does_not_stop_the_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import slashdocs.runtime as runtime
    from slashdocs import commands_json, commands_page

    def boom(*_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("json exploded")

    monkeypatch.setattr(runtime, "write_json", boom)
    with caplog.at_level(logging.ERROR, logger="slashdocs"):
        generate(
            make_bot(),
            outputs=[
                commands_json(tmp_path / "commands.json"),
                commands_page(tmp_path / "commands.html"),
            ],
        )
    assert (tmp_path / "commands.html").exists()
    assert any("failed" in r.message for r in caplog.records)


def test_generate_prefix_override(tmp_path: Path) -> None:
    generate(make_bot(), tmp_path, prefix="?")
    assert "[?ping]" in (tmp_path / "index.mdx").read_text(encoding="utf-8")

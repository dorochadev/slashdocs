from pathlib import Path

from slashdocs._io import write_if_changed


def test_write_if_changed_creates_parents_and_reports_written(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "commands.json"
    assert write_if_changed(path, "hello\n") is True
    assert path.read_text(encoding="utf-8") == "hello\n"


def test_write_if_changed_skips_identical_content(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    write_if_changed(path, "hello\n")
    before = path.stat().st_mtime_ns
    assert write_if_changed(path, "hello\n") is False
    assert path.stat().st_mtime_ns == before


def test_write_if_changed_overwrites_non_utf8_content(tmp_path: Path) -> None:
    path = tmp_path / "commands.json"
    path.write_bytes(b"\xff\xfe not utf-8")
    assert write_if_changed(path, "hello\n") is True
    assert path.read_text(encoding="utf-8") == "hello\n"

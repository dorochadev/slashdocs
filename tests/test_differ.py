from pathlib import Path

from slashdocs.differ import STATE_FILENAME, compute_diff, load_state, save_state
from slashdocs.model import CommandDoc, Manifest


def _cmd(slug: str, description: str = "d") -> CommandDoc:
    return CommandDoc(name=slug, slug=slug, kind="slash", description=description)


def test_no_previous_state_means_everything_added() -> None:
    diff = compute_diff(None, Manifest(commands=(_cmd("a"), _cmd("b"))))
    assert diff.added == ("a", "b") and not diff.changed and not diff.removed
    assert not diff.is_empty


def test_identical_manifests_produce_empty_diff() -> None:
    m = Manifest(commands=(_cmd("a"),))
    assert compute_diff(m, m).is_empty


def test_added_changed_removed() -> None:
    old = Manifest(commands=(_cmd("a"), _cmd("b"), _cmd("c")))
    new = Manifest(commands=(_cmd("a"), _cmd("b", description="different"), _cmd("d")))
    diff = compute_diff(old, new)
    assert diff.added == ("d",)
    assert diff.changed == ("b",)
    assert diff.removed == ("c",)


def test_state_round_trip(tmp_path: Path) -> None:
    m = Manifest(commands=(_cmd("a"),))
    save_state(tmp_path, m)
    assert load_state(tmp_path) == m


def test_load_state_missing_returns_none(tmp_path: Path) -> None:
    assert load_state(tmp_path) is None


def test_load_state_corrupt_returns_none(tmp_path: Path) -> None:
    (tmp_path / STATE_FILENAME).write_text("{not json", encoding="utf-8")
    assert load_state(tmp_path) is None


def test_prefix_change_marks_all_common_slugs_changed() -> None:
    old = Manifest(commands=(_cmd("a"), _cmd("b")), prefix="!")
    new = Manifest(commands=(_cmd("a"), _cmd("b")), prefix="?")
    diff = compute_diff(old, new)
    assert diff.changed == ("a", "b")
    assert not diff.added and not diff.removed


def test_load_state_from_old_schema_returns_none(tmp_path: Path) -> None:
    import json

    v1 = {"manifest": {"schema_version": 1, "commands": []}}
    (tmp_path / STATE_FILENAME).write_text(json.dumps(v1), encoding="utf-8")
    assert load_state(tmp_path) is None

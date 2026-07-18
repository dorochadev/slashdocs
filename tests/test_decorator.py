import pytest

from slashdocs.decorator import DocsExtras, docs, get_extras


class FakeCommand:
    """Duck-types discord.py's Command: has an .extras dict and a .callback."""

    def __init__(self, callback):
        self.extras: dict = {}
        self.callback = callback


async def _noop() -> None: ...


def test_docs_on_bare_function_sets_attribute() -> None:
    fn = docs(category="Economy", example="/coinflip 500 heads")(_noop)
    extras = get_extras(fn)
    assert extras == DocsExtras(category="Economy", examples=("/coinflip 500 heads",))


def test_docs_on_command_object_uses_extras_dict() -> None:
    cmd = FakeCommand(_noop)
    docs(hidden=True, notes="Owner only.")(cmd)
    assert get_extras(cmd) == DocsExtras(hidden=True, notes="Owner only.")
    assert "slashdocs" in cmd.extras


def test_get_extras_falls_back_to_callback_attribute() -> None:
    async def fn() -> None: ...

    docs(category="Fun")(fn)
    cmd = FakeCommand(fn)
    cmd.extras.clear()  # nothing stored on the object itself
    assert get_extras(cmd) == DocsExtras(category="Fun")


def test_example_list_normalizes_to_tuple() -> None:
    fn = docs(example=["/a", "/b"])(lambda: None)
    extras = get_extras(fn)
    assert extras is not None and extras.examples == ("/a", "/b")


def test_docs_on_non_command_raises_type_error() -> None:
    with pytest.raises(TypeError):
        docs(category="Nope")(42)  # type: ignore[arg-type]


def test_get_extras_returns_none_when_absent() -> None:
    async def undecorated() -> None: ...

    assert get_extras(undecorated) is None
    assert get_extras(object()) is None

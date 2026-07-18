"""The optional @docs decorator. Never imports discord.py — it duck-types on
the ``extras`` dict that every discord.py Command object exposes."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

EXTRAS_KEY = "slashdocs"
_FUNC_ATTR = "__slashdocs_extras__"

T = TypeVar("T")


@dataclass(frozen=True)
class DocsExtras:
    category: str | None = None
    examples: tuple[str, ...] = ()
    hidden: bool = False
    notes: str = ""
    permissions: tuple[str, ...] = ()
    tier: str = ""


def docs(
    *,
    category: str | None = None,
    example: str | list[str] | None = None,
    hidden: bool = False,
    notes: str = "",
    permissions: str | list[str] | None = None,
    tier: str = "",
) -> Callable[[T], T]:
    """Attach docs metadata to a discord.py command (any decorator order) or
    a bare coroutine function (below the command decorator)."""
    if example is None:
        examples: tuple[str, ...] = ()
    elif isinstance(example, str):
        examples = (example,)
    else:
        examples = tuple(example)
    if permissions is None:
        perms: tuple[str, ...] = ()
    elif isinstance(permissions, str):
        perms = (permissions,)
    else:
        perms = tuple(permissions)
    extras = DocsExtras(
        category=category,
        examples=examples,
        hidden=hidden,
        notes=notes,
        permissions=perms,
        tier=tier,
    )

    def wrap(target: T) -> T:
        cmd_extras = getattr(target, "extras", None)
        if isinstance(cmd_extras, dict):
            cmd_extras[EXTRAS_KEY] = extras
        elif callable(target):
            setattr(target, _FUNC_ATTR, extras)
        else:
            raise TypeError(
                f"@docs cannot be applied to {target!r}: "
                "expected a discord.py command or a coroutine function"
            )
        return target

    return wrap


def get_extras(obj: Any) -> DocsExtras | None:
    """Retrieve extras from a command object, its callback, or a bare function."""
    cmd_extras = getattr(obj, "extras", None)
    if isinstance(cmd_extras, dict):
        found = cmd_extras.get(EXTRAS_KEY)
        if isinstance(found, DocsExtras):
            return found
    callback = getattr(obj, "callback", None)
    if callback is not None:
        found = getattr(callback, _FUNC_ATTR, None)
        if isinstance(found, DocsExtras):
            return found
    found = getattr(obj, _FUNC_ATTR, None)
    return found if isinstance(found, DocsExtras) else None

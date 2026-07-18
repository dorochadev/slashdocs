"""Turns a live discord.py bot into a Manifest. The ONLY module that imports discord."""

from __future__ import annotations

import re
from typing import Any

from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING

from .decorator import DocsExtras, get_extras
from .model import CommandDoc, Manifest, ParamDoc


def walk_bot(bot: commands.Bot, *, prefix: str | None = None) -> Manifest:
    out: list[CommandDoc] = []
    slugs: set[str] = set()

    hybrid_names = {
        c.name
        for c in bot.commands
        if isinstance(c, (commands.HybridCommand, commands.HybridGroup))
    }

    # Slash commands first so they claim the clean slugs.
    for tree_cmd in sorted(bot.tree.get_commands(), key=lambda c: c.name):
        if tree_cmd.name in hybrid_names:
            continue  # documented once, via the prefix walk below
        doc: CommandDoc | None
        if isinstance(tree_cmd, app_commands.Group):
            doc = _walk_group(tree_cmd, slugs)
        elif isinstance(tree_cmd, app_commands.Command):
            doc = _walk_slash(tree_cmd, slugs)
        else:
            continue  # context menus: out of scope for v1
        if doc is not None:
            out.append(doc)

    for prefix_cmd in sorted(bot.commands, key=lambda c: c.qualified_name):
        if _is_framework_internal(prefix_cmd):
            continue  # e.g. discord.py's auto-injected default help command
        doc = _walk_prefix(prefix_cmd, slugs)
        if doc is not None:
            out.append(doc)

    out.sort(key=lambda d: (d.category, d.name))
    return Manifest(
        commands=tuple(out),
        prefix=prefix if prefix is not None else _detect_prefix(bot),
    )


def _detect_prefix(bot: commands.Bot) -> str:
    raw = bot.command_prefix
    if isinstance(raw, str):
        return raw
    if isinstance(raw, (list, tuple)) and raw and isinstance(raw[0], str):
        return raw[0]
    return "!"  # callable prefixes are opaque; use walk_bot(prefix=...) to override


def _perm_name(flag: str) -> str:
    return flag.replace("_", " ").title()


def _merge_permissions(introspected: tuple[str, ...], extras: DocsExtras | None) -> tuple[str, ...]:
    extra = extras.permissions if extras else ()
    return tuple(dict.fromkeys((*introspected, *extra)))


def _slash_permissions(cmd: object) -> tuple[str, ...]:
    perms = getattr(cmd, "default_permissions", None)
    if perms is None:
        return ()
    return tuple(_perm_name(name) for name, value in perms if value)


def _check_permissions(cmd: object) -> tuple[str, ...]:
    """Best-effort: read the perms dict out of @has_permissions-style check closures."""
    names: list[str] = []
    for check in getattr(cmd, "checks", ()):
        try:
            freevars = check.__code__.co_freevars
            closure = check.__closure__ or ()
            for var, cell in zip(freevars, closure, strict=False):
                if var == "perms" and isinstance(cell.cell_contents, dict):
                    names.extend(_perm_name(k) for k, v in cell.cell_contents.items() if v)
        except Exception:  # arbitrary user checks; introspection must never break the walk
            continue
    return tuple(dict.fromkeys(names))


def _cooldown(cmd: object) -> tuple[int, float]:
    """Prefix/hybrid cooldowns only; slash-side cooldown checks are not introspectable."""
    cd = getattr(cmd, "cooldown", None)
    rate = getattr(cd, "rate", None)
    per = getattr(cd, "per", None)
    if rate is None or per is None:
        return (0, 0.0)
    return (int(rate), float(per))


def _walk_slash(
    cmd: app_commands.Command[Any, ..., Any],
    slugs: set[str],
    *,
    as_sub: bool = False,
) -> CommandDoc | None:
    extras = get_extras(cmd)
    if extras is not None and extras.hidden:
        return None
    return CommandDoc(
        name=cmd.qualified_name,
        slug="" if as_sub else _claim_slug(cmd.name, slugs),
        kind="slash",
        description=_clean_desc(cmd.description),
        category=_category(extras, _cog_name(cmd)),
        params=tuple(_param_from_app(p) for p in cmd.parameters),
        examples=extras.examples if extras else (),
        notes=extras.notes if extras else "",
        permissions=_merge_permissions(_slash_permissions(cmd), extras),
        tier=extras.tier if extras else "",
    )


def _walk_group(
    group: app_commands.Group, slugs: set[str], *, as_sub: bool = False
) -> CommandDoc | None:
    extras = get_extras(group)
    if extras is not None and extras.hidden:
        return None
    subs: list[CommandDoc] = []
    for sub in sorted(group.commands, key=lambda c: c.name):
        if isinstance(sub, app_commands.Group):
            sub_doc = _walk_group(sub, slugs, as_sub=True)
        else:
            sub_doc = _walk_slash(sub, slugs, as_sub=True)
        if sub_doc is not None:
            subs.append(sub_doc)
    return CommandDoc(
        name=group.qualified_name,
        slug="" if as_sub else _claim_slug(group.name, slugs),
        kind="slash",
        description=_clean_desc(group.description),
        category=_category(extras, _cog_name(group)),
        examples=extras.examples if extras else (),
        notes=extras.notes if extras else "",
        permissions=_merge_permissions(_slash_permissions(group), extras),
        tier=extras.tier if extras else "",
        subcommands=tuple(subs),
    )


def _walk_prefix(
    cmd: commands.Command,  # type: ignore[type-arg]
    slugs: set[str],
    *,
    as_sub: bool = False,
) -> CommandDoc | None:
    if cmd.hidden:
        return None
    extras = get_extras(cmd)
    if extras is not None and extras.hidden:
        return None
    is_hybrid = isinstance(cmd, (commands.HybridCommand, commands.HybridGroup))
    rate, per = _cooldown(cmd)
    subs: tuple[CommandDoc, ...] = ()
    if isinstance(cmd, commands.Group):
        subs = tuple(
            doc
            for doc in (
                _walk_prefix(sub, slugs, as_sub=True)
                for sub in sorted(cmd.commands, key=lambda c: c.qualified_name)
            )
            if doc is not None
        )
    return CommandDoc(
        name=cmd.qualified_name,
        slug="" if as_sub else _claim_slug(cmd.name, slugs, fallback=f"prefix-{cmd.name}"),
        kind="hybrid" if is_hybrid else "prefix",
        # description= on hybrids lands in cmd.description, not help/brief
        description=cmd.help or cmd.brief or cmd.description or "",
        category=_category(extras, cmd.cog_name),
        params=tuple(_param_from_prefix(name, p) for name, p in cmd.clean_params.items()),
        examples=extras.examples if extras else (),
        notes=extras.notes if extras else "",
        aliases=tuple(cmd.aliases),
        permissions=_merge_permissions(_check_permissions(cmd), extras),
        cooldown_rate=rate,
        cooldown_per=per,
        tier=extras.tier if extras else "",
        subcommands=subs,
    )


def _param_from_app(p: app_commands.Parameter) -> ParamDoc:
    return ParamDoc(
        name=p.name,
        type=p.type.name,
        required=p.required,
        description=_clean_desc(p.description),
        choices=tuple(str(c.name) for c in p.choices),
        default=None if p.default is MISSING else repr(p.default),
    )


def _param_from_prefix(name: str, p: commands.Parameter) -> ParamDoc:
    if p.annotation is p.empty:
        type_name = "string"
    else:
        type_name = getattr(p.annotation, "__name__", str(p.annotation)).lower()
    return ParamDoc(
        name=name,
        type=type_name,
        required=p.required,
        description=p.description or "",
    )


def _cog_name(cmd: object) -> str | None:
    binding = getattr(cmd, "binding", None)
    if isinstance(binding, commands.Cog):
        return binding.qualified_name
    return None


def _category(extras: DocsExtras | None, cog_name: str | None) -> str:
    if extras is not None and extras.category:
        return extras.category
    return cog_name or "General"


def _is_framework_internal(cmd: commands.Command) -> bool:  # type: ignore[type-arg]
    """True for commands discord.py injects itself (their callback lives in discord.*)."""
    module = getattr(cmd.callback, "__module__", "") or ""
    return module.startswith("discord.")


def _clean_desc(desc: str) -> str:
    return "" if desc == "…" else desc  # discord.py's placeholder for "no description"


_RESERVED_SLUGS = frozenset({"index", "meta"})  # filenames the writer owns


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "cmd"


def _claim_slug(name: str, slugs: set[str], *, fallback: str | None = None) -> str:
    base = _slugify(name)
    if base in _RESERVED_SLUGS or base in slugs:
        base = _slugify(fallback) if fallback else f"{base}-cmd"
    slug = base
    counter = 2
    while slug in slugs or slug in _RESERVED_SLUGS:
        slug = f"{base}-{counter}"
        counter += 1
    slugs.add(slug)
    return slug

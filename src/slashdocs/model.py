"""Frozen data model shared by all slashdocs layers. Never imports discord.py."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ParamDoc:
    name: str
    type: str
    required: bool
    description: str = ""
    choices: tuple[str, ...] = ()
    default: str | None = None


@dataclass(frozen=True)
class CommandDoc:
    name: str  # qualified name, e.g. "coinflip" or "config set"
    slug: str  # file-safe stem; "" for subcommands (rendered inside the parent page)
    kind: str  # "slash" | "prefix" | "hybrid"
    description: str = ""
    category: str = "General"
    params: tuple[ParamDoc, ...] = ()
    examples: tuple[str, ...] = ()
    notes: str = ""
    aliases: tuple[str, ...] = ()
    permissions: tuple[str, ...] = ()  # human-readable, e.g. "Ban Members", "Booster Only"
    cooldown_rate: int = 0  # 0 means no cooldown
    cooldown_per: float = 0.0
    tier: str = ""  # e.g. "Premium"; rendered as a badge
    subcommands: tuple[CommandDoc, ...] = ()

    def content_hash(self) -> str:
        return _sha256(_canonical(asdict(self)))


def _param_from_dict(data: dict[str, Any]) -> ParamDoc:
    return ParamDoc(
        name=data["name"],
        type=data["type"],
        required=data["required"],
        description=data.get("description", ""),
        choices=tuple(data.get("choices", ())),
        default=data.get("default"),
    )


def _command_from_dict(data: dict[str, Any]) -> CommandDoc:
    return CommandDoc(
        name=data["name"],
        slug=data["slug"],
        kind=data["kind"],
        description=data.get("description", ""),
        category=data.get("category", "General"),
        params=tuple(_param_from_dict(p) for p in data.get("params", ())),
        examples=tuple(data.get("examples", ())),
        notes=data.get("notes", ""),
        aliases=tuple(data.get("aliases", ())),
        permissions=tuple(data.get("permissions", ())),
        cooldown_rate=data.get("cooldown_rate", 0),
        cooldown_per=data.get("cooldown_per", 0.0),
        tier=data.get("tier", ""),
        subcommands=tuple(_command_from_dict(c) for c in data.get("subcommands", ())),
    )


@dataclass(frozen=True)
class Manifest:
    commands: tuple[CommandDoc, ...] = ()
    prefix: str = "!"
    schema_version: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Manifest:
        return cls(
            commands=tuple(_command_from_dict(c) for c in data.get("commands", ())),
            prefix=data.get("prefix", "!"),
            schema_version=data.get("schema_version", 2),
        )

    def canonical_json(self) -> str:
        return _canonical(self.to_dict())

    def content_hash(self) -> str:
        return _sha256(self.canonical_json())

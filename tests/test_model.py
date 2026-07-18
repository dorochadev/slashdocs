import json

from slashdocs.model import CommandDoc, Manifest, ParamDoc


def _sample_manifest() -> Manifest:
    return Manifest(
        commands=(
            CommandDoc(
                name="coinflip",
                slug="coinflip",
                kind="slash",
                description="Bet money on a coin flip.",
                category="Economy",
                notes="Requires economy.",
                aliases=("cf",),
                params=(
                    ParamDoc(
                        name="amount", type="integer", required=True, description="Amount to bet"
                    ),
                    ParamDoc(
                        name="side",
                        type="string",
                        required=True,
                        choices=("heads", "tails"),
                        default="heads",
                    ),
                ),
                examples=("/coinflip 500 heads",),
            ),
            CommandDoc(
                name="config",
                slug="config",
                kind="slash",
                description="Server configuration.",
                subcommands=(
                    CommandDoc(
                        name="config set",
                        slug="",
                        kind="slash",
                        description="Set a value.",
                    ),
                ),
            ),
        )
    )


def test_manifest_round_trips_through_dict() -> None:
    m = _sample_manifest()
    assert Manifest.from_dict(m.to_dict()) == m


def test_canonical_json_is_deterministic() -> None:
    m = _sample_manifest()
    assert m.canonical_json() == _sample_manifest().canonical_json()
    assert '"schema_version":1' in m.canonical_json()  # compact separators, sorted keys


def test_manifest_round_trips_through_json_text() -> None:
    m = _sample_manifest()
    assert Manifest.from_dict(json.loads(m.canonical_json())) == m


def test_content_hash_changes_when_content_changes() -> None:
    m = _sample_manifest()
    cmd = m.commands[0]
    changed = CommandDoc(**{**_asdict_shallow(cmd), "description": "Different."})
    assert cmd.content_hash() != changed.content_hash()
    assert cmd.content_hash() == m.commands[0].content_hash()  # stable


def _asdict_shallow(c: CommandDoc) -> dict:
    return {
        "name": c.name,
        "slug": c.slug,
        "kind": c.kind,
        "description": c.description,
        "category": c.category,
        "params": c.params,
        "examples": c.examples,
        "notes": c.notes,
        "aliases": c.aliases,
        "subcommands": c.subcommands,
    }

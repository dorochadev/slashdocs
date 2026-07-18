from conftest import make_bot
from slashdocs.walker import walk_bot


def test_walk_finds_all_visible_commands_once() -> None:
    manifest = walk_bot(make_bot())
    names = [c.name for c in manifest.commands]
    assert sorted(names) == ["balance", "coinflip", "config", "ping"]
    # Manifest order is (category, name): Economy first, then General alphabetically
    assert names == ["coinflip", "balance", "config", "ping"]


def test_builtin_help_command_is_excluded() -> None:
    bot = make_bot()
    assert bot.get_command("help") is not None  # discord.py injects it automatically
    manifest = walk_bot(bot)
    assert "help" not in {c.name for c in manifest.commands}


def test_hidden_command_is_excluded() -> None:
    manifest = walk_bot(make_bot())
    assert "secret" not in {c.name for c in manifest.commands}


def test_slash_command_params_choices_and_extras() -> None:
    manifest = walk_bot(make_bot())
    coinflip = next(c for c in manifest.commands if c.name == "coinflip")
    assert coinflip.kind == "slash"
    assert coinflip.category == "Economy"
    assert coinflip.examples == ("/coinflip 500 heads",)
    amount, side = coinflip.params
    assert (amount.name, amount.type, amount.required) == ("amount", "integer", True)
    assert amount.description == "Amount to bet"
    assert side.choices == ("heads", "tails")


def test_group_has_subcommands_with_empty_slug() -> None:
    manifest = walk_bot(make_bot())
    config = next(c for c in manifest.commands if c.name == "config")
    assert config.slug == "config"
    assert [s.name for s in config.subcommands] == ["config set"]
    assert config.subcommands[0].slug == ""
    assert [p.name for p in config.subcommands[0].params] == ["key", "value"]


def test_prefix_command_help_and_aliases() -> None:
    manifest = walk_bot(make_bot())
    ping = next(c for c in manifest.commands if c.name == "ping")
    assert ping.kind == "prefix"
    assert ping.description == "Check the bot's latency."
    assert ping.aliases == ("pong",)


def test_hybrid_documented_once_as_hybrid() -> None:
    manifest = walk_bot(make_bot())
    balances = [c for c in manifest.commands if c.name == "balance"]
    assert len(balances) == 1
    assert balances[0].kind == "hybrid"


def test_walk_is_deterministic() -> None:
    assert walk_bot(make_bot()).content_hash() == walk_bot(make_bot()).content_hash()

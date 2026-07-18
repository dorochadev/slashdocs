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
    # description= on a hybrid lands in cmd.description, not help/brief
    assert balances[0].description == "Get the money balance of someone."


def test_walk_is_deterministic() -> None:
    assert walk_bot(make_bot()).content_hash() == walk_bot(make_bot()).content_hash()


async def test_kitchen_sink_covers_rare_paths() -> None:
    from conftest import make_kitchen_sink_bot

    manifest = walk_bot(await make_kitchen_sink_bot())
    by_name = {c.name: c for c in manifest.commands}

    # Context menu skipped entirely
    assert "Report" not in by_name

    # Natively hidden prefix command and @docs-hidden slash group excluded
    assert "sudo" not in by_name
    assert "internal" not in by_name

    # Cog name becomes the default category for both prefix and slash commands
    assert by_name["kick"].category == "Moderation"
    assert by_name["warn"].category == "Moderation"

    # Prefix group documents its subcommand; unannotated param falls back to string
    tag = by_name["tag"]
    assert [s.name for s in tag.subcommands] == ["tag add"]
    tag_add_params = {p.name: p for p in tag.subcommands[0].params}
    assert tag_add_params["name"].type == "string"
    assert tag_add_params["value"].type == "str"

    # Nested slash group: admin > config > reset
    admin = by_name["admin"]
    assert [s.name for s in admin.subcommands] == ["admin config"]
    assert [s.name for s in admin.subcommands[0].subcommands] == ["admin config reset"]

    # Slug collision: slash claims the clean slug, prefix falls back
    by_slug = {c.slug: c for c in manifest.commands}
    assert by_slug["stats"].kind == "slash"
    assert by_slug["prefix-stats"].kind == "prefix"


def test_claim_slug_counter_suffix_when_fallback_also_taken() -> None:
    from slashdocs.walker import _claim_slug

    slugs = {"stats", "prefix-stats"}
    assert _claim_slug("stats", slugs, fallback="prefix-stats") == "prefix-stats-2"
    assert _claim_slug("stats", slugs, fallback="prefix-stats") == "prefix-stats-3"


def test_slugs_are_sanitized_and_file_safe() -> None:
    from slashdocs.walker import _claim_slug

    slugs: set[str] = set()
    assert _claim_slug("../evil", slugs) == "evil"
    assert _claim_slug("foo/bar", slugs) == "foo-bar"
    assert _claim_slug("Weird  Name!", slugs) == "weird-name"


def test_reserved_slugs_are_never_claimed() -> None:
    from slashdocs.walker import _claim_slug

    slugs: set[str] = set()
    assert _claim_slug("index", slugs) == "index-cmd"
    assert _claim_slug("meta", slugs, fallback="prefix-meta") == "prefix-meta"


def test_collision_counter_appends_to_chosen_base() -> None:
    from slashdocs.walker import _claim_slug

    slugs = {"ping", "prefix-ping"}
    assert _claim_slug("ping", slugs, fallback="prefix-ping") == "prefix-ping-2"


def test_prefix_captured_and_overridable() -> None:
    import discord
    from discord.ext import commands

    assert walk_bot(make_bot()).prefix == "!"
    listy = commands.Bot(command_prefix=["?", "!"], intents=discord.Intents.none())
    assert walk_bot(listy).prefix == "?"
    called = commands.Bot(command_prefix=lambda bot, msg: "!", intents=discord.Intents.none())
    assert walk_bot(called).prefix == "!"  # callable: fall back to default
    assert walk_bot(called, prefix=",").prefix == ","


def test_extras_permissions_and_tier_on_hybrid() -> None:
    manifest = walk_bot(make_bot())
    balance = next(c for c in manifest.commands if c.name == "balance")
    assert balance.permissions == ("Booster Only",)
    assert balance.tier == "Premium"


async def test_introspected_permissions_and_cooldowns() -> None:
    from conftest import make_kitchen_sink_bot

    manifest = walk_bot(await make_kitchen_sink_bot())
    by_name = {c.name: c for c in manifest.commands}
    kick = by_name["kick"]
    assert kick.permissions == ("Kick Members",)
    assert (kick.cooldown_rate, kick.cooldown_per) == (1, 5.0)
    warn = by_name["warn"]
    assert warn.permissions == ("Moderate Members",)
    assert (warn.cooldown_rate, warn.cooldown_per) == (0, 0.0)


def test_hybrid_params_carry_slash_metadata() -> None:
    manifest = walk_bot(make_bot())
    balance = next(c for c in manifest.commands if c.name == "balance")
    (user,) = balance.params
    assert user.description == "Whose balance to view"
    assert user.choices == ("me", "you")
    assert user.required is False
    assert user.default == "'me'"


async def test_bot_required_permissions_are_not_shown_as_user_requirements() -> None:
    """@bot_has_permissions documents what the BOT needs, not the invoking user."""
    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())

    @bot.command(name="embed_thing")
    @commands.bot_has_permissions(embed_links=True)
    async def embed_thing(ctx) -> None: ...  # type: ignore[no-untyped-def]

    @bot.command(name="mixed")
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(embed_links=True)
    async def mixed(ctx) -> None: ...  # type: ignore[no-untyped-def]

    manifest = walk_bot(bot)
    by_name = {c.name: c for c in manifest.commands}
    assert by_name["embed_thing"].permissions == ()
    assert by_name["mixed"].permissions == ("Kick Members",)

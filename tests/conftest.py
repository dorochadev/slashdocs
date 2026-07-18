"""In-process discord.py bot fixtures. No gateway connection, no token, ever."""

import discord
from discord import app_commands
from discord.ext import commands

from slashdocs.decorator import docs


def make_bot() -> commands.Bot:
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())

    # Slash command with params, choices, @docs BELOW the command decorator
    @bot.tree.command(name="coinflip", description="Bet money on a coin flip.")
    @app_commands.describe(amount="Amount to bet", side="Which side to bet on")
    @app_commands.choices(
        side=[
            app_commands.Choice(name="heads", value="heads"),
            app_commands.Choice(name="tails", value="tails"),
        ]
    )
    @docs(category="Economy", example="/coinflip 500 heads")
    async def coinflip(interaction: discord.Interaction, amount: int, side: str) -> None: ...

    # Slash command hidden via @docs ABOVE the command decorator (object path)
    @docs(hidden=True)
    @bot.tree.command(name="secret", description="Owner only.")
    async def secret(interaction: discord.Interaction) -> None: ...

    # Slash group with a subcommand
    config = app_commands.Group(name="config", description="Server configuration.")

    @config.command(name="set", description="Set a config value.")
    async def config_set(interaction: discord.Interaction, key: str, value: str) -> None: ...

    bot.tree.add_command(config)

    # Prefix command with help/aliases
    @bot.command(name="ping", help="Check the bot's latency.", aliases=["pong"])
    async def ping(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        ...

    # Hybrid command — must be documented exactly once, kind="hybrid"
    @bot.hybrid_command(name="balance", description="Get the money balance of someone.")
    async def balance(ctx: commands.Context, user: str) -> None:  # type: ignore[type-arg]
        ...

    return bot


class Moderation(commands.Cog):
    """Cog whose name should become the default category."""

    @commands.command(name="kick", help="Kick a member.")
    async def kick(self, ctx: commands.Context, member: str) -> None:  # type: ignore[type-arg]
        ...

    @app_commands.command(name="warn", description="Warn a member.")
    async def warn(self, interaction: discord.Interaction, member: str) -> None: ...


async def make_kitchen_sink_bot() -> commands.Bot:
    """Covers the walker's rarer paths: cogs, context menus, nested groups,
    hidden prefix commands, prefix groups, unannotated params, slug collisions."""
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())

    await bot.add_cog(Moderation())

    # Context menu — out of scope for v1, must be skipped
    @bot.tree.context_menu(name="Report")
    async def report(interaction: discord.Interaction, message: discord.Message) -> None: ...

    # Natively hidden prefix command (discord.py's own hidden flag)
    @bot.command(name="sudo", help="Owner only.", hidden=True)
    async def sudo(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        ...

    # Prefix group with a subcommand carrying an unannotated param
    @bot.group(name="tag", help="Manage tags.", invoke_without_command=True)
    async def tag(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        ...

    @tag.command(name="add", help="Add a tag.")
    async def tag_add(ctx: commands.Context, name, value: str) -> None:  # type: ignore[no-untyped-def, type-arg]
        ...

    # Nested slash group (Discord allows depth 2)
    admin = app_commands.Group(name="admin", description="Admin tools.")
    admin_config = app_commands.Group(name="config", description="Admin config.", parent=admin)

    @admin_config.command(name="reset", description="Reset config.")
    async def admin_config_reset(interaction: discord.Interaction) -> None: ...

    bot.tree.add_command(admin)

    # Hidden slash group via @docs
    hidden_group = app_commands.Group(name="internal", description="Internal tools.")
    docs(hidden=True)(hidden_group)

    @hidden_group.command(name="dump", description="Dump state.")
    async def internal_dump(interaction: discord.Interaction) -> None: ...

    bot.tree.add_command(hidden_group)

    # Same name as slash AND prefix — prefix side must get the fallback slug
    @bot.tree.command(name="stats", description="Server stats.")
    async def stats_slash(interaction: discord.Interaction) -> None: ...

    @bot.command(name="stats", help="Server stats (prefix).")
    async def stats_prefix(ctx: commands.Context) -> None:  # type: ignore[type-arg]
        ...

    return bot

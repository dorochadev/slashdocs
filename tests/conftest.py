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

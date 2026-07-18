<p align="center">
  <img src="https://raw.githubusercontent.com/dorochadev/slashdocs/main/.github/assets/banner.webp"
       alt="slashdocs — turn your Discord bot commands into beautiful documentation" width="100%">
</p>

<p align="center">
  <a href="https://github.com/dorochadev/slashdocs/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/dorochadev/slashdocs/ci.yml?branch=main&label=CI"></a>
  <a href="https://pypi.org/project/slashdocs/"><img alt="PyPI" src="https://img.shields.io/pypi/v/slashdocs"></a>
  <a href="https://pypi.org/project/slashdocs/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/slashdocs"></a>
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue"></a>
</p>

Auto-generated command docs for discord.py bots — attach one line and your
commands page writes itself on startup.

Your bot already knows every command, parameter, type, description, permission,
and cooldown. slashdocs turns that into three kinds of output, kept in sync
every time the bot starts — no annotations required to get started:

- **MDX pages** for a docs site (Fumadocs, Nextra, Docusaurus, Starlight):
  one page per command, a category index, sidebar metadata.
- **commands.json** — a stable, documented JSON feed for building your own
  interactive `/commands` page.
- **commands.html** — a zero-dependency, self-contained searchable command
  browser (category sidebar with counts, live search, parameter chips,
  permission badges) for bots without a website.

## Install

```bash
pip install slashdocs   # or: uv add slashdocs
```

## Quickstart

```python
import slashdocs
from slashdocs import docs

@bot.tree.command(description="Bet money on a coin flip.")
@docs(category="Economy", example="/coinflip 500 heads")
async def coinflip(interaction: discord.Interaction, amount: int, side: str): ...

slashdocs.attach(bot, out="docs/commands")

bot.run(TOKEN)
```

Want the interactive command browser (and/or the JSON feed) too? Configure
outputs explicitly — one walk feeds them all:

```python
from slashdocs import attach, mdx, commands_json, commands_page

attach(bot, outputs=[
    mdx("docs/content/commands"),                     # docs-site MDX (as above)
    commands_json("site/public/commands.json"),       # feed your own /commands UI
    commands_page("site/public/commands.html",        # instant searchable page
                  title="MyBot Commands", accent="#5865F2"),
])
```

On startup slashdocs walks the loaded command tree (slash, prefix, and hybrid
commands, groups, cogs), diffs against the previous run, and writes only what
changed:

```
INFO slashdocs: 12 added, 0 changed, 0 removed -> docs/commands
```

Second startup with nothing changed:

```
INFO slashdocs: docs up to date (12 commands)
```

## The @docs decorator (optional)

Everything discord.py knows is picked up automatically. `@docs` adds what it
can't express:

```python
@docs(
    category="Economy",              # docs-site grouping (default: cog name)
    example="/coinflip 500 heads",   # str or list[str]
    hidden=True,                     # exclude from generated docs
    notes="Requires the Economy module to be enabled.",
    permissions="Booster Only",      # custom permission badges (str or list[str])
    tier="Premium",                  # renders a 👑 tier badge
)
```

Standard permissions and cooldowns are picked up without `@docs`:
`@app_commands.default_permissions(...)` on slash commands,
`@commands.has_permissions(...)` / `has_guild_permissions(...)` and
`@commands.cooldown(...)` on prefix and hybrid commands. The bot's real
`command_prefix` is rendered too (pass `attach(..., prefix="?")` to override —
needed when the prefix is a callable).

Works above or below the command decorator, on slash, prefix, and hybrid
commands and groups. Commands marked `hidden=True` in discord.py's own
`@commands.command(hidden=True)` are excluded too, as is discord.py's
auto-injected default help command.

## Wiring the output into your docs site

slashdocs writes plain MDX with frontmatter plus `meta.json`. Point it at your
content directory:

- **Fumadocs** — `attach(bot, out="content/docs/commands")`. `meta.json` is
  picked up natively for sidebar order.
- **Nextra** — `attach(bot, out="pages/commands")` (or `content/` for Nextra 4).
- **Docusaurus** — `attach(bot, out="docs/commands")`; frontmatter `title` and
  `description` are used as-is; `meta.json` is ignored (harmless).
- **Astro Starlight** — `attach(bot, out="src/content/docs/commands")`.

Generated files carry `generated_by: slashdocs` in their frontmatter; slashdocs
only ever deletes files bearing that marker, so hand-written pages in the same
folder are safe.

## The commands.json feed

`commands_json(path)` writes a deterministic, schema-versioned JSON document —
the same manifest slashdocs uses internally:

```jsonc
{
  "schema_version": 2,
  "prefix": "!",
  "commands": [
    {
      "name": "ban", "slug": "ban", "kind": "slash",       // "slash" | "prefix" | "hybrid"
      "description": "...", "category": "Moderation",
      "params": [{ "name": "user", "type": "user", "required": true,
                   "description": "...", "choices": [], "default": null }],
      "permissions": ["Ban Members"], "tier": "",
      "cooldown_rate": 0, "cooldown_per": 0.0,
      "aliases": [], "examples": [], "notes": "",
      "subcommands": []                                     // same shape, nested
    }
  ]
}
```

Fetch it from any frontend and render search/filter UI however you like.
The file is only rewritten when its content changes, so it's safe to serve
statically and cache.

## The static commands page

`commands_page(path, title=..., accent=...)` emits a single HTML file with the
data embedded and zero external requests — drop it on any static host. It
renders a category sidebar with counts, live search over names/aliases/
descriptions, and cards with parameter chips, permission and tier badges,
cooldowns, and slash/prefix indicators — hybrid commands show both invocation
forms. Light and dark themes follow the visitor's system preference.

## API

```python
slashdocs.attach(bot, out=None, *, outputs=None, prefix=None, base_slug="/commands", clean=True)
slashdocs.mdx(path, *, base_slug="/commands", clean=True)
slashdocs.commands_json(path)
slashdocs.commands_page(path, *, title="Commands", accent="#5865F2")
slashdocs.docs(*, category=None, example=None, hidden=False, notes="", permissions=None, tier="")
slashdocs.__version__
```

`attach(bot, out="docs/commands")` is shorthand for a single `mdx()` output.

`attach()`'s on_ready hook can never crash your bot: every output is attempted
even if another fails, and any failure is caught, logged to the `slashdocs`
logger, and never re-raised into the bot. Calling `generate()` directly (e.g.
from a script) instead raises `OutputGenerationError` if any output failed,
after every output has been attempted — so a CI job or build script can tell
generation actually failed rather than reading a false "up to date".

## Requirements

- Python ≥ 3.10
- discord.py ≥ 2.4

## License

MIT

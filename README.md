# slashdocs

Auto-generated MDX command docs for discord.py bots — attach one line and your
commands page writes itself on startup.

Your bot already knows every command, parameter, type, and description.
slashdocs turns that into a browsable docs site's content — one MDX page per
command, an index grouped by category, and sidebar metadata — and keeps it in
sync every time the bot starts. No annotations required to get started.

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
async def coinflip(interaction, amount: int, side: str): ...

slashdocs.attach(bot, out="docs/commands")

bot.run(TOKEN)
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
)
```

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

## API

```python
slashdocs.attach(bot, out="docs/commands", *, base_slug="/commands", clean=True, fmt="mdx")
slashdocs.docs(*, category=None, example=None, hidden=False, notes="")
slashdocs.__version__
```

Docs generation can never crash your bot: all failures are caught and logged
to the `slashdocs` logger.

## Requirements

- Python ≥ 3.10
- discord.py ≥ 2.4

## License

MIT

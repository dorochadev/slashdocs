"""Renders a Manifest as a single self-contained commands.html.

No build step, no external requests: styles and script are inline and the command
data is embedded as a JSON island. The page renders a searchable, category-filtered
command browser (the bleed.bot / noctaly.com style) for bots without a docs site.

Stateless like json_out: write_page byte-compares against the file on disk.
"""

from __future__ import annotations

import html as html_mod
import json
import logging
import re
from pathlib import Path

from ._io import write_if_changed
from .model import Manifest

logger = logging.getLogger("slashdocs")

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root {
  --accent: __ACCENT__;
  --bg: #ffffff; --fg: #16181d; --muted: #5c6270; --card: #f5f6f8; --line: #e3e5ea;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #101116; --fg: #e8eaef; --muted: #9aa1b0; --card: #191b22; --line: #262933; }
}
* { box-sizing: border-box; margin: 0; }
body { background: var(--bg); color: var(--fg);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
.layout { display: flex; gap: 2rem; max-width: 1100px; margin: 0 auto; padding: 2rem 1rem; }
aside { flex: 0 0 200px; position: sticky; top: 2rem; align-self: flex-start;
  max-height: calc(100vh - 4rem); overflow-y: auto; }
aside button { display: flex; justify-content: space-between; width: 100%; padding: .4rem .7rem;
  border: 0; border-radius: .5rem; background: none; color: var(--muted);
  font: inherit; cursor: pointer; text-align: left; }
aside button:hover { background: var(--card); }
aside button.active { background: var(--card); color: var(--fg); font-weight: 600; }
aside button .count { color: var(--muted); font-size: .85em; }
main { flex: 1; min-width: 0; }
h1 { font-size: 1.5rem; margin-bottom: 1rem; }
#search { width: 100%; padding: .6rem .9rem; margin-bottom: 1.25rem;
  border: 1px solid var(--line); border-radius: .6rem; background: var(--card);
  color: var(--fg); font: inherit; }
#search:focus { outline: 2px solid var(--accent); border-color: transparent; }
.card { padding: 1rem; margin-bottom: .75rem; border: 1px solid var(--line);
  border-radius: .75rem; background: var(--card); }
.card h2 { font-size: 1rem; font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  display: flex; flex-wrap: wrap; gap: .5rem; align-items: center; }
.card p { color: var(--muted); margin: .35rem 0 .5rem; }
.chips { display: flex; flex-wrap: wrap; gap: .35rem; }
.chip { padding: .1rem .55rem; border-radius: 999px; font-size: .78em;
  border: 1px solid var(--line); color: var(--muted); }
.chip.req { border-color: var(--accent); color: var(--accent); }
.badge { padding: .1rem .55rem; border-radius: .4rem; font-size: .72em; font-weight: 600;
  background: var(--accent); color: #fff; font-family: system-ui, sans-serif; }
.badge.kind { background: none; border: 1px solid var(--line); color: var(--muted);
  font-weight: 400; }
.meta { display: flex; flex-wrap: wrap; gap: .5rem .9rem; margin-top: .5rem;
  color: var(--muted); font-size: .82em; }
.empty { color: var(--muted); padding: 2rem 0; text-align: center; }
@media (max-width: 720px) { .layout { flex-direction: column; } aside { position: static;
  display: flex; flex-wrap: wrap; gap: .25rem; flex-basis: auto; } aside button { width: auto; } }
</style>
</head>
<body>
<div class="layout">
  <aside id="categories" aria-label="Categories"></aside>
  <main>
    <h1>__TITLE__</h1>
    <input id="search" type="search" placeholder="Search commands…" aria-label="Search commands">
    <div id="cards"></div>
  </main>
</div>
<script id="slashdocs-data" type="application/json">__DATA__</script>
<script>
(function () {
  "use strict";
  var data = JSON.parse(document.getElementById("slashdocs-data").textContent);
  var prefix = data.prefix || "!";

  function flatten(cmd, out) {
    out.push(cmd);
    (cmd.subcommands || []).forEach(function (sub) {
      sub.category = cmd.category;
      flatten(sub, out);
    });
    return out;
  }
  var all = [];
  data.commands.forEach(function (c) { flatten(c, all); });

  var counts = {};
  all.forEach(function (c) { counts[c.category] = (counts[c.category] || 0) + 1; });
  var categories = Object.keys(counts).sort();
  var state = { category: null, query: "" };

  function displayName(c) {
    if (c.kind === "hybrid") return "/" + c.name + "  ·  " + prefix + c.name;
    return (c.kind === "prefix" ? prefix : "/") + c.name;
  }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }

  function matches(c) {
    if (state.category && c.category !== state.category) return false;
    if (!state.query) return true;
    var hay = (c.name + " " + (c.aliases || []).join(" ") + " " + (c.description || ""))
      .toLowerCase();
    return hay.indexOf(state.query) !== -1;
  }

  function renderSidebar() {
    var aside = document.getElementById("categories");
    aside.textContent = "";
    function item(label, count, value) {
      var b = el("button", value === state.category ? "active" : "");
      b.appendChild(el("span", "", label));
      b.appendChild(el("span", "count", String(count)));
      b.addEventListener("click", function () { state.category = value; render(); });
      aside.appendChild(b);
    }
    item("All", all.length, null);
    categories.forEach(function (cat) { item(cat, counts[cat], cat); });
  }

  function renderCards() {
    var root = document.getElementById("cards");
    root.textContent = "";
    var shown = all.filter(matches);
    if (!shown.length) {
      root.appendChild(el("div", "empty", "No commands match."));
      return;
    }
    shown.forEach(function (c) {
      var card = el("article", "card");
      var h = el("h2", "", displayName(c));
      h.appendChild(el("span", "badge kind", c.kind));
      if (c.tier) h.appendChild(el("span", "badge", "\\u{1F451} " + c.tier));
      (c.permissions || []).forEach(function (p) { h.appendChild(el("span", "badge", p)); });
      card.appendChild(h);
      card.appendChild(el("p", "", c.description || "No description given"));
      if ((c.params || []).length) {
        var chips = el("div", "chips");
        c.params.forEach(function (p) {
          chips.appendChild(el("span", "chip" + (p.required ? " req" : ""), p.name));
        });
        card.appendChild(chips);
      }
      var meta = [];
      if ((c.aliases || []).length) meta.push("aliases: " + c.aliases.join(", "));
      if (c.cooldown_rate) meta.push("cooldown: " + c.cooldown_rate + "/" + c.cooldown_per + "s");
      if (meta.length) {
        var m = el("div", "meta");
        meta.forEach(function (t) { m.appendChild(el("span", "", t)); });
        card.appendChild(m);
      }
      root.appendChild(card);
    });
  }

  function render() { renderSidebar(); renderCards(); }
  document.getElementById("search").addEventListener("input", function (e) {
    state.query = e.target.value.trim().toLowerCase();
    renderCards();
  });
  render();
})();
</script>
</body>
</html>
"""


_PLACEHOLDER_RE = re.compile("__TITLE__|__ACCENT__|__DATA__")


def render_page(manifest: Manifest, *, title: str = "Commands", accent: str = "#5865F2") -> str:
    data = json.dumps(manifest.to_dict(), sort_keys=True).replace("</", "<\\/")
    values = {
        "__TITLE__": html_mod.escape(title),
        "__ACCENT__": html_mod.escape(accent),
        "__DATA__": data,
    }
    # Single-pass substitution: sequential str.replace() calls would let a title or
    # accent that literally contains a later token (e.g. "__DATA__") get substituted
    # again by a later .replace(), corrupting the output.
    return _PLACEHOLDER_RE.sub(lambda m: values[m.group(0)], _TEMPLATE)


def write_page(
    path: Path, manifest: Manifest, *, title: str = "Commands", accent: str = "#5865F2"
) -> bool:
    """Write commands.html if its content would change. Returns True if written."""
    written = write_if_changed(path, render_page(manifest, title=title, accent=accent))
    if written:
        logger.info("slashdocs: wrote %s", path)
    return written

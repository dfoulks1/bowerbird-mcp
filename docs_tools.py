#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.10,<2", "pyyaml"]
# ///
"""Write docs-src/tools.md from the tools' own docstrings and signatures: a paragraph and an argument table each."""
import html
import inspect
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bowerbird_mcp as k


def prose(doc: str) -> str:
    """The docstring as one paragraph; <...> escaped outside `code` so Markdown keeps it."""
    parts = " ".join(inspect.cleandoc(doc or "").split()).split("`")
    return "`".join(html.escape(p, quote=False) if i % 2 == 0 else p for i, p in enumerate(parts))


out = ["# Tools", "", "<!-- seal-banner: Derived from the tools' own docstrings. -->", "", ("Every tool, from its own docstring. Run one as `bowerbird-mcp <tool> "
                       "name=value ...` (or with flags: `--name value`, `-n value`), or see the same text with `help <tool>`. `-O json|text` chooses the output."), ""]
for name, fn in sorted(k.REG.items()):
    roles = [r for r, ts in k.ROLES.items() if name in ts]  # the roles that switch it on, and the formats whose server offers it
    fmts = ["OKF", *(f.replace("seal-only", "Seal-only").replace("asciidoc", "AsciiDoc").replace("skos", "SKOS").replace("adr", "ADR").replace("markdown", "Markdown")
                     for f in ("markdown", "adr", "skos", "asciidoc", "seal-only") if name in k.TIERS[f])]
    out += [f"## {name}", "", f"Role: {', '.join(f'`{r}`' for r in roles)}. Offered by a server for: {', '.join(fmts)}.", "", prose(fn.__doc__), ""]
    if name in k.EXAMPLES:
        out += ["```sh", *(f"bowerbird-mcp {k.flag_example(name, e)}" for e in k.EXAMPLES[name]), "```", ""]
    args = [(n, p) for n, p in inspect.signature(fn).parameters.items() if n != "ctx"]
    if args:
        sh = k.short_flags(name, fn)
        out += ["| Argument | Flag | Type | Default |", "|---|---|---|---|"]
        for n, p in args:
            out.append(f"| `{n}` | `{k.flag_text(n, p, sh)}` | `{k.type_text(p).split(', default')[0].removesuffix(', required')}` | " + ("required" if p.default is p.empty else "unset" if p.default is None else f"`{p.default!r}`") + " |")
        out.append("")
(HERE / "docs-src/tools.md").write_text("\n".join(out))
if k.KB_ROOT == HERE:
    k.mark_derived(HERE / "docs-src/tools.md", "docs_tools.py")  # the ledger says this page is built from the code, for these bytes

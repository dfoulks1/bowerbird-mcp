# Dendron

<!-- seal-banner: Written with Claude Sonnet 5.5. The link rules come from Dendron's own documentation, read second-hand; the checks are tests on throwaway collections, not yet a real workspace. A person has not reviewed this page yet. -->

**Use it when** your notes are a Dendron workspace and you want search, link checking and reviews over them.
Dendron's own README says the project is in maintenance only; this format reads the files as they are.

## Install and switch it on

```sh
pip install 'bowerbird-mcp[dendron]'          # or: uvx --from 'bowerbird-mcp[dendron]' bowerbird-mcp ...
```

```yaml
# bower.yaml, at the root of the workspace
format: dendron
about: My notes.
```

The add-on is its own package (`bowerbird-dendron`, in this repository, released with `bowerbird-mcp`). The extra pulls it in, and Bowerbird finds it through the
`bowerbird.formats` entry point. Without it, `format: dendron` stops with a message that says to install it. Everything else is the
[Markdown](markdown.md) format: the same tools, the same sealing (`.waxseals.yaml` beside the files), and ADR records in it are sealed
with an outcome as in [ADR](adr.md).

## What it reads

Markdown notes in the workspace. A note's name is its file name, and the dots are the hierarchy: `recipes.vegetarian.md` is the child of `recipes`.

| You write | Bowerbird reads it as |
|---|---|
| `[[recipes.vegetarian]]` | a link to the note with that name |
| `[[Veggies\|recipes.vegetarian]]` | the same link; **the alias is on the left** (the opposite of Obsidian and Foam) |
| `[[recipes.vegetarian#header]]` | a link; the header is checked against the note's headings |
| `[[recipes.vegetarian#^anchor]]` | a link to the note; the anchor is not checked |
| `![[recipes.vegetarian]]` | a note reference, read as a link |
| `[[dendron://vault/recipes.vegetarian]]` | a link to `recipes.vegetarian`; the vault prefix is dropped |
| `[[recipes]]` with no `recipes.md` but a `recipes.vegetarian.md` | a **stub**: the parent exists, so this is not a broken link |

## How a name finds its note

The name matches the file name exactly, case ignored, in any folder of the workspace (so any vault). A name that finds no note and is not the
parent of one is a broken link (a `dead_link` warning).

## Reviews and lint

As in [Markdown](markdown.md): seals live in a `.waxseals.yaml` beside the note, and `lint` warns of a wikilink that leads nowhere.

## What it does not do yet

- Hashtags (`#a.b`) and `@user` tags, which Dendron treats as links to `tags.a.b` and `user.x`, are not read; nor are the `tags` property, schemas
  (`*.schema.yml`) or `dendron.yml`.
- Wildcard references (`![[demo.journal.*]]`) and range references (`![[note#start:#end]]`) are not followed.
- A link into a named vault is resolved by note name across every vault, not within the vault it names.
- The documentation does not say whether link names are case-sensitive or how header slugs are made; Bowerbird ignores case and uses the same slugs as in markdown.

## Tested against

Made-up collections, not a real workspace. The test builds this one in a temporary folder:

- `x.md` holding `[[alias|a.b.c#head]]`, `[[a.b]]`, `[[dendron://v/a.b.c]]` and `[[gone.x]]`, and `a.b.c.md`.
- What the test checks: the alias is read from the left; `[[a.b]]` is a stub (a child exists, there is no file) and is not broken; the `dendron://v/` prefix is dropped; and the only broken link reported is `[[gone.x]]`.
- Not tested: more than one vault, `dendron.yml`, or a header slug that differs from the markdown one.

Nothing here has run against a real workspace: only the small made-up collections above, in a temporary folder on Linux with Python 3.10, by the test suite (`test_bowerbird_mcp.py`). Windows and macOS paths, large workspaces and Dendron's own newer features are untested. The rules this page lists as unconfirmed come from Dendron's own documentation, read second-hand.

## Report a problem

Something read wrong, a link reported broken that is not, or one missed: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to [dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Say which
format it is (`format: dendron`), the version (`bowerbird-mcp --version`), and give the smallest note or two that show it, never your private ones. More on
[reporting a problem](../troubleshooting.md#reporting-a-problem).

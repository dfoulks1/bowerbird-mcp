# Foam

<!-- seal-banner: Written with Claude Sonnet 5.5. The link rules come from Foam's own documentation, read second-hand; the checks are tests on throwaway collections, not yet a real workspace. A person has not reviewed this page yet. -->

**Use it when** your notes are a Foam workspace in VS Code and you want search, link checking and reviews over them.

## Install and switch it on

```sh
pip install 'bowerbird-mcp[foam]'          # or: uvx --from 'bowerbird-mcp[foam]' bowerbird-mcp ...
```

```yaml
# bower.yaml, at the root of the workspace
format: foam
about: My notes.
```

The add-on is its own package (`bowerbird-foam`, in this repository, released with `bowerbird-mcp`). The extra pulls it in, and Bowerbird finds it through the
`bowerbird.formats` entry point. Without it, `format: foam` stops with a message that says to install it. Everything else is the
[Markdown](markdown.md) format: the same tools, the same sealing (`.waxseals.yaml` beside the files), and ADR records in it are sealed
with an outcome as in [ADR](adr.md).

## What it reads

Markdown notes anywhere in the workspace. It leaves out `.foam/` (templates, which hold `$FOAM_*` variables inside `[[ ]]`) and `.vscode/`.

| You write | Bowerbird reads it as |
|---|---|
| `[[note]]`, `[[house/todo]]` | a link by identifier: any unique path suffix |
| `[[note\|alias]]` | the same link; the alias is a label |
| `[[note#Section Title]]` | a link; the section is checked against the headings |
| `[[note#^id]]` | a link to the note; the block id is not checked |
| `![[note]]`, `![[note#Section]]` | an embed, read as a link |
| `![[image.png\|300]]` | a link to the file; the size is ignored |
| `[[projects]]` | `projects.md` if there is one, else `projects/index.md`, else `projects/README.md` |
| `[note]: note.md "Note"` | a link reference definition: read as it is, in every format; Foam writes one for each wikilink |

A link to a note that does not exist yet is a Foam *placeholder*. Bowerbird reports it as a `dead_link` warning like any broken link, so
a list of them is a list of notes still to write.

## How a name finds its note

By path suffix, as Foam does: `[[todo]]` finds any `todo.md`, `[[house/todo]]` finds `house/todo.md` anywhere. The case is ignored. If several
notes match, the shortest path wins, then the nearest to the linking page. Foam itself picks alphabetically and warns; this differs when two
paths are the same length.

Foam's documentation also treats a name that starts with `/` or `.` as a path (`[[./a]]`, `[[../b]]`, `[[/from/root]]`). Bowerbird reads these as a
name, so they are reported as broken. It does not settle case rules either: Foam's documentation does not say.

## Reviews and lint

As in [Markdown](markdown.md): seals live in a `.waxseals.yaml` beside the note, and `lint` warns of a wikilink that leads nowhere.

## What it does not do yet

- Inline `#tags`, the `tags` and `alias` properties, and `type` are not read.
- Relative and root-anchored path links (`[[./a]]`, `[[/a]]`) are not resolved.
- `foam.files.exclude` and `foam.files.include` are not read; `.gitignore` decides what is left out, as in every format.

## Tested against

Made-up collections, not a real workspace. The test builds this one in a temporary folder:

- `a.md` holding `[[projects]]`, `[[house/todo]]` and `[[nope]]`; `projects/index.md`; `projects/house/todo.md`; and `.foam/templates/n.md` holding `[[$FOAM_X]]`.
- What the test checks: `[[projects]]` finds `projects/index.md`; `[[house/todo]]` finds the note by path suffix; `.foam/` is left out; and the only broken link reported is `[[nope]]`.
- Not tested: that a link reference definition is never called unused. Markdown-format `lint` does not report unused definitions at all, so that setting has nothing to quiet yet.

Nothing here has run against a real workspace: only the small made-up collections above, in a temporary folder on Linux with Python 3.10, by the test suite (`test_bowerbird_mcp.py`). Windows and macOS paths, large workspaces and Foam's own newer features are untested. The rules this page lists as unconfirmed come from Foam's own documentation, read second-hand.

## Report a problem

Something read wrong, a link reported broken that is not, or one missed: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to [dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Say which
format it is (`format: foam`), the version (`bowerbird-mcp --version`), and give the smallest note or two that show it, never your private ones. More on
[reporting a problem](../troubleshooting.md#reporting-a-problem).

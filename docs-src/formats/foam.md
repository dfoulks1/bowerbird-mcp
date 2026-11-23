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
| `[note]: note.md "Note"` | a link reference definition: kept, and never reported as unused |

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

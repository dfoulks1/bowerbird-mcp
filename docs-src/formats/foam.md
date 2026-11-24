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

The add-on ships in the one `bowerbird-mcp` package (`bowerbird_foam.py`): the extra adds nothing, it is the name you ask for, and `format: foam` is the switch. Everything else is the
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
| `[[./a]]`, `[[../b]]`, `[[/c]]` | a path: from the citing note, or (`/`) from the workspace root; the `.md` is optional |
| `alias: Plan B, Plan C` | `[[Plan B]]` finds this note |
| `#tag`, `#nested/tag` | a tag of the note, beside the `tags` property (a comma-separated `tags: a, b` is read too) |
| `[note]: note.md "Note"` | a link reference definition: read as it is, in every format; Foam writes one for each wikilink |

A link to a note that does not exist yet is a Foam *placeholder*. Bowerbird reports it as a `dead_link` warning like any broken link, so
a list of them is a list of notes still to write.

## How a name finds its note

By path suffix, as Foam does: `[[todo]]` finds any `todo.md`, `[[house/todo]]` finds `house/todo.md` anywhere. The case is ignored. If several
notes match, the shortest path wins, then the nearest to the linking page. Foam itself picks alphabetically and warns; this differs when two
paths are the same length.

A name that starts with `/` or `.` is a path, as Foam's documentation says: `[[./a]]` and `[[../b]]` from the citing note, `[[/from/root]]` from the workspace root. A path that finds no file is a broken link.
Foam's documentation does not settle case rules, so the case is ignored here.

## Reviews and lint

Seal a note as in [Sealing](../sealing.md); the review goes in a `.waxseals.yaml` in the note's folder, and the note is never edited. `lint` is offered here as in [Markdown](markdown.md): it checks fact blocks and warns of a wikilink that leads nowhere (`dead_link`) or to a heading that is not there (`dead_anchor`).

## Limits

- `foam.files.exclude` and `foam.files.include` are not read; `.gitignore` decides what is left out, as in every format. `.foam/` and `.vscode/` are always left out.
- The `type` property and a note's `title` are not used for links (Foam finds a note by its file name or alias).
- The inline tag rule is Obsidian's, because Foam's documentation does not give one.
- A file named only for a date (`2024-05-01.md`) is a daily note, not an ADR record, so sealing it asks for no `decision`. A dated name with a title (`2024-05-01-use-x.md`) is a record, as in [Markdown](markdown.md).

## Tested against

Made-up collections, not a real workspace. The test builds this one in a temporary folder:

- `a.md` holding `[[projects]]`, `[[house/todo]]`, `[[nope]]`, `[[./gone]]` and `[[/a]]`; `projects/index.md` with `alias: Plan B, Plan C`; `projects/house/todo.md`; `projects/house/sib.md`; and `.foam/templates/n.md` holding `[[$FOAM_X]]`.
- What the test checks: `[[projects]]` finds `projects/index.md`; `[[house/todo]]` finds the note by path suffix; `[[./sib]]`, `[[../index]]` and `[[/a]]` are read as paths; `[[Plan B]]` and `[[plan c]]` find the index by alias; `.foam/` is left out; the only broken links reported are `[[nope]]` and `[[./gone]]`; and `#one and #two/x` are tags.
- Not tested: that a link reference definition is never called unused. Markdown-format `lint` does not report unused definitions at all, so that setting has nothing to quiet yet.

Nothing here has run against a real workspace: only the small made-up collections above, in a temporary folder on Linux with Python 3.10, by the test suite
(`test_bowerbird_mcp.py`). Windows and macOS paths, large workspaces and Foam's own newer features are untested. The rules this page lists as unconfirmed come from
Foam's own documentation, read second-hand.

## Report a problem

Something read wrong, a link reported broken that is not, or one missed: [open an issue](https://github.com/dfoulks1/bowerbird-mcp/issues/new) or write to [dfoulks@voltpop.com](mailto:dfoulks@voltpop.com). Say which
format it is (`format: foam`), the version (`bowerbird-mcp --version`), and give the smallest note or two that show it, never your private ones. More on
[reporting a problem](../troubleshooting.md#reporting-a-problem).

# Obsidian

<!-- seal-banner: Written with Claude Sonnet 5.5. The link rules come from Obsidian's own documentation, read second-hand; the checks are tests on throwaway collections, not yet a real vault. A person has not reviewed this page yet. -->

**Use it when** your notes live in an Obsidian vault and you want to search them, follow their links and know which a person has checked,
without changing how you write.

## Install and switch it on

```sh
pip install 'bowerbird-mcp[obsidian]'          # or: uvx --from 'bowerbird-mcp[obsidian]' bowerbird-mcp ...
```

```yaml
# bower.yaml, at the root of the vault
format: obsidian
about: My notes.
```

The add-on is its own package (`bowerbird-obsidian`, in this repository, released with `bowerbird-mcp`). The extra pulls it in, and Bowerbird finds it through the
`bowerbird.formats` entry point. Without it, `format: obsidian` stops with a message that says to install it. Everything else is the
[Markdown](markdown.md) format: the same tools, the same sealing (`.waxseals.yaml` beside the files), and ADR records in it are sealed
with an outcome as in [ADR](adr.md).

## What it reads

Markdown notes, anywhere in the vault. It leaves out `.obsidian/` (the vault's settings, plugins and workspace) and `.trash/`.

| You write | Bowerbird reads it as |
|---|---|
| `[[Note]]`, `[[Note.md]]` | a link to the note named Note |
| `[[Note\|alias]]` | the same link; the alias is only a label |
| `[[Note#Heading]]`, `[[Note#H1#H2]]` | a link to the note; the heading is checked against the note's headings |
| `[[#Heading]]` | a link to a heading of this note |
| `[[Note#^block-id]]` | a link to the note; the block id is not checked (Obsidian keeps it hidden in the text) |
| `![[Note]]`, `![[Note#Heading]]` | an embed, read as a link |
| `![[diagram.png]]`, `![[diagram.png\|300]]` | a link to the file: beside the note, from the vault root, or anywhere in the vault; the size part is ignored |
| `[text](Note%20Name.md)` | a markdown link, as in every format |
| `%% [[a comment]] %%` | nothing: a comment is not read |

Links inside code (fenced or inline) are not read, in this format or any other.

## How a name finds its note

A link names a note by its path, ending with what you wrote: `[[Note]]` finds `Note.md` anywhere, `[[Projects/Note]]` finds `Projects/Note.md`.
The `.md` is optional and the case is ignored. When several notes match, the one with the shortest path wins, then the one nearest the
page that links. A name that finds nothing is a broken link, reported as a warning (`dead_link`), and `links` shows it with `exists: false`.

Obsidian's own documentation says how it *writes* links (the shortest unique path, or the full path from the vault root) but not how it
resolves a name that two notes share, or whether case matters. Bowerbird's rule above is its own. If your vault depends on another,
the warnings will show it.

## Reviews and lint

Seal a note as in [Sealing](../sealing.md); the review lives in a `.waxseals.yaml` in the note's folder. `lint` reports a wikilink that
leads nowhere or to a heading that is not there, both as warnings.

## What it does not do yet

- Inline `#tags` and the `tags`, `aliases` and `cssclasses` properties are not read; `[[Alias]]` does not resolve to the note that
  declares the alias.
- `.canvas` and `.base` files are not read, and a link inside one is not followed.
- `[[## text]]` and `[[^text]]` are searches in Obsidian, not links; they are reported as broken.
